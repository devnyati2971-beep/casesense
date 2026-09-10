import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../providers/drafts_controller.dart';

class DraftBriefScreen extends ConsumerWidget {
  final String matterId;
  const DraftBriefScreen({super.key, required this.matterId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch state to disable button and show loading while generating
    final draftsState = ref.watch(draftsControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.ivory,
      appBar: AppBar(
        backgroundColor: AppColors.espresso,
        iconTheme: const IconThemeData(color: AppColors.ivory),
        title: Text('Matter Brief', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 64.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Review Matter Brief', style: Theme.of(context).textTheme.displayMedium),
                const SizedBox(height: 16),
                Text('This is the exact snapshot the AI will use to generate your legal document. Verify the facts and selected authorities.', 
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                const SizedBox(height: 48),

                Container(
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(color: AppColors.charcoal, borderRadius: BorderRadius.circular(8)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('SELECTED AUTHORITIES (2)', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.ivory)),
                      const SizedBox(height: 16),
                      Text('1. Kesavananda Bharati v. State of Kerala (1973)', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.ivory)),
                      const SizedBox(height: 8),
                      Text('2. S.P. Gupta v. Union of India (1981)', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.ivory)),
                    ],
                  ),
                ),
                const SizedBox(height: 32),
                
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    TextButton.icon(
                      onPressed: draftsState.isLoading ? null : () => context.pop(),
                      icon: const Icon(Icons.arrow_back, color: AppColors.charcoal),
                      label: const Text('Back to Edit', style: TextStyle(color: AppColors.charcoal)),
                    ),
                    
                    // Generate Button with Riverpod Logic
                    draftsState.isLoading
                        ? Row(
                            children: [
                              const CircularProgressIndicator(color: AppColors.antiqueBrass),
                              const SizedBox(width: 16),
                              Text('AI is drafting...', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.antiqueBrass)),
                            ],
                          )
                        : PrimaryButton(
                            label: 'Looks Good — Generate Draft',
                            icon: Icons.auto_awesome,
                            onPressed: () async {
                              // Call the generate function in controller
                              final success = await ref.read(draftsControllerProvider.notifier).generateDraft('123'); // using dummy ID
                              
                              // If generated successfully, push to the Editor
                              if (success && context.mounted) {
                                context.push('/drafts/123');
                              }
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
}