import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

class ResearchListState {
  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> sessions;

  ResearchListState({
    this.isLoading = false,
    this.error,
    this.sessions = const [],
  });

  ResearchListState copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? sessions,
  }) {
    return ResearchListState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      sessions: sessions ?? this.sessions,
    );
  }
}

class ResearchListController extends StateNotifier<ResearchListState> {
  final Ref ref;

  ResearchListController(this.ref) : super(ResearchListState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get(Endpoints.listResearch);
      final raw = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
      final items = (raw['items'] ?? unwrapData(res.data)['items']) as List<dynamic>? ?? [];
      state = state.copyWith(
        isLoading: false,
        sessions: items.cast<Map<String, dynamic>>(),
      );
    } on DioException catch (e) {
      state = state.copyWith(isLoading: false, error: e.error?.toString() ?? e.message);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final researchListControllerProvider = StateNotifierProvider<ResearchListController, ResearchListState>((ref) {
  return ResearchListController(ref);
});
