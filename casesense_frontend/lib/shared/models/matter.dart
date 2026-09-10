class Matter {
  final String id;
  final String title;
  final String? caseNumber;
  final String? court;
  final String status;
  final String? clientRef;

  Matter({
    required this.id,
    required this.title,
    this.caseNumber,
    this.court,
    required this.status,
    this.clientRef,
  });

  factory Matter.fromJson(Map<String, dynamic> json) {
    return Matter(
      id: json['id'],
      title: json['title'],
      caseNumber: json['case_number'],
      court: json['court'],
      status: json['status'],
      clientRef: json['client_ref'],
    );
  }
}