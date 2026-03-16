import 'package:beforedoctor/features/transcript/presentation/widgets/transcript_editor_card.dart';
import 'package:flutter/material.dart';


class TranscriptEditor extends StatelessWidget {
  const TranscriptEditor({
    super.key,
    required this.controller,
    required this.onSend,
    required this.visible,
  });

  final TextEditingController controller;
  final VoidCallback onSend;
  final bool visible;

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      child: visible
          ? Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
              child: TranscriptEditorCard(
                controller: controller,
                onApply: onSend,
              ),
            )
          : const SizedBox.shrink(),
    );
  }
}
