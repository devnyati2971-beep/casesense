import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/status_chip.dart';

class DraftsTab extends StatelessWidget {
  const DraftsTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(48),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Legal Drafts', style: Theme.of(context).textTheme.headlineMedium),
            PrimaryButton(label: 'Create Draft', onPressed: () {}),
          ],
        ),
        const SizedBox(height: 32),
        _buildDraftCard(context, 'Bail Application - Supreme Court', 'BAIL_APPLICATION', 'EDITING'),
      ],
    );
  }

  Widget _buildDraftCard(BuildContext context, String title, String type, String status) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.parchment,
        border: Border.all(color: AppColors.stone),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(type, style: Theme.of(context).textTheme.labelSmall),
              const SizedBox(height: 4),
              Text(title, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
          Row(
            children: [
              StatusChip(status: status),
              const SizedBox(width: 16),
              const Icon(Icons.edit_document, color: AppColors.charcoal),
            ],
          )
        ],
      ),
    );
  }
}