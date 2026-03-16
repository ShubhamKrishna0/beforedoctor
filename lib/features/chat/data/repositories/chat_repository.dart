import 'package:beforedoctor/core/network/api_client.dart';
import 'package:beforedoctor/features/chat/data/models/doctor_response_model.dart';

class ChatRepository {
  ChatRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<DoctorResponseModel> sendMessage(String text) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/chat/message',
      data: {
        'text': text,
        'generate_audio': true,
      },
    );
    return DoctorResponseModel.fromJson(response.data ?? <String, dynamic>{});
  }
}
