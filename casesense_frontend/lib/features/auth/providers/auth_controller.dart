import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/api/api_exception.dart';
import '../../../core/storage/secure_storage.dart';

class AuthState {
  final bool isAuthenticated;
  final bool isVerified;
  final Map<String, dynamic>? user;
  AuthState({
    required this.isAuthenticated,
    required this.isVerified,
    this.user,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isVerified,
    Map<String, dynamic>? user,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isVerified: isVerified ?? this.isVerified,
      user: user ?? this.user,
    );
  }
}

class AuthController extends StateNotifier<AsyncValue<AuthState>> {
  final Ref ref;

  AuthController(this.ref) : super(const AsyncValue.loading()) {
    checkAuthStatus();
  }

  String _extractErrorMessage(Object e) {
    if (e is DioException && e.error is ApiException) {
      return (e.error as ApiException).message;
    }
    return e.toString();
  }

  Future<void> checkAuthStatus() async {
    final storage = ref.read(secureStorageProvider);
    final token = await storage.getAccessToken();
    if (token == null) {
      state = AsyncValue.data(AuthState(isAuthenticated: false, isVerified: false));
      return;
    }
    try {
      // Validate the token against the backend and fetch the profile.
      final dio = ref.read(dioProvider);
      final res = await dio.get(Endpoints.me);
      final user = unwrapData(res.data);
      state = AsyncValue.data(AuthState(
        isAuthenticated: true,
        isVerified: user['is_verified'] == true,
        user: user,
      ));
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        await storage.clearTokens();
        state = AsyncValue.data(AuthState(isAuthenticated: false, isVerified: false));
      } else {
        state = AsyncValue.error(_extractErrorMessage(e), StackTrace.current);
      }
    } catch (e, st) {
      state = AsyncValue.error(_extractErrorMessage(e), st);
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(Endpoints.login, data: {'email': email, 'password': password});
      final data = unwrapData(res.data);
      final tokens = (data['tokens'] as Map<String, dynamic>?) ?? {};
      final user = (data['user'] as Map<String, dynamic>?) ?? {};
      await ref.read(secureStorageProvider).saveTokens(
        tokens['access_token'] ?? '',
        tokens['refresh_token'] ?? '',
      );
      state = AsyncValue.data(AuthState(
        isAuthenticated: true,
        isVerified: user['is_verified'] == true,
        user: user,
      ));
    } catch (e, st) {
      state = AsyncValue.error(_extractErrorMessage(e), st);
    }
  }

  Future<bool> register({
    required String fullName,
    required String email,
    required String password,
    String? barCouncilId,
    String? phone,
  }) async {
    state = const AsyncValue.loading();
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(Endpoints.register, data: {
        'full_name': fullName,
        'email': email,
        'password': password,
        if (barCouncilId != null) 'bar_council_id': barCouncilId,
        if (phone != null) 'phone': phone,
      });
      final data = unwrapData(res.data);
      final tokens = (data['tokens'] as Map<String, dynamic>?) ?? {};
      final user = (data['user'] as Map<String, dynamic>?) ?? {};
      await ref.read(secureStorageProvider).saveTokens(
        tokens['access_token'] ?? '',
        tokens['refresh_token'] ?? '',
      );
      state = AsyncValue.data(AuthState(
        isAuthenticated: true,
        isVerified: user['is_verified'] == true,
        user: user,
      ));
      return true;
    } catch (e, st) {
      state = AsyncValue.error(_extractErrorMessage(e), st);
      return false;
    }
  }

  Future<void> logout() async {
    try {
      final dio = ref.read(dioProvider);
      final refreshToken = await ref.read(secureStorageProvider).getRefreshToken();
      if (refreshToken != null) {
        await dio.post(Endpoints.logout, data: {'refresh_token': refreshToken});
      }
    } catch (_) {
      // Ignore network errors on logout — always clear local state.
    }
    await ref.read(secureStorageProvider).clearTokens();
    state = AsyncValue.data(AuthState(isAuthenticated: false, isVerified: false));
  }

  Future<bool> oauthLogin(String code, String stateParam) async {
    state = const AsyncValue.loading();
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post('/auth/oauth/callback', data: {
        'code': code,
        'state': stateParam,
      });
      final data = unwrapData(res.data);
      final tokens = (data['tokens'] as Map<String, dynamic>?) ?? {};
      final user = (data['user'] as Map<String, dynamic>?) ?? {};
      await ref.read(secureStorageProvider).saveTokens(
        tokens['access_token'] ?? '',
        tokens['refresh_token'] ?? '',
      );
      state = AsyncValue.data(AuthState(
        isAuthenticated: true,
        isVerified: user['is_verified'] == true,
        user: user,
      ));
      return true;
    } catch (e, st) {
      state = AsyncValue.error(_extractErrorMessage(e), st);
      return false;
    }
  }

  Future<void> verifyEmail(String token) async {
    // Keep the logged-in user while the verification request is in flight.
    // Reading state after setting loading always produced null and discarded
    // the profile from the sidebar.
    final current = state.value;
    state = const AsyncValue.loading();
    try {
      final dio = ref.read(dioProvider);
      await dio.post(Endpoints.verifyEmail, data: {'token': token});
      state = AsyncValue.data(AuthState(
        isAuthenticated: current?.isAuthenticated ?? true,
        isVerified: true,
        user: current?.user,
      ));
    } catch (e, st) {
      state = AsyncValue.error(_extractErrorMessage(e), st);
    }
  }
}

final authControllerProvider = StateNotifierProvider<AuthController, AsyncValue<AuthState>>((ref) {
  return AuthController(ref);
});
