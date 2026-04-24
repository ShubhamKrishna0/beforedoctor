import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';

class ClarifyingQuestionsCard extends StatelessWidget {
  const ClarifyingQuestionsCard({
    super.key,
    required this.questions,
  });

  final List<String> questions;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFFEDE7F6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Clarifying Questions',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.primaryBlue,
                  ),
            ),
            const SizedBox(height: 12),
            for (final question in questions)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.help_outline,
                      size: 20,
                      color: Color(0xFF7C4DFF),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        question,
                        style: const TextStyle(color: AppColors.ink),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
