import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/status_chip.dart';

class ResearchTab extends StatelessWidget {
  const ResearchTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(48),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Legal Research', style: Theme.of(context).textTheme.headlineMedium),
            PrimaryButton(label: 'Start New Search', onPressed: () {}),
          ],
        ),
        const SizedBox(height: 32),
        _buildResearchSession(context, 'Bail requirements under Section 439', 'COMPLETED'),
      ],
    );
  }

  Widget _buildResearchSession(BuildContext context, String concept, String status) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.ivory,
        border: Border.all(color: AppColors.stone),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Concept Search', style: Theme.of(context).textTheme.labelSmall),
              const SizedBox(height: 4),
              Text(concept, style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
          Row(
            children: [
              StatusChip(status: status),
              const SizedBox(width: 16),
              const Icon(Icons.chevron_right, color: AppColors.charcoal),
            ],
          )
        ],
      ),
    );
  }
}