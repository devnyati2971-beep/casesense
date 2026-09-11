import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class IntelligenceTab extends StatelessWidget {
  const IntelligenceTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        'Case intelligence will appear after your uploaded documents are processed.',
        style: Theme.of(
          context,
        ).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze),
        textAlign: TextAlign.center,
      ),
    );
  }
}
