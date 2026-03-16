import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';

class TranscriptEditorCard extends StatefulWidget {
  const TranscriptEditorCard({
    super.key,
    required this.controller,
    required this.onApply,
  });

  final TextEditingController controller;
  final VoidCallback onApply;

  @override
  State<TranscriptEditorCard> createState() => _TranscriptEditorCardState();
}

class _TranscriptEditorCardState extends State<TranscriptEditorCard> {
  final FocusNode _focusNode = FocusNode();

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isEmpty = widget.controller.text.trim().isEmpty;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'Transcript',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: () => _focusNode.requestFocus(),
                  icon: const Icon(Icons.edit_rounded, size: 18),
                  label: const Text('Edit'),
                ),
                const SizedBox(width: 4),
                FilledButton.icon(
                  onPressed: isEmpty ? null : widget.onApply,
                  icon: const Icon(Icons.send_rounded, size: 18),
                  label: const Text('Send'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: widget.controller,
              focusNode: _focusNode,
              maxLines: 5,
              decoration: InputDecoration(
                filled: true,
                fillColor: AppColors.surface,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(18),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
