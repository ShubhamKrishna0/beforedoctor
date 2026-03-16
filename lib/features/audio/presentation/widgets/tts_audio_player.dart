import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';


class TtsAudioPlayer extends StatefulWidget {
  const TtsAudioPlayer({
    super.key,
    required this.url,
  });

  final String url;

  @override
  State<TtsAudioPlayer> createState() => _TtsAudioPlayerState();
}

class _TtsAudioPlayerState extends State<TtsAudioPlayer> {
  final AudioPlayer _player = AudioPlayer();
  bool _loading = true;
  bool _error = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      setState(() {
        _loading = true;
        _error = false;
      });
      await _player.setUrl(widget.url);
      setState(() {
        _loading = false;
      });
    } catch (_) {
      setState(() {
        _loading = false;
        _error = true;
      });
    }
  }

  @override
  void didUpdateWidget(covariant TtsAudioPlayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.url != widget.url) {
      _player.stop();
      _load();
    }
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error) {
      return const Text(
        'Audio unavailable',
        style: TextStyle(fontSize: 12),
      );
    }
    return Row(
      children: [
        if (_loading)
          const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        else
          StreamBuilder<PlayerState>(
            stream: _player.playerStateStream,
            builder: (context, snapshot) {
              final state = snapshot.data;
              final playing = state?.playing ?? false;
              return IconButton.filledTonal(
                onPressed: () {
                  if (playing) {
                    _player.pause();
                  } else {
                    _player.play();
                  }
                },
                icon: Icon(playing ? Icons.pause_rounded : Icons.play_arrow_rounded),
              );
            },
          ),
        const SizedBox(width: 8),
        const Text(
          'Listen',
          style: TextStyle(fontSize: 12),
        ),
      ],
    );
  }
}
