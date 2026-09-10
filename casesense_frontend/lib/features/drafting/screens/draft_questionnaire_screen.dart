import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/app_text_field.dart';

class DraftQuestionnaireScreen extends ConsumerWidget {
  final String matterId;
  const DraftQuestionnaireScreen({super.key, required this.matterId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppColors.ivory,
      appBar: AppBar(
        backgroundColor: AppColors.espresso,
        iconTheme: const IconThemeData(color: AppColors.ivory),
        title: Text('Draft Preparation: Bail Application', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 64.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Document Questionnaire', style: Theme.of(context).textTheme.displayMedium),
                const SizedBox(height: 16),
                Text('CaseSense has auto-filled known details from Case Intelligence. Please provide the remaining information to build your Matter Brief.', 
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                const SizedBox(height: 48),

                // Auto-filled field (Tactile paper look)
                _buildAutoFilledField(context, 'Accused Name', 'Ramesh Kumar', 'Case Intelligence'),
                const SizedBox(height: 24),
                _buildAutoFilledField(context, 'FIR Number', '245/2024', 'Document Extracted'),
                const SizedBox(height: 48),

                // Missing required fields
                Text('Required Information', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.antiqueBrass)),
                const SizedBox(height: 24),
                const AppTextField(
                  label: 'Police Station',
                  hint: 'E.g., Central Police Station, Jaipur',
                ),
                const SizedBox(height: 24),
                const AppTextField(
                  label: 'Specific Prayer / Relief Sought',
                  hint: 'State the exact relief you want the court to grant...',
                ),
                
                const SizedBox(height: 64),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    PrimaryButton(
                      label: 'Review Matter Brief',
                      onPressed: () {
                        // Submit answers and go to Brief snapshot
                        context.push('/matters/$matterId/drafts/brief');
                      },
                    ),
                  ],
                )
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAutoFilledField(BuildContext context, String label, String value, String source) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.parchment,
        border: Border.all(color: AppColors.stone),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: Theme.of(context).textTheme.labelSmall),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: AppColors.success.withOpacity(0.1), borderRadius: BorderRadius.circular(4)),
                child: Row(
                  children: [
                    const Icon(Icons.auto_awesome, color: AppColors.success, size: 12),
                    const SizedBox(width: 4),
                    Text('Auto-filled from $source', style: const TextStyle(color: AppColors.success, fontSize: 10, fontWeight: FontWeight.bold)),
                  ],
                ),
              )
            ],
          ),
          const SizedBox(height: 8),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}