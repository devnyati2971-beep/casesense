import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class DocumentsTab extends StatelessWidget {
  const DocumentsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        'Documents are shown inside each matter workspace.',
        style: Theme.of(
          context,
        ).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze),
      ),
    );
  }
}
