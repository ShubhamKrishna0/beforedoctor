import 'package:beforedoctor/core/constants/colors.dart';
import 'package:beforedoctor/features/audio/presentation/widgets/tts_audio_player.dart';
import 'package:beforedoctor/features/chat/domain/entities/doctor_response.dart';
import 'package:flutter/material.dart';

class StructuredResponseCard extends StatelessWidget {
  const StructuredResponseCard({
    super.key,
    required this.response,
  });

  final DoctorResponse response;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Section(title: 'Summary of Symptoms', content: response.summaryOfSymptoms),
            _BulletSection(title: 'Possible Causes', items: response.possibleCauses),
            _BulletSection(title: 'Immediate Advice', items: response.immediateAdvice),
            _BulletSection(
              title: 'Lifestyle Suggestions',
              items: response.lifestyleSuggestions,
            ),
            _BulletSection(
              title: 'Warning Signs',
              items: response.warningSigns,
              accent: AppColors.warningOrange,
            ),
            _Section(
              title: 'When to See a Real Doctor',
              content: response.whenToSeeARealDoctor,
            ),
            _Section(
              title: 'Medical Disclaimer',
              content: response.medicalDisclaimer,
              accent: AppColors.danger,
            ),
            if (response.followUpQuestions.isNotEmpty)
              _BulletSection(
                title: 'Follow-up Questions',
                items: response.followUpQuestions,
              ),
            if (response.audioResponseUrl != null) ...[
              const SizedBox(height: 8),
              TtsAudioPlayer(url: response.audioResponseUrl!),
            ],
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.content,
    this.accent = AppColors.primaryBlue,
  });

  final String title;
  final String content;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: accent,
                ),
          ),
          const SizedBox(height: 8),
          Text(content),
        ],
      ),
    );
  }
}

class _BulletSection extends StatelessWidget {
  const _BulletSection({
    required this.title,
    required this.items,
    this.accent = AppColors.medicalGreen,
  });

  final String title;
  final List<String> items;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: accent,
                ),
          ),
          const SizedBox(height: 8),
          for (final item in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text('• $item'),
            ),
        ],
      ),
    );
  }
}
