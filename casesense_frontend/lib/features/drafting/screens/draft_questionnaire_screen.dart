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
        title: Text(
          'Draft Preparation: Bail Application',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(color: AppColors.ivory),
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 64.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Document Questionnaire',
                  style: Theme.of(context).textTheme.displayMedium,
                ),
                const SizedBox(height: 16),
                Text(
                  'Provide the case details needed to build your matter brief.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.subtleBronze,
                  ),
                ),
                const SizedBox(height: 48),

                Text(
                  'Required Information',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: AppColors.antiqueBrass,
                  ),
                ),
                const SizedBox(height: 24),
                const AppTextField(
                  label: 'Party / Client Name',
                  hint: 'Enter the party or client name',
                ),
                const SizedBox(height: 24),
                const AppTextField(
                  label: 'Case or FIR Number',
                  hint: 'Enter the case or FIR number, if applicable',
                ),
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
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
