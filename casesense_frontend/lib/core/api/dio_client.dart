import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'endpoints.dart';
import '../storage/secure_storage.dart';
import 'api_exception.dart';

final dioProvider = Provider<Dio>((ref) {
  final storage = ref.watch(secureStorageProvider);

  final dio = Dio(BaseOptions(
    baseUrl: Endpoints.baseUrl,
    connectTimeout: const Duration(seconds: 15), // As per Blueprint
    receiveTimeout: const Duration(seconds: 30),
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final token = await storage.getAccessToken();
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      return handler.next(options);
    },
    onError: (DioException e, handler) async {
      // 401 Token Refresh Logic
      if (e.response?.statusCode == 401 &&
          !e.requestOptions.path.contains(Endpoints.refresh) &&
          !e.requestOptions.path.contains(Endpoints.login)) {
        final refreshToken = await storage.getRefreshToken();
        if (refreshToken != null) {
          try {
            // Attempt to refresh using the same dio (keeps baseUrl + interceptor chain)
            final res = await dio.post(Endpoints.refresh, data: {'refresh_token': refreshToken});
            final data = (res.data is Map<String, dynamic>) ? res.data['data'] as Map<String, dynamic>? : null;
            final access = data?['access_token'];
            final refresh = data?['refresh_token'];
            if (access == null) {
              throw DioException(requestOptions: e.requestOptions, message: 'Refresh failed');
            }
            await storage.saveTokens(access, refresh ?? refreshToken);
            // Retry original request
            e.requestOptions.headers['Authorization'] = 'Bearer $access';
            final retry = await dio.fetch(e.requestOptions);
            return handler.resolve(retry);
          } catch (_) {
            await storage.clearTokens(); // Refresh failed, force logout
          }
        }
      }

      // Map standard error envelope
      if (e.response?.data != null && e.response?.data is Map<String, dynamic>) {
        return handler.reject(DioException(
          requestOptions: e.requestOptions,
          error: ApiException.fromJson(e.response!.data),
        ));
      }
      return handler.next(e);
    },
  ));

  return dio;
});

/// Helper to unwrap the standard `{success, data, message}` envelope.
Map<String, dynamic> unwrapData(dynamic responseData) {
  if (responseData is Map<String, dynamic>) {
    final data = responseData['data'];
    if (data is Map<String, dynamic>) return data;
  }
  return <String, dynamic>{};
}