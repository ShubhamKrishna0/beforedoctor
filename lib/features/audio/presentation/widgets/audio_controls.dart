import 'package:flutter/material.dart';

class AudioControls extends StatelessWidget {
  const AudioControls({
    super.key,
    required this.isPlaying,
    required this.isMuted,
    required this.onPlayPause,
    required this.onMuteToggle,
  });

  final bool isPlaying;
  final bool isMuted;
  final VoidCallback onPlayPause;
  final VoidCallback onMuteToggle;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton.filledTonal(
          onPressed: onPlayPause,
          icon: Icon(isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded),
        ),
        const SizedBox(width: 8),
        IconButton.filledTonal(
          onPressed: onMuteToggle,
          icon: Icon(isMuted ? Icons.volume_off_rounded : Icons.volume_up_rounded),
        ),
      ],
    );
  }
}
