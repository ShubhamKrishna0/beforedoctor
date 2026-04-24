import 'package:beforedoctor/features/chat/data/models/doctor_response_model.dart';

class ChatMessageResponseModel {
  const ChatMessageResponseModel({
    required this.conversationId,
    required this.phase,
    this.questions,
    this.response,
    this.audioResponseUrl,
    this.isUrgent = false,
    this.smartAlerts = const [],
  });

  final String conversationId;
  final String phase;
  final List<String>? questions;
  final DoctorResponseModel? response;
  final String? audioResponseUrl;
  final bool isUrgent;
  final List<String> smartAlerts;

  factory ChatMessageResponseModel.fromJson(Map<String, dynamic> json) {
    final responseData = json['response'] as Map<String, dynamic>?;
    DoctorResponseModel? doctorResponse;
    if (responseData != null) {
      doctorResponse = DoctorResponseModel.fromJson({
        'response': responseData,
        'audio_response_url': json['audio_response_url'],
      });
    }

    return ChatMessageResponseModel(
      conversationId: json['conversation_id'] as String? ?? '',
      phase: json['phase'] as String? ?? 'gathering',
      questions: (json['questions'] as List?)
          ?.map((e) => e as String)
          .toList(),
      response: doctorResponse,
      audioResponseUrl: json['audio_response_url'] as String?,
      isUrgent: json['is_urgent'] as bool? ?? false,
      smartAlerts: List<String>.from(
        json['smart_alerts'] as List? ?? const [],
      ),
    );
  }
}
