import 'dart:math' as math;

import 'package:flutter/material.dart';

/// A modern slide-only action button with a guided indicator.
/// The user drags the knob horizontally to trigger the action.
class SlideActionButton extends StatefulWidget {
  const SlideActionButton({
    super.key,
    required this.onSlide,
    this.width,
    this.height = 68,
    this.knobSize = 56,
    this.accent = const Color(0xFF2276FF),
    this.knobIcon,
  });

  final void Function(AxisDirection direction) onSlide;
  final double? width;
  final double height;
  final double knobSize;
  final Color accent;
  final Widget? knobIcon;

  @override
  State<SlideActionButton> createState() => _SlideActionButtonState();
}

class _SlideActionButtonState extends State<SlideActionButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _hintController = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  )..repeat();

  double _dragX = 0;
  AxisDirection _direction = AxisDirection.right;
  bool _hasTriggered = false;

  double _resolvedWidth = 220;
  double get _trackWidth =>
      math.max(0, _resolvedWidth - widget.knobSize);

  @override
  void dispose() {
    _hintController.dispose();
    super.dispose();
  }

  void _updateDrag(DragUpdateDetails details) {
    final nextX =
        (_dragX + details.delta.dx).clamp(0, _trackWidth).toDouble();
    if (!_hasTriggered && (nextX - _dragX).abs() > 6) {
      _direction =
          details.delta.dx >= 0 ? AxisDirection.right : AxisDirection.left;
      _hasTriggered = true;
      widget.onSlide(_direction);
    }
    setState(() {
      _dragX = nextX;
    });
  }

  void _endDrag(DragEndDetails details) {
    final midpoint = _trackWidth / 2;
    final newDirection =
        _dragX >= midpoint ? AxisDirection.right : AxisDirection.left;
    setState(() {
      _direction = newDirection;
      _dragX = newDirection == AxisDirection.right ? _trackWidth : 0;
    });
    if (!_hasTriggered) {
      widget.onSlide(_direction);
    }
    _hasTriggered = false;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        _resolvedWidth = widget.width ?? constraints.maxWidth;
        return SizedBox(
          width: _resolvedWidth,
          height: widget.height,
          child: Stack(
            alignment: Alignment.centerLeft,
            children: [
              _SlideTrack(
                accent: widget.accent,
                direction: _direction,
                controller: _hintController,
              ),
              AnimatedPositioned(
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOut,
                left: _dragX,
                child: GestureDetector(
                  onHorizontalDragUpdate: _updateDrag,
                  onHorizontalDragEnd: _endDrag,
                  child: _SlideKnob(
                    size: widget.knobSize,
                    accent: widget.accent,
                    icon: widget.knobIcon,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SlideTrack extends StatelessWidget {
  const _SlideTrack({
    required this.accent,
    required this.direction,
    required this.controller,
  });

  final Color accent;
  final AxisDirection direction;
  final AnimationController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        final wave = (math.sin(controller.value * math.pi * 2) + 1) / 2;
        final shimmer = 0.15 + (wave * 0.35);
        return Container(
          height: 56,
          decoration: BoxDecoration(
            color: accent.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(color: accent.withValues(alpha: 0.18)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Opacity(
                  opacity: direction == AxisDirection.left ? shimmer : 0.0,
                  child: _PulseDots(accent: accent),
                ),
              ),
              Expanded(
                child: Opacity(
                  opacity: direction == AxisDirection.right ? shimmer : 0.0,
                  child: _PulseDots(accent: accent),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _PulseDots extends StatelessWidget {
  const _PulseDots({required this.accent});

  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _Dot(accent: accent, delay: 0),
        _Dot(accent: accent, delay: 140),
        _Dot(accent: accent, delay: 280),
      ],
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot({
    required this.accent,
    required this.delay,
  });

  final Color accent;
  final int delay;

  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final phase = ((_controller.value * 900) - widget.delay) / 900;
        final opacity = (phase >= 0 && phase <= 1)
            ? (0.25 + (0.75 * (1 - (phase - 0.5).abs() * 2)))
            : 0.25;
        final scale = 0.9 + (0.2 * opacity);
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: widget.accent.withValues(alpha: opacity),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: widget.accent.withValues(alpha: opacity * 0.6),
                blurRadius: 6,
              ),
            ],
          ),
          transform: Matrix4.identity()..scale(scale, scale),
        );
      },
    );
  }
}

class _SlideKnob extends StatelessWidget {
  const _SlideKnob({
    required this.size,
    required this.accent,
    this.icon,
  });

  final double size;
  final Color accent;
  final Widget? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.white, accent.withValues(alpha: 0.15)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        shape: BoxShape.circle,
        border: Border.all(color: accent.withValues(alpha: 0.4), width: 1.4),
        boxShadow: [
          BoxShadow(
            color: accent.withValues(alpha: 0.35),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Center(
        child: icon ??
            Icon(
              Icons.circle,
              color: accent.withValues(alpha: 0.75),
              size: size * 0.35,
            ),
      ),
    );
  }
}
