class ApiException implements Exception {
  final String code;
  final String message;
  final Map<String, dynamic>? details;
  final String? traceId;

  ApiException({
    required this.code,
    required this.message,
    this.details,
    this.traceId,
  });

  factory ApiException.fromJson(Map<String, dynamic> json) {
    final error = json['error'] ?? {};
    return ApiException(
      code: error['code'] ?? 'UNKNOWN_ERROR',
      message: error['message'] ?? 'An unexpected error occurred.',
      details: error['details'],
      traceId: json['trace_id'],
    );
  }

  @override
  String toString() => message;
}