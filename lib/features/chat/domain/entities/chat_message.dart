import 'package:beforedoctor/features/chat/domain/entities/doctor_response.dart';


class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    required this.timestamp,
    this.response,
  });

  final String id;
  final String role;
  final String text;
  final DateTime timestamp;
  final DoctorResponse? response;
}
