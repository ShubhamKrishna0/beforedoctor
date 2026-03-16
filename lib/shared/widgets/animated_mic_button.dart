import 'dart:math' as math;

import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';

class AnimatedMicButton extends StatefulWidget {
  const AnimatedMicButton({
    super.key,
    required this.recording,
    required this.onTap,
  });

  final bool recording;
  final VoidCallback onTap;

  @override
  State<AnimatedMicButton> createState() => _AnimatedMicButtonState();
}

class _AnimatedMicButtonState extends State<AnimatedMicButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final wave = 1 + (math.sin(_controller.value * math.pi * 2) * 0.12);
          return SizedBox(
            width: 108,
            height: 108,
            child: Stack(
              alignment: Alignment.center,
              children: [
                for (final factor in [1.65, 1.3])
                  Transform.scale(
                    scale: widget.recording ? wave * factor : factor * 0.82,
                    child: Container(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.primaryBlue.withValues(alpha: 0.10),
                      ),
                    ),
                  ),
                Container(
                  width: 74,
                  height: 74,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF4EA3FF),
                        AppColors.primaryBlue,
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primaryBlue.withValues(alpha: 0.35),
                        blurRadius: 24,
                        spreadRadius: 6,
                      ),
                    ],
                  ),
                  child: Icon(
                    widget.recording ? Icons.stop_rounded : Icons.mic_none_rounded,
                    color: Colors.white,
                    size: 34,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
