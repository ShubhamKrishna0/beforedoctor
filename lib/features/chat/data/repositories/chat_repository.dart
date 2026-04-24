import 'package:beforedoctor/core/network/api_client.dart';
import 'package:beforedoctor/features/chat/data/models/chat_message_response_model.dart';

class ChatRepository {
  ChatRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<ChatMessageResponseModel> sendMessage(
    String text, {
    String? conversationId,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/chat/message',
      data: {
        'text': text,
        'generate_audio': true,
        if (conversationId != null) 'conversation_id': conversationId,
      },
    );
    return ChatMessageResponseModel.fromJson(
      response.data ?? <String, dynamic>{},
    );
  }
}
