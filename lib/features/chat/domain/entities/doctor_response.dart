class DoctorResponse {
  const DoctorResponse({
    required this.summaryOfSymptoms,
    required this.possibleCauses,
    required this.immediateAdvice,
    required this.lifestyleSuggestions,
    required this.warningSigns,
    required this.whenToSeeARealDoctor,
    required this.medicalDisclaimer,
    required this.followUpQuestions,
    this.audioResponseUrl,
  });

  final String summaryOfSymptoms;
  final List<String> possibleCauses;
  final List<String> immediateAdvice;
  final List<String> lifestyleSuggestions;
  final List<String> warningSigns;
  final String whenToSeeARealDoctor;
  final String medicalDisclaimer;
  final List<String> followUpQuestions;
  final String? audioResponseUrl;
}
