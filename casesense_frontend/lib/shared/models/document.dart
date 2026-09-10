class Document {
  final String id;
  final String fileName;
  final String status;
  final int? pageCount;
  final String? errorReason;

  Document({
    required this.id,
    required this.fileName,
    required this.status,
    this.pageCount,
    this.errorReason,
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'],
      fileName: json['file_name'],
      status: json['status'],
      pageCount: json['page_count'],
      errorReason: json['error_reason'],
    );
  }
}