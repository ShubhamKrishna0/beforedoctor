import 'dart:io';

import 'package:beforedoctor/core/network/api_client.dart';
import 'package:dio/dio.dart';

class AudioRepository {
  AudioRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<Map<String, dynamic>> transcribeAudio(File file) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(file.path),
    });
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/audio/transcribe',
      data: formData,
    );
    return response.data ?? <String, dynamic>{};
  }
}
