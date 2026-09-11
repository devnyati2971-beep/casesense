import 'package:dio/dio.dart';
import 'dart:typed_data';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/legacy.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';

// State to hold the specific matter's data and its uploaded documents
class MatterState {
  final bool isLoading;
  final String? error;
  final Map<String, dynamic>? matterData;
  final List<Map<String, dynamic>> documents;

  MatterState({
    this.isLoading = false,
    this.error,
    this.matterData,
    this.documents = const [],
  });

  MatterState copyWith({
    bool? isLoading,
    String? error,
    Map<String, dynamic>? matterData,
    List<Map<String, dynamic>>? documents,
  }) {
    return MatterState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      matterData: matterData ?? this.matterData,
      documents: documents ?? this.documents,
    );
  }
}

class MatterController extends StateNotifier<MatterState> {
  final Ref ref;

  MatterController(this.ref) : super(MatterState());

  // 1. Fetch Matter Details (GET /matters/{id}) + documents
  Future<void> loadMatter(String matterId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);

      final matterRes = await dio.get(Endpoints.matterDetail(matterId));
      final matter = unwrapData(matterRes.data);

      List<Map<String, dynamic>> docs = [];
      try {
        final docsRes = await dio.get(Endpoints.matterDocuments(matterId));
        final raw = docsRes.data is Map<String, dynamic>
            ? docsRes.data as Map<String, dynamic>
            : <String, dynamic>{};
        final items =
            (raw['items'] ?? unwrapData(docsRes.data)['items'])
                as List<dynamic>? ??
            [];
        docs = items.cast<Map<String, dynamic>>();
      } catch (_) {
        // Document list is optional — don't fail the whole load.
      }

      state = state.copyWith(
        isLoading: false,
        matterData: matter,
        documents: docs,
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

  // 2. Upload Document (POST /matters/{id}/documents)
  Future<bool> uploadDocument(
    String matterId,
    String filePath,
    String fileName,
  ) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final form = FormData.fromMap({
        'file': await MultipartFile.fromFile(filePath, filename: fileName),
      });
      final res = await dio.post(
        Endpoints.matterDocuments(matterId),
        data: form,
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final doc =
          (raw['document'] ?? unwrapData(res.data)['document'])
              as Map<String, dynamic>?;

      state = state.copyWith(
        isLoading: false,
        documents: [if (doc != null) doc, ...state.documents],
      );
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  /// Uploads browser-picked or desktop-picked bytes. This avoids relying on a
  /// local file path, which is unavailable in Flutter web.
  Future<bool> uploadDocumentBytes(
    String matterId,
    Uint8List bytes,
    String fileName,
  ) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final dio = ref.read(dioProvider);
      final form = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          bytes,
          filename: fileName,
          contentType: _contentTypeFor(fileName),
        ),
      });
      final res = await dio.post(
        Endpoints.matterDocuments(matterId),
        data: form,
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final doc =
          (raw['document'] ?? unwrapData(res.data)['document'])
              as Map<String, dynamic>?;
      state = state.copyWith(
        isLoading: false,
        documents: [if (doc != null) doc, ...state.documents],
      );
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return false;
    }
  }

  DioMediaType _contentTypeFor(String fileName) {
    final extension = fileName.split('.').last.toLowerCase();
    return switch (extension) {
      'pdf' => DioMediaType('application', 'pdf'),
      'docx' => DioMediaType(
        'application',
        'vnd.openxmlformats-officedocument.wordprocessingml.document',
      ),
      'txt' => DioMediaType('text', 'plain'),
      'jpg' || 'jpeg' => DioMediaType('image', 'jpeg'),
      'png' => DioMediaType('image', 'png'),
      _ => DioMediaType('application', 'octet-stream'),
    };
  }

  // 3. Delete (soft) document
  Future<bool> deleteDocument(String docId) async {
    try {
      final dio = ref.read(dioProvider);
      await dio.delete('/documents/$docId');
      state = state.copyWith(
        documents: state.documents.where((d) => d['id'] != docId).toList(),
      );
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  // 4. Refresh document status (polling after upload)
  Future<void> refreshDocumentStatus(String docId) async {
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get('/documents/$docId/status');
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final status = raw['status'] ?? unwrapData(res.data)['status'];
      state = state.copyWith(
        documents: state.documents.map((d) {
          return d['id'] == docId ? {...d, 'status': status} : d;
        }).toList(),
      );
    } catch (_) {}
  }
}

// Family provider so we can pass the matterId
final matterControllerProvider =
    StateNotifierProvider.family<MatterController, MatterState, String>((
      ref,
      matterId,
    ) {
      return MatterController(ref)..loadMatter(matterId);
    });
