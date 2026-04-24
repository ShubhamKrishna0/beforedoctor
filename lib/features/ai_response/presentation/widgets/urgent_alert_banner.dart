import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';

class UrgentAlertBanner extends StatelessWidget {
  const UrgentAlertBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.danger,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 24),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Urgent: Your symptoms may require immediate medical attention. '
              'Please seek emergency care.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
