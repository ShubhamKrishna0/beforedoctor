import 'package:beforedoctor/core/constants/colors.dart';
import 'package:beforedoctor/features/chat/domain/entities/conversation_phase.dart';
import 'package:flutter/material.dart';

class ConversationPhaseIndicator extends StatelessWidget {
  const ConversationPhaseIndicator({
    super.key,
    required this.phase,
  });

  final ConversationPhase phase;

  @override
  Widget build(BuildContext context) {
    final label = switch (phase) {
      ConversationPhase.gathering => 'Gathering information…',
      ConversationPhase.responding => 'Providing response',
      ConversationPhase.followUp => 'Follow-up',
    };

    final color = switch (phase) {
      ConversationPhase.gathering => AppColors.warningOrange,
      ConversationPhase.responding => AppColors.medicalGreen,
      ConversationPhase.followUp => AppColors.primaryBlue,
    };

    return Chip(
      avatar: Icon(Icons.circle, size: 10, color: color),
      label: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
      backgroundColor: color.withValues(alpha: 0.1),
      side: BorderSide.none,
      padding: const EdgeInsets.symmetric(horizontal: 4),
    );
  }
}
