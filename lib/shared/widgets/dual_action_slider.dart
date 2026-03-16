import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';


class DualActionSlider extends StatefulWidget {
  const DualActionSlider({
    super.key,
    required this.onLeftToRight,
    required this.onRightToLeft,
  });

  final VoidCallback onLeftToRight;
  final VoidCallback onRightToLeft;

  @override
  State<DualActionSlider> createState() => _DualActionSliderState();
}

class _DualActionSliderState extends State<DualActionSlider>
    with SingleTickerProviderStateMixin {
  double _position = 0;
  double _maxPosition = 0;
  double _dragStartX = 0;
  bool _dragging = false;
  late final AnimationController _hintController = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat();

  @override
  void dispose() {
    _hintController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        _maxPosition = constraints.maxWidth - 64;
        return SizedBox(
          height: 64,
          child: Stack(
            alignment: Alignment.centerLeft,
            children: [
              _SliderTrack(
                controller: _hintController,
                showHint: !_dragging,
              ),
              Positioned(
                left: _position.clamp(0, _maxPosition),
                child: GestureDetector(
                  onHorizontalDragStart: (details) {
                    setState(() {
                      _dragStartX = details.globalPosition.dx;
                      _dragging = true;
                    });
                  },
                  onHorizontalDragUpdate: (details) {
                    setState(() {
                      _position =
                          (_position + details.delta.dx).clamp(0, _maxPosition);
                    });
                  },
                  onHorizontalDragEnd: (details) {
                    final delta =
                        details.primaryVelocity ?? (details.velocity.pixelsPerSecond.dx);
                    if (delta > 300) {
                      widget.onLeftToRight();
                    } else if (delta < -300) {
                      widget.onRightToLeft();
                    }
                    setState(() {
                      _position = 0;
                      _dragging = false;
                    });
                  },
                  child: _Knob(),
                ),
              ),
              const Positioned(
                left: 16,
                child: Icon(Icons.mic_none_rounded, color: Colors.white),
              ),
              const Positioned(
                right: 16,
                child: Icon(Icons.chat_bubble_outline_rounded,
                    color: Colors.white),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SliderTrack extends StatelessWidget {
  const _SliderTrack({
    required this.controller,
    required this.showHint,
  });

  final AnimationController controller;
  final bool showHint;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        final t = controller.value;
        return Container(
          height: 64,
          decoration: BoxDecoration(
            color: AppColors.primaryBlue,
            borderRadius: BorderRadius.circular(32),
            boxShadow: [
              BoxShadow(
                color: AppColors.primaryBlue.withValues(alpha: 0.25),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: showHint
              ? Stack(
                  children: [
                    _HintChevrons(
                      alignment: Alignment.centerLeft,
                      progress: t,
                      direction: AxisDirection.right,
                    ),
                    _HintChevrons(
                      alignment: Alignment.centerRight,
                      progress: 1 - t,
                      direction: AxisDirection.left,
                    ),
                  ],
                )
              : null,
        );
      },
    );
  }
}

class _Knob extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white,
        border: Border.all(
          color: AppColors.primaryBlue.withValues(alpha: 0.3),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.15),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: const Icon(Icons.drag_indicator_rounded,
          color: AppColors.primaryBlue),
    );
  }
}

class _HintChevrons extends StatelessWidget {
  const _HintChevrons({
    required this.alignment,
    required this.progress,
    required this.direction,
  });

  final Alignment alignment;
  final double progress;
  final AxisDirection direction;

  @override
  Widget build(BuildContext context) {
    final opacity = 0.25 + (0.6 * progress);
    return Align(
      alignment: alignment,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              direction == AxisDirection.right
                  ? Icons.chevron_right_rounded
                  : Icons.chevron_left_rounded,
              color: Colors.white.withValues(alpha: opacity),
              size: 18,
            ),
            const SizedBox(width: 2),
            Icon(
              direction == AxisDirection.right
                  ? Icons.chevron_right_rounded
                  : Icons.chevron_left_rounded,
              color: Colors.white.withValues(alpha: opacity * 0.75),
              size: 18,
            ),
          ],
        ),
      ),
    );
  }
}
