import 'package:beforedoctor/core/constants/colors.dart';
import 'package:beforedoctor/core/network/api_client.dart';
import 'package:flutter/material.dart';

class FeedbackButtons extends StatefulWidget {
  const FeedbackButtons({
    super.key,
    required this.aiResponseId,
    required this.apiClient,
  });

  final String aiResponseId;
  final ApiClient apiClient;

  @override
  State<FeedbackButtons> createState() => _FeedbackButtonsState();
}

class _FeedbackButtonsState extends State<FeedbackButtons> {
  int? _selectedRating;

  Future<void> _submitFeedback(int rating) async {
    setState(() => _selectedRating = rating);
    try {
      await widget.apiClient.dio.post(
        '/api/v1/feedback',
        data: {
          'ai_response_id': widget.aiResponseId,
          'rating': rating,
        },
      );
    } catch (_) {
      // Feedback submission is non-critical; keep the visual state.
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          icon: Icon(
            _selectedRating == 1 ? Icons.thumb_up : Icons.thumb_up_outlined,
            color: _selectedRating == 1 ? AppColors.medicalGreen : AppColors.ink,
            size: 20,
          ),
          onPressed: _selectedRating == null ? () => _submitFeedback(1) : null,
          tooltip: 'Helpful',
        ),
        IconButton(
          icon: Icon(
            _selectedRating == -1 ? Icons.thumb_down : Icons.thumb_down_outlined,
            color: _selectedRating == -1 ? AppColors.danger : AppColors.ink,
            size: 20,
          ),
          onPressed: _selectedRating == null ? () => _submitFeedback(-1) : null,
          tooltip: 'Not helpful',
        ),
      ],
    );
  }
}
