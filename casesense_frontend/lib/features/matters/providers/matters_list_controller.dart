import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

class MattersListState {
  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> matters;
  final String filter; // active / archived / deleted

  MattersListState({
    this.isLoading = false,
    this.error,
    this.matters = const [],
    this.filter = 'active',
  });

  MattersListState copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? matters,
    String? filter,
  }) {
    return MattersListState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      matters: matters ?? this.matters,
      filter: filter ?? this.filter,
    );
  }
}

class MattersListController extends StateNotifier<MattersListState> {
  final Ref ref;

  MattersListController(this.ref) : super(MattersListState()) {
    load();
  }

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get(Endpoints.matters, queryParameters: {'status': state.filter});
      final raw = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
      final items = (raw['items'] ?? unwrapData(res.data)['items']) as List<dynamic>? ?? [];
      state = state.copyWith(
        isLoading: false,
        matters: items.cast<Map<String, dynamic>>(),
      );
    } on DioException catch (e) {
      state = state.copyWith(isLoading: false, error: e.error?.toString() ?? e.message);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<String?> createMatter({required String title, String? caseNumber, String? courtName, String? matterType}) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(Endpoints.matters, data: {
        'title': title,
        if (caseNumber != null) 'case_number': caseNumber,
        if (courtName != null) 'court_name': courtName,
        if (matterType != null) 'matter_type': matterType,
      });
      final raw = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
      final matter = raw.containsKey('id') ? raw : unwrapData(res.data);
      state = state.copyWith(
        isLoading: false,
        matters: [matter, ...state.matters],
      );
      return matter['id']?.toString();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return null;
    }
  }

  Future<void> setFilter(String filter) async {
    state = state.copyWith(filter: filter);
    await load();
  }
}

final mattersListControllerProvider = StateNotifierProvider<MattersListController, MattersListState>((ref) {
  return MattersListController(ref);
});