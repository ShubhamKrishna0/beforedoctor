import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';

class SmartAlertBanner extends StatelessWidget {
  const SmartAlertBanner({
    super.key,
    required this.alerts,
  });

  final List<String> alerts;

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.warningOrange.withValues(alpha: 0.15),
        border: Border.all(color: AppColors.warningOrange),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.notifications_active, size: 20, color: AppColors.warningOrange),
              const SizedBox(width: 8),
              Text(
                'Recurring Symptom Alert',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.warningOrange,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          for (final alert in alerts)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '• $alert',
                style: const TextStyle(color: AppColors.ink),
              ),
            ),
        ],
      ),
    );
  }
}
