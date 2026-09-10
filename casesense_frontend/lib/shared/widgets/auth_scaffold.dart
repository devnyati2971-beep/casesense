import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

/// Shared scaffold for all auth screens (login / register / verify / reset).
///
/// Full-bleed background image (assets/images/dashboard_img.png) with a dark
/// espresso overlay + subtle brand strip on the left, and the auth form in a
/// premium glassmorphic card — per the product mockups.
class AuthScaffold extends StatelessWidget {
  final Widget formChild;
  final bool showBrandStrip;

  const AuthScaffold({
    super.key,
    required this.formChild,
    this.showBrandStrip = true,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 900;
        return Scaffold(
          body: Stack(
            fit: StackFit.expand,
            children: [
              // Background image
              Image.asset(
                'assets/images/dashboard_img.png',
                fit: BoxFit.cover,
                errorBuilder: (context, error, stack) => Container(
                  color: AppColors.espresso,
                ),
              ),
              // Dark overlay for readability
              Container(
                color: AppColors.nearBlack.withOpacity(0.72),
              ),
              // Content
              SafeArea(
                child: Row(
                  children: [
                    if (showBrandStrip && isWide)
                      Expanded(
                        flex: 5,
                    child: Padding(
                      padding: const EdgeInsets.all(64.0),
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.account_balance,
                                    color: AppColors.antiqueBrass, size: 32),
                                const SizedBox(width: 12),
                                Text(
                                  'CaseSense',
                                  style: Theme.of(context)
                                      .textTheme
                                      .headlineMedium
                                      ?.copyWith(
                                        color: AppColors.ivory,
                                        fontWeight: FontWeight.bold,
                                        letterSpacing: -0.5,
                                      ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 32),
                            Text(
                              '"The life of the law has not been logic: it has been experience."',
                              style: Theme.of(context)
                                  .textTheme
                                  .displaySmall
                                  ?.copyWith(
                                    color: AppColors.ivory,
                                    fontStyle: FontStyle.italic,
                                    height: 1.4,
                                  ),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              '— O.W. Holmes Jr.',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyLarge
                                  ?.copyWith(color: AppColors.warmGrey),
                            ),
                            const SizedBox(height: 40),
                            _FeatureRow(
                              icon: Icons.verified_outlined,
                              text: 'Paragraph-level citation verification',
                            ),
                            const SizedBox(height: 16),
                            _FeatureRow(
                              icon: Icons.gavel_outlined,
                              text: 'AI Citation Finder for Indian case law',
                            ),
                            const SizedBox(height: 16),
                            _FeatureRow(
                              icon: Icons.edit_document,
                              text: 'Citation-aware drafting with traceability',
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                    Expanded(
                      flex: 6,
                      child: Center(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 32.0, vertical: 32.0),
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 440),
                            padding: const EdgeInsets.all(40.0),
                            decoration: BoxDecoration(
                              color: AppColors.ivory.withOpacity(0.97),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                  color: AppColors.stone.withOpacity(0.4)),
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.nearBlack.withOpacity(0.45),
                                  blurRadius: 40,
                                  offset: const Offset(0, 20),
                                ),
                              ],
                            ),
                            child: formChild,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _FeatureRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _FeatureRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: AppColors.antiqueBrass, size: 18),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: Theme.of(context)
                .textTheme
                .bodyLarge
                ?.copyWith(color: AppColors.ivory.withOpacity(0.9)),
          ),
        ),
      ],
    );
  }
}
