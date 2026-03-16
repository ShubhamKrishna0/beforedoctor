import 'package:beforedoctor/core/constants/colors.dart';
import 'package:beforedoctor/presentation/bloc/chat_cubit.dart';
import 'package:beforedoctor/presentation/bloc/chat_state.dart';
import 'package:beforedoctor/shared/widgets/animated_mic_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';


class VoiceInputBar extends StatelessWidget {
  const VoiceInputBar({
    super.key,
    required this.onEditTap,
  });

  final VoidCallback onEditTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: BlocBuilder<ChatCubit, ChatState>(
        builder: (context, state) {
          return Row(
            children: [
              GestureDetector(
                onHorizontalDragEnd: (details) {
                  if (details.primaryVelocity == null) {
                    return;
                  }
                  if (details.primaryVelocity! > 0) {
                    context.read<ChatCubit>().startRecording();
                  } else if (details.primaryVelocity! < 0) {
                    context.read<ChatCubit>().stopRecording();
                  }
                },
                child: AnimatedMicButton(
                  recording: state.recording,
                  onTap: () {
                    if (state.recording) {
                      context.read<ChatCubit>().stopRecording();
                    } else {
                      context.read<ChatCubit>().startRecording();
                    }
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: AnimatedOpacity(
                  opacity: state.recording ? 1 : 0,
                  duration: const Duration(milliseconds: 200),
                  child: _ListeningWave(active: state.recording),
                ),
              ),
              const SizedBox(width: 16),
              IconButton.filledTonal(
                onPressed: onEditTap,
                icon: const Icon(Icons.edit_rounded),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ListeningWave extends StatelessWidget {
  const _ListeningWave({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      height: 36,
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: active
            ? AppColors.primaryBlue.withValues(alpha: 0.08)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(18),
      ),
      child: active
          ? Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _Bar(height: 10),
                _Bar(height: 18),
                _Bar(height: 14),
                _Bar(height: 22),
                _Bar(height: 12),
              ],
            )
          : const SizedBox.shrink(),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 240),
      margin: const EdgeInsets.symmetric(horizontal: 4),
      width: 4,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.primaryBlue,
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }
}
