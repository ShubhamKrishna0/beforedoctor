import 'package:beforedoctor/features/transcript/presentation/widgets/transcript_editor_card.dart';
import 'package:flutter/material.dart';


Future<void> showTranscriptOverlay({
  required BuildContext context,
  required TextEditingController controller,
  required VoidCallback onSend,
  required VoidCallback onCancel,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) => Padding(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        24 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TranscriptEditorCard(
            controller: controller,
            onApply: () {
              onSend();
              Navigator.pop(context);
            },
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: () {
                onCancel();
                Navigator.pop(context);
              },
              child: const Text('Cancel'),
            ),
          ),
        ],
      ),
    ),
  );
}
