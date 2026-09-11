import 'dart:async';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

// State class to hold our research data and loading status
class ResearchState {
  final bool isLoading;
  final String? sessionId;
  final String? error;
  final String currentStage;
  final Map<String, dynamic>? results;

  /// True when the guest used both free searches (429 from the backend) —
  /// the UI shows the register CTA instead of an error.
  final bool guestLimitReached;

  ResearchState({
    this.isLoading = false,
    this.sessionId,
    this.error,
    this.currentStage = 'CREATED',
    this.results,
    this.guestLimitReached = false,
  });

  ResearchState copyWith({
    bool? isLoading,
    String? sessionId,
    String? error,
    String? currentStage,
    Map<String, dynamic>? results,
    bool clearResults = false,
    bool? guestLimitReached,
  }) {
    return ResearchState(
      isLoading: isLoading ?? this.isLoading,
      sessionId: sessionId ?? this.sessionId,
      error: error,
      currentStage: currentStage ?? this.currentStage,
      results: clearResults ? null : (results ?? this.results),
      guestLimitReached: guestLimitReached ?? this.guestLimitReached,
    );
  }
}

// The Controller (Like a Service layer)
class ResearchController extends StateNotifier<ResearchState> {
  final Ref ref;
  Timer? _pollTimer;

  ResearchController(this.ref) : super(ResearchState());

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  // Method called when user clicks "Find" on Citation Finder
  Future<String?> submitQuery(String query, {String? matterId}) async {
    state = state.copyWith(
      isLoading: true,
      error: null,
      guestLimitReached: false,
    );

    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(
        Endpoints.queryResearch,
        data: {'query': query, if (matterId != null) 'matter_id': matterId},
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      // Accepted response is plain {session_id, status_url} — fall back to envelope.
      final data = raw.containsKey('session_id') ? raw : unwrapData(res.data);
      final sessionId = data['session_id']?.toString();

      state = state.copyWith(
        isLoading: false,
        sessionId: sessionId,
        currentStage: 'CREATED',
      );

      return sessionId;
    } on DioException catch (e) {
      // v2.2 guest tier: both free searches used -> 429 with RATE_LIMITED.
      final errCode = (e.response?.data is Map<String, dynamic>)
          ? (((e.response!.data as Map<String, dynamic>)['error'] ?? const {})
                as Map<String, dynamic>)['code']
          : null;
      if (e.response?.statusCode == 429 && errCode == 'RATE_LIMITED') {
        state = state.copyWith(isLoading: false, guestLimitReached: true);
        return null;
      }
      final message = (e.error is Exception)
          ? e.error.toString()
          : (e.message ?? 'Research failed.');
      state = state.copyWith(isLoading: false, error: message);
      return null;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return null;
    }
  }

  Future<String?> submitDocument(Uint8List bytes, String fileName) async {
    state = state.copyWith(
      isLoading: true,
      error: null,
      guestLimitReached: false,
    );
    try {
      final res = await ref
          .read(dioProvider)
          .post(
            '/research/document',
            data: FormData.fromMap({
              'file': MultipartFile.fromBytes(bytes, filename: fileName),
            }),
          );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final data = raw.containsKey('session_id') ? raw : unwrapData(res.data);
      final sessionId = data['session_id']?.toString();
      state = state.copyWith(
        isLoading: false,
        sessionId: sessionId,
        currentStage: 'CREATED',
      );
      return sessionId;
    } catch (error) {
      state = state.copyWith(isLoading: false, error: error.toString());
      return null;
    }
  }

  // Method called by RunStatusScreen to poll for progress
  Future<void> loadSession(String sessionId) async {
    state = state.copyWith(isLoading: true, error: null, sessionId: sessionId);
    try {
      final res = await ref
          .read(dioProvider)
          .get(Endpoints.researchSession(sessionId));
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final data = raw.containsKey('status') ? raw : unwrapData(res.data);
      final status = data['status']?.toString() ?? 'CREATED';
      state = state.copyWith(
        isLoading: false,
        currentStage: status,
        results: data['results'] as Map<String, dynamic>?,
        clearResults: status != 'COMPLETED',
      );
      if (status != 'COMPLETED' && status != 'FAILED') {
        await pollSessionStatus(sessionId);
      }
    } catch (error) {
      state = state.copyWith(isLoading: false, error: error.toString());
    }
  }

  Future<void> pollSessionStatus(String sessionId) async {
    final dio = ref.read(dioProvider);

    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
      try {
        final res = await dio.get(Endpoints.researchSession(sessionId));
        // Status endpoint returns a plain body {status, stage, results, error} —
        // fall back to the envelope when present.
        final raw = res.data is Map<String, dynamic>
            ? res.data as Map<String, dynamic>
            : <String, dynamic>{};
        final data = raw.containsKey('status') ? raw : unwrapData(res.data);
        final status = data['status'] ?? 'CREATED';
        final stage = data['stage'] ?? status;
        final results = data['results'] as Map<String, dynamic>?;

        state = state.copyWith(
          currentStage: status == 'COMPLETED' ? 'COMPLETED' : stage,
          results: results,
        );

        if (status == 'COMPLETED' || status == 'FAILED') {
          timer.cancel();
        }
      } catch (e) {
        timer.cancel();
        state = state.copyWith(error: e.toString());
      }
    });
  }
}

// Provider that the UI will listen to
final researchControllerProvider =
    StateNotifierProvider<ResearchController, ResearchState>((ref) {
      return ResearchController(ref);
    });
