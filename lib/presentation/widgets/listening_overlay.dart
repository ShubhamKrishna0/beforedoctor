import 'package:beforedoctor/shared/widgets/animated_mic_button.dart';
import 'package:flutter/material.dart';
import 'package:waveform_flutter/waveform_flutter.dart';


Future<void> showListeningOverlay({
  required BuildContext context,
  required Stream<Amplitude> amplitudeStream,
  required VoidCallback onStop,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    isDismissible: false,
    enableDrag: false,
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) => Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'Listening...',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 80,
            child: AnimatedWaveList(stream: amplitudeStream),
          ),
          const SizedBox(height: 12),
          AnimatedMicButton(
            recording: true,
            onTap: onStop,
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: onStop,
            child: const Text('Stop'),
          ),
        ],
      ),
    ),
  );
}
