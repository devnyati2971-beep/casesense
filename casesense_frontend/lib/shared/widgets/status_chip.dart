import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  final String status;

  const StatusChip({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    Color bgColor;
    Color textColor;
    IconData? icon;

    switch (status.toUpperCase()) {
      case 'VERIFIED':
      case 'PROCESSED':
      case 'COMPLETED':
        bgColor = AppColors.success.withOpacity(0.1);
        textColor = AppColors.success;
        icon = Icons.check_circle_outline;
        break;
      case 'PARTIALLY_VERIFIED':
      case 'PROCESSING':
      case 'RETRIEVING':
      case 'ANALYZING':
      case 'GENERATING':
        bgColor = AppColors.warning.withOpacity(0.1);
        textColor = AppColors.warning;
        icon = Icons.sync;
        break;
      case 'FAILED':
      case 'NEEDS_REVIEW':
      case 'UNVERIFIED':
        bgColor = AppColors.error.withOpacity(0.1);
        textColor = AppColors.error;
        icon = Icons.warning_amber_rounded;
        break;
      case 'UPLOADED':
      case 'CREATED':
      case 'DRAFT':
      default:
        bgColor = AppColors.stone.withOpacity(0.15);
        textColor = AppColors.charcoal;
        icon = Icons.fiber_manual_record;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(4), // Sharp editorial corners
        border: Border.all(color: textColor.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: textColor),
          const SizedBox(width: 6),
          Text(
            status.toUpperCase(),
            style: TextStyle(
              color: textColor,
              fontSize: 10,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.0,
            ),
          ),
        ],
      ),
    );
  }
}