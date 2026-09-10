import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:ui';
import '../../core/providers/language_provider.dart';
import '../../core/theme/app_theme.dart';
import '../../features/auth/providers/auth_controller.dart';

class AppSidebar extends ConsumerWidget {
  final String currentRoute;

  const AppSidebar({super.key, required this.currentRoute});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final isAuthed = authState.value?.isAuthenticated ?? false;
    final user = authState.value?.user ?? <String, dynamic>{};
    final displayName = (user['full_name'] as String?) ?? 'Advocate';
    final role = (user['role'] as String?) ?? 'Advocate';
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'A';
    final language = ref.watch(languageProvider);

    // Locked destinations require an account (v2.2 guest tier: only Home and
    // the Citation Finder are public).
    void goOrLogin(String route) {
      if (isAuthed) {
        context.go(route);
      } else {
        context.push('/login?from=$route');
      }
    }

    return Container(
      width: 260,
      decoration: BoxDecoration(
        color: AppColors.nearBlack,
        image: DecorationImage(
          image: const AssetImage('assets/images/nav_panel.png'),
          fit: BoxFit.fill,
          colorFilter: ColorFilter.mode(AppColors.nearBlack.withOpacity(0.3), BlendMode.darken),
        ),
      ),
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
      child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.account_balance, color: AppColors.antiqueBrass, size: 28),
                  const SizedBox(width: 12),
                  Text(
                    'CaseSense',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: AppColors.ivory,
                      fontWeight: FontWeight.bold,
                      letterSpacing: -0.5,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 48),

              // v2.2 Primary Navigation
              _SidebarItem(icon: Icons.home_filled, label: 'Home', isActive: currentRoute == '/dashboard', onTap: () => context.go('/dashboard')),
              _SidebarItem(icon: Icons.manage_search, label: 'Citation Finder', isActive: currentRoute == '/finder', onTap: () => context.go('/finder')),
              _SidebarItem(icon: Icons.edit_document, label: 'Drafting', isLocked: !isAuthed, isActive: currentRoute.startsWith('/draft'), onTap: () => goOrLogin('/drafts_list')),
              _SidebarItem(icon: Icons.history, label: 'History', isLocked: !isAuthed, isActive: currentRoute == '/history', onTap: () => goOrLogin('/history')),
              _SidebarItem(icon: Icons.bookmark_outline, label: 'Saved Citations', isLocked: !isAuthed, isActive: currentRoute == '/saved-citations', onTap: () => goOrLogin('/saved-citations')),
              _SidebarItem(icon: Icons.local_library_outlined, label: 'Library', isLocked: !isAuthed, isActive: currentRoute == '/library', onTap: () => goOrLogin('/library')),

              const Spacer(),

              // v2.2 Language toggle (English / हिन्दी / Bilingual)
              _LanguageToggle(current: language),

              const SizedBox(height: 16),
              if (isAuthed) ...[
                _SidebarItem(icon: Icons.person_outline, label: 'Account', isActive: currentRoute == '/account', onTap: () => context.go('/account')),
                const SizedBox(height: 16),
                // User profile row (from real auth state)
                Row(
                  children: [
                    CircleAvatar(
                      radius: 16,
                      backgroundColor: AppColors.antiqueBrass,
                      child: Text(initial, style: const TextStyle(color: AppColors.ivory, fontSize: 12)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(displayName, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory, fontSize: 13), overflow: TextOverflow.ellipsis),
                          Text(role, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 11)),
                        ],
                      ),
                    ),
                  ],
                ),
              ] else ...[
                // Guest CTA — full services require an account.
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => context.push('/login?from=$currentRoute'),
                    icon: const Icon(Icons.login, size: 16),
                    label: const Text('Sign In'),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.antiqueBrass,
                      foregroundColor: AppColors.ivory,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () => context.push('/register'),
                    child: const Text('Create Account', style: TextStyle(fontSize: 12)),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.warmGrey,
                      side: BorderSide(color: AppColors.stone.withOpacity(0.4)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                  ),
                ),
              ],
            ],
      ),
    );
  }
}

class _LanguageToggle extends StatelessWidget {
  final LanguageState current;

  const _LanguageToggle({required this.current});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.charcoal.withOpacity(0.5),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.stone.withOpacity(0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final lang in AppLanguage.values) ...[
            _LangOption(
              label: switch (lang) {
                AppLanguage.english => 'EN',
                AppLanguage.hindi => 'हिं',
                AppLanguage.bilingual => 'BI',
              },
              isActive: current.language == lang,
            ),
          ],
        ],
      ),
    );
  }
}

class _LangOption extends ConsumerWidget {
  final String label;
  final bool isActive;

  const _LangOption({required this.label, required this.isActive});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: () {
        final lang = switch (label) {
          'EN' => AppLanguage.english,
          'हिं' => AppLanguage.hindi,
          _ => AppLanguage.bilingual,
        };
        ref.read(languageProvider.notifier).setLanguage(lang);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isActive ? AppColors.antiqueBrass : Colors.transparent,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isActive ? AppColors.ivory : AppColors.warmGrey,
            fontSize: 11,
            fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}

class _SidebarItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isActive;
  final bool isLocked;
  final VoidCallback onTap;

  const _SidebarItem({
    required this.icon,
    required this.label,
    required this.isActive,
    required this.onTap,
    this.isLocked = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        hoverColor: AppColors.antiqueBrass.withOpacity(0.1),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 12.0),
          decoration: BoxDecoration(
            color: isActive ? AppColors.charcoal : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(icon, color: isActive ? AppColors.antiqueBrass : AppColors.warmGrey, size: 20),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: isActive ? AppColors.ivory : AppColors.warmGrey,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
              if (isLocked)
                Icon(Icons.lock_outline, size: 14, color: AppColors.warmGrey.withOpacity(0.7)),
            ],
          ),
        ),
      ),
    );
  }
}
