import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

// Represents the state of selected authorities for a specific session/matter
class AuthoritiesState {
  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> selectedAuthorities;

  AuthoritiesState({
    this.isLoading = false,
    this.error,
    this.selectedAuthorities = const [],
  });

  AuthoritiesState copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? selectedAuthorities,
  }) {
    return AuthoritiesState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      selectedAuthorities: selectedAuthorities ?? this.selectedAuthorities,
    );
  }
}

class AuthoritiesController extends StateNotifier<AuthoritiesState> {
  final Ref ref;

  AuthoritiesController(this.ref) : super(AuthoritiesState());

  // 1. Select an Authority (POST /research/{sid}/authorities)
  Future<bool> selectAuthority(
    String sessionId,
    String propositionId,
    String judgmentId,
    Map<String, dynamic> authorityData,
  ) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(
        Endpoints.selectAuthority(sessionId),
        data: {
          'proposition_id': propositionId,
          'judgment_id': judgmentId,
        },
      );
      final raw = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
      final authority = raw.containsKey('id') ? raw : unwrapData(res.data);

      state = state.copyWith(
        isLoading: false,
        selectedAuthorities: [...state.selectedAuthorities, authority],
      );
      return true;
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      state = state.copyWith(
        isLoading: false,
        error: status == 409 ? 'This authority is already selected.' : 'Failed to select authority.',
      );
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Failed to select authority.');
      return false;
    }
  }

  // 2. Add Note to Authority (POST /authorities/{id}/notes)
  Future<bool> addNote(String authorityId, String noteBody) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      await dio.post(
        Endpoints.authorityNotes(authorityId),
        data: {'body': noteBody},
      );
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Failed to add note.');
      return false;
    }
  }

  // 3. Deselect Authority (DELETE /authorities/{id})
  Future<void> removeAuthority(String authorityId) async {
    try {
      final dio = ref.read(dioProvider);
      await dio.delete(Endpoints.authorityDetail(authorityId));
    } catch (_) {}
    state = state.copyWith(
      selectedAuthorities: state.selectedAuthorities.where((a) => a['id'] != authorityId).toList(),
    );
  }
}

final authoritiesControllerProvider = StateNotifierProvider<AuthoritiesController, AuthoritiesState>((ref) {
  return AuthoritiesController(ref);
});