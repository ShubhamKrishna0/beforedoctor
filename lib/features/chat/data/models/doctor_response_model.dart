import 'package:beforedoctor/features/chat/domain/entities/doctor_response.dart';

class DoctorResponseModel extends DoctorResponse {
  const DoctorResponseModel({
    required super.summaryOfSymptoms,
    required super.possibleCauses,
    required super.immediateAdvice,
    required super.lifestyleSuggestions,
    required super.warningSigns,
    required super.whenToSeeARealDoctor,
    required super.medicalDisclaimer,
    required super.followUpQuestions,
    super.audioResponseUrl,
    super.conversationSummary,
  });

  factory DoctorResponseModel.fromJson(Map<String, dynamic> json) {
    final response = json['response'] as Map<String, dynamic>? ?? json;
    return DoctorResponseModel(
      summaryOfSymptoms: response['summary_of_symptoms'] as String? ?? '',
      possibleCauses:
          List<String>.from(response['possible_causes'] as List? ?? const []),
      immediateAdvice:
          List<String>.from(response['immediate_advice'] as List? ?? const []),
      lifestyleSuggestions: List<String>.from(
        response['lifestyle_suggestions'] as List? ?? const [],
      ),
      warningSigns:
          List<String>.from(response['warning_signs'] as List? ?? const []),
      whenToSeeARealDoctor:
          response['when_to_see_a_real_doctor'] as String? ?? '',
      medicalDisclaimer: response['medical_disclaimer'] as String? ?? '',
      followUpQuestions: List<String>.from(
        response['follow_up_questions'] as List? ?? const [],
      ),
      audioResponseUrl: json['audio_response_url'] as String?,
      conversationSummary: response['conversation_summary'] as String?,
    );
  }
}
