import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class GhostButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  const GhostButton({super.key, required this.label, this.onPressed, this.icon});

  @override
  Widget build(BuildContext context) {
    return TextButton.icon(
      onPressed: onPressed,
      icon: icon != null ? Icon(icon, size: 18) : const SizedBox.shrink(),
      label: Text(label),
      style: TextButton.styleFrom(
        foregroundColor: AppColors.charcoal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(4),
          side: const BorderSide(color: AppColors.stone),
        ),
        textStyle: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 14),
      ),
    );
  }
}