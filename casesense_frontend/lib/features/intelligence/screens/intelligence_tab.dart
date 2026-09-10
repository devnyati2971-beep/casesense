import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';

class IntelligenceTab extends StatelessWidget {
  const IntelligenceTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(48),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Case Intelligence', style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 8),
                Text('AI extracted facts and legal issues. Review and confirm.', style: Theme.of(context).textTheme.bodyLarge),
              ],
            ),
            PrimaryButton(label: 'Run Analysis', onPressed: () {}),
          ],
        ),
        const SizedBox(height: 48),
        _buildSection(context, 'Key Facts', [
          'The accused has been in judicial custody since October 12, 2024.',
          'Chargesheet was filed on December 10, 2024.',
        ]),
        const SizedBox(height: 32),
        _buildSection(context, 'Legal Issues', [
          'Whether the prolonged pre-trial detention violates Article 21.',
          'Whether the nature of the offense restricts bail under Section 439.',
        ]),
      ],
    );
  }

  Widget _buildSection(BuildContext context, String title, List<String> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.antiqueBrass)),
        const SizedBox(height: 16),
        ...items.map((item) => Padding(
          padding: const EdgeInsets.only(bottom: 12.0),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('• ', style: TextStyle(color: AppColors.subtleBronze, fontSize: 18)),
              Expanded(child: Text(item, style: Theme.of(context).textTheme.bodyLarge)),
            ],
          ),
        )),
      ],
    );
  }
}