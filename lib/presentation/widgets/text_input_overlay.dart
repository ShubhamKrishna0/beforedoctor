import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';


Future<String?> showTextInputOverlay(BuildContext context) async {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) => const _TextInputSheet(),
  );
}

class _TextInputSheet extends StatefulWidget {
  const _TextInputSheet();

  @override
  State<_TextInputSheet> createState() => _TextInputSheetState();
}

class _TextInputSheetState extends State<_TextInputSheet> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        24 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _controller,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: 'Write your message',
              filled: true,
              fillColor: AppColors.surface,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel'),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: () {
                  final text = _controller.text.trim();
                  if (text.isEmpty) {
                    return;
                  }
                  Navigator.pop(context, text);
                },
                child: const Text('Send'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
