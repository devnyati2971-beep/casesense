import 'package:flutter/material.dart';

/// Premium 3D "tilt" hover card — Flutter-web safe.
///
/// The old implementation crashed Flutter web with
/// `Assertion failed: mouse_tracker.dart:199` / `hit_test.dart:214`:
///   - setState on *every* pointer-move flooded the framework while a
///     perspective Matrix4 rotated the hit-test result.
///   - Inside a scroll view, LayoutBuilder's unbounded height made the hover
///     math produce NaN → rotateX(NaN) → hit-testing assertion.
///
/// This version:
///   - guards degenerate (infinite/zero) sizes from the hover math,
///   - clamps every rotation value (NaN can never enter the transform),
///   - animates via TweenAnimationBuilder (one tween per target change),
///     and keeps the tilt small so hit-testing stays stable.
class Tactile3DCard extends StatefulWidget {
  final Widget child;
  final double depth;

  const Tactile3DCard({
    super.key,
    required this.child,
    this.depth = 0.02,
  });

  @override
  State<Tactile3DCard> createState() => _Tactile3DCardState();
}

class _Tactile3DCardState extends State<Tactile3DCard> {
  static const double _maxTilt = 0.06; // radians (~3.4°)

  Offset _target = Offset.zero;

  void _onHover(PointerEvent details, Size size) {
    if (size.width <= 0 || size.height <= 0) return; // degenerate size guard
    final dx = (details.localPosition.dx / size.width - 0.5) * 2; // -1..1
    final dy = (details.localPosition.dy / size.height - 0.5) * 2; // -1..1
    // Clamp so NaN/Infinity can never reach the transform.
    final cx = dx.isFinite ? dx.clamp(-1.0, 1.0) : 0.0;
    final cy = dy.isFinite ? dy.clamp(-1.0, 1.0) : 0.0;
    final scale = (widget.depth * 20).clamp(0.5, 1.5).toDouble();
    final next = Offset(cy * _maxTilt * scale, -cx * _maxTilt * scale);
    if (next != _target) {
      setState(() => _target = next);
    }
  }

  void _onExit(PointerEvent details) {
    if (_target != Offset.zero) {
      setState(() => _target = Offset.zero);
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final h = constraints.maxHeight.isFinite ? constraints.maxHeight : w;

        return MouseRegion(
          opaque: false,
          hitTestBehavior: HitTestBehavior.translucent,
          onHover: (details) => _onHover(details, Size(w, h)),
          onExit: _onExit,
          child: TweenAnimationBuilder<Offset>(
            tween: Tween(end: _target),
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeOutCubic,
            builder: (context, offset, child) {
              // Final safety clamp — nothing non-finite reaches the Matrix4.
              final rx = offset.dx.isFinite ? offset.dx.clamp(-_maxTilt, _maxTilt) : 0.0;
              final ry = offset.dy.isFinite ? offset.dy.clamp(-_maxTilt, _maxTilt) : 0.0;
              return Transform(
                transform: Matrix4.identity()
                  ..setEntry(3, 2, 0.0015)
                  ..rotateX(rx)
                  ..rotateY(ry),
                alignment: Alignment.center,
                child: child,
              );
            },
            child: widget.child,
          ),
        );
      },
    );
  }
}
