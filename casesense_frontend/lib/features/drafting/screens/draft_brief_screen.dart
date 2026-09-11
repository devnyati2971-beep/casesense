import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';

class DraftBriefScreen extends ConsumerWidget {
  final String matterId;
  const DraftBriefScreen({super.key, required this.matterId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppColors.ivory,
      appBar: AppBar(
        backgroundColor: AppColors.espresso,
        iconTheme: const IconThemeData(color: AppColors.ivory),
        title: Text(
          'Matter Brief',
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
                  'Review Matter Brief',
                  style: Theme.of(context).textTheme.displayMedium,
                ),
                const SizedBox(height: 16),
                Text(
                  'This is the exact snapshot the AI will use to generate your legal document. Verify the facts and selected authorities.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.subtleBronze,
                  ),
                ),
                const SizedBox(height: 48),

                Container(
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(
                    color: AppColors.charcoal,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'SELECTED AUTHORITIES',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.ivory,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No authorities have been selected yet. Use Citation Finder to save verified authorities before generating a draft.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.ivory,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    TextButton.icon(
                      onPressed: () => context.pop(),
                      icon: const Icon(
                        Icons.arrow_back,
                        color: AppColors.charcoal,
                      ),
                      label: const Text(
                        'Back to Edit',
                        style: TextStyle(color: AppColors.charcoal),
                      ),
                    ),

                    PrimaryButton(
                      label: 'Open Draft Workspace',
                      icon: Icons.edit_document,
                      onPressed: () =>
                          context.go('/matters/$matterId?tab=drafts'),
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
