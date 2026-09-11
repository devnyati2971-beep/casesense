import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

class DraftsState {
  final bool isLoading;
  final String? error;
  final String? currentDraftId;
  final String status; // CREATED, GENERATING, GENERATED, EDITING, FINALIZED
  final Map<String, dynamic>? draftDetail;
  final List<Map<String, dynamic>> drafts;
  final List<Map<String, dynamic>> allDrafts;

  DraftsState({
    this.isLoading = false,
    this.error,
    this.currentDraftId,
    this.status = 'CREATED',
    this.draftDetail,
    this.drafts = const [],
    this.allDrafts = const [],
  });

  DraftsState copyWith({
    bool? isLoading,
    String? error,
    String? currentDraftId,
    String? status,
    Map<String, dynamic>? draftDetail,
    List<Map<String, dynamic>>? drafts,
    List<Map<String, dynamic>>? allDrafts,
  }) {
    return DraftsState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      currentDraftId: currentDraftId ?? this.currentDraftId,
      status: status ?? this.status,
      draftDetail: draftDetail ?? this.draftDetail,
      drafts: drafts ?? this.drafts,
      allDrafts: allDrafts ?? this.allDrafts,
    );
  }
}

class DraftsController extends StateNotifier<DraftsState> {
  final Ref ref;
  Timer? _pollTimer;

  DraftsController(this.ref) : super(DraftsState());

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  // 1. Create a new draft
  Future<String?> createDraft(
    String matterId,
    String documentType, {
    String? title,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(
        Endpoints.drafts(matterId),
        data: {
          'document_type': documentType,
          if (title != null) 'title': title,
        },
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final draft = raw.containsKey('id') ? raw : unwrapData(res.data);
      final newDraftId = draft['id']?.toString();

      state = state.copyWith(
        isLoading: false,
        currentDraftId: newDraftId,
        status: draft['status'] ?? 'CREATED',
      );
      return newDraftId;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return null;
    }
  }

  // 2. Generate Draft (AI composition) — async job, poll the draft status.
  Future<bool> generateDraft(String draftId, {String? instructions}) async {
    state = state.copyWith(isLoading: true, status: 'GENERATING');
    try {
      final dio = ref.read(dioProvider);
      await dio.post(
        Endpoints.draftGenerate(draftId),
        data: {
          if (instructions != null && instructions.trim().isNotEmpty)
            'argument_focus': instructions.trim(),
        },
      );
      _pollDraftStatus(draftId);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
        status: 'FAILED',
      );
      return false;
    }
  }

  void _pollDraftStatus(String draftId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      try {
        final dio = ref.read(dioProvider);
        final res = await dio.get(Endpoints.draftDetail(draftId));
        final raw = res.data is Map<String, dynamic>
            ? res.data as Map<String, dynamic>
            : <String, dynamic>{};
        final draft = raw['draft'] ?? unwrapData(res.data)['draft'] ?? raw;
        final status = draft['status'] ?? 'CREATED';
        final currentVersion = raw['current_version'] as Map<String, dynamic>?;

        state = state.copyWith(
          status: status,
          draftDetail: currentVersion ?? state.draftDetail,
        );

        if (status == 'GENERATED' ||
            status == 'LAWYER_REVIEW' ||
            status == 'FAILED' ||
            status == 'FINALIZED') {
          timer.cancel();
          state = state.copyWith(isLoading: false);
        }
      } catch (e) {
        timer.cancel();
        state = state.copyWith(isLoading: false, error: e.toString());
      }
    });
  }

  // 3. Load draft detail (sections, arguments, citations)
  Future<void> loadDraftDetail(String draftId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get(Endpoints.draftDetail(draftId));
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final draft =
          raw['draft'] as Map<String, dynamic>? ??
          unwrapData(res.data)['draft'] as Map<String, dynamic>?;
      final currentVersion =
          raw['current_version'] as Map<String, dynamic>? ??
          unwrapData(res.data)['current_version'] as Map<String, dynamic>?;

      state = state.copyWith(
        isLoading: false,
        draftDetail: currentVersion,
        currentDraftId: draftId,
        status: draft?['status'] ?? state.status,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  // 4. Save edited sections (lawyer editing — no silent overwrite)
  Future<bool> saveSections(
    String draftId,
    List<Map<String, dynamic>> sections, {
    int? expectedVersion,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      await dio.patch(
        Endpoints.draftDetail(draftId),
        data: {
          if (expectedVersion != null) 'expected_version': expectedVersion,
          'sections': sections,
        },
      );
      state = state.copyWith(isLoading: false, status: 'LAWYER_REVIEW');
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  // 5. Finalize Draft
  Future<bool> finalizeDraft(String draftId) async {
    state = state.copyWith(isLoading: true);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(Endpoints.draftFinalize(draftId));
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final draft = raw.containsKey('id') ? raw : unwrapData(res.data);
      state = state.copyWith(
        isLoading: false,
        status: draft['status'] ?? 'FINALIZED',
      );
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  // 6. Request PDF export
  Future<bool> exportDraft(String draftId, {String format = 'pdf'}) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      await dio.post(Endpoints.draftExport(draftId), data: {'format': format});
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  // 7. Load draft list for a matter
  Future<void> loadDrafts(String matterId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get(Endpoints.drafts(matterId));
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final items =
          (raw['items'] ?? unwrapData(res.data)['items']) as List<dynamic>? ??
          [];
      state = state.copyWith(
        isLoading: false,
        drafts: items.cast<Map<String, dynamic>>(),
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  // 8. Load all drafts across matters (History/Drafting view)
  Future<void> loadAllDrafts() async {
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get('/drafts');
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final items =
          (raw['items'] ?? unwrapData(res.data)['items']) as List<dynamic>? ??
          [];
      state = state.copyWith(allDrafts: items.cast<Map<String, dynamic>>());
    } catch (_) {
      // Non-fatal — the list stays empty.
    }
  }
}

final draftsControllerProvider =
    StateNotifierProvider<DraftsController, DraftsState>((ref) {
      return DraftsController(ref);
    });
