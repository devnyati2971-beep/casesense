import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

class SavedCitationsState {
  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> citations;
  final String filter; // all / judgment / act / article / other
  final String searchQuery;

  SavedCitationsState({
    this.isLoading = false,
    this.error,
    this.citations = const [],
    this.filter = 'all',
    this.searchQuery = '',
  });

  SavedCitationsState copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? citations,
    String? filter,
    String? searchQuery,
  }) {
    return SavedCitationsState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      citations: citations ?? this.citations,
      filter: filter ?? this.filter,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class SavedCitationsController extends StateNotifier<SavedCitationsState> {
  final Ref ref;

  SavedCitationsController(this.ref) : super(SavedCitationsState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final query = <String, dynamic>{
        'citation_type': state.filter,
        if (state.searchQuery.isNotEmpty) 'q': state.searchQuery,
      };
      final res = await dio.get(
        Endpoints.savedCitations,
        queryParameters: query,
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final items =
          (raw['items'] ?? unwrapData(res.data)['items']) as List<dynamic>? ??
          [];
      state = state.copyWith(
        isLoading: false,
        citations: items.cast<Map<String, dynamic>>(),
      );
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.error?.toString() ?? e.message,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> setFilter(String type) async {
    state = state.copyWith(filter: type);
    await load();
  }

  Future<void> search(String query) async {
    state = state.copyWith(searchQuery: query);
    await load();
  }

  Future<bool> saveCitation(Map<String, dynamic> data) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(Endpoints.savedCitations, data: data);
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final saved = raw.containsKey('id') ? raw : unwrapData(res.data);
      state = state.copyWith(
        isLoading: false,
        citations: [saved, ...state.citations],
      );
      return true;
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      state = state.copyWith(
        isLoading: false,
        error: code == 409 ? 'Already saved.' : 'Failed to save citation.',
      );
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  Future<bool> removeCitation(String id) async {
    try {
      final dio = ref.read(dioProvider);
      await dio.delete(Endpoints.savedCitationDetail(id));
      state = state.copyWith(
        citations: state.citations.where((c) => c['id'] != id).toList(),
      );
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  Future<bool> updateNote(String id, {String? note, String? label}) async {
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.patch(
        Endpoints.savedCitationDetail(id),
        data: {
          if (note != null) 'note': note,
          if (label != null) 'label': label,
        },
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final updated = raw.containsKey('id') ? raw : unwrapData(res.data);
      state = state.copyWith(
        citations: state.citations
            .map((c) => c['id'] == id ? updated : c)
            .toList(),
      );
      return true;
    } catch (e) {
      return false;
    }
  }
}

final savedCitationsControllerProvider =
    StateNotifierProvider<SavedCitationsController, SavedCitationsState>((ref) {
      return SavedCitationsController(ref);
    });
