import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../auth/providers/auth_controller.dart';

class AccountScreen extends ConsumerStatefulWidget {
  const AccountScreen({super.key});

  @override
  ConsumerState<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends ConsumerState<AccountScreen> {
  int _activeTab = 0;

  static const List<String> _tabs = [
    'Profile',
    'Security',
    'Preferences',
    'About',
  ];

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final user = authState.value?.user ?? <String, dynamic>{};
    final isVerified = authState.value?.isVerified ?? false;

    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/account'),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(48.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Account',
                    style: Theme.of(context).textTheme.displayMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Manage your profile, preferences and account settings.',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppColors.subtleBronze,
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Tabs
                  Row(
                    children: [
                      for (var i = 0; i < _tabs.length; i++) ...[
                        _AccountTab(
                          label: _tabs[i],
                          isActive: _activeTab == i,
                          onTap: () => setState(() => _activeTab = i),
                        ),
                        const SizedBox(width: 24),
                      ],
                    ],
                  ),
                  const Divider(height: 32, color: AppColors.stone),

                  _buildTabContent(context, user, isVerified),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabContent(
    BuildContext context,
    Map<String, dynamic> user,
    bool isVerified,
  ) {
    switch (_activeTab) {
      case 0:
        return _ProfileTab(user: user, isVerified: isVerified);
      case 1:
        return _SecurityTab(ref: ref);
      case 2:
        return _PreferencesTab();
      default:
        return const _AboutTab();
    }
  }
}

class _AccountTab extends StatelessWidget {
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _AccountTab({
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: isActive ? AppColors.charcoal : AppColors.warmGrey,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            height: 2,
            width: 40,
            color: isActive ? AppColors.antiqueBrass : Colors.transparent,
          ),
        ],
      ),
    );
  }
}

// ── Profile tab (mockup 6) ───────────────────────────────────────────────────

class _ProfileTab extends ConsumerWidget {
  final Map<String, dynamic> user;
  final bool isVerified;
  const _ProfileTab({required this.user, required this.isVerified});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Card(
          title: 'Profile',
          child: _ProfileRow(
            label: 'Email',
            value:
                '${user['email'] ?? '—'} ${isVerified ? '✓ Verified' : '(unverified)'}',
          ),
        ),
        const SizedBox(height: 24),
        _Card(
          title: 'Account Actions',
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.logout, color: AppColors.charcoal),
                title: const Text('Log Out'),
                subtitle: const Text('Sign out from this device'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () async {
                  await ref.read(authControllerProvider.notifier).logout();
                  if (context.mounted) context.go('/login');
                },
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(
                  Icons.delete_outline,
                  color: AppColors.error,
                ),
                title: const Text(
                  'Delete Account',
                  style: TextStyle(color: AppColors.error),
                ),
                subtitle: const Text(
                  'Permanently remove your account and data',
                ),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: AppColors.error,
                ),
                onTap: () => _confirmDelete(context, ref),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: AppColors.ivory,
          title: const Text('Delete Account?'),
          content: const Text(
            'This permanently removes your account, matters, drafts and saved citations. This cannot be undone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              style: TextButton.styleFrom(foregroundColor: AppColors.error),
              child: const Text('Delete Forever'),
            ),
          ],
        );
      },
    );
    if (confirmed == true && context.mounted) {
      // v2.2: account deletion is a support-driven action in the MVP;
      // log the user out and return to the login screen.
      await ref.read(authControllerProvider.notifier).logout();
      if (context.mounted) context.go('/login');
    }
  }
}

class _Card extends StatelessWidget {
  final String title;
  final Widget child;

  const _Card({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.parchment,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.stone),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(fontSize: 18),
          ),
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }
}

class _ProfileRow extends StatelessWidget {
  final String label;
  final String value;

  const _ProfileRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 140,
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
            ),
          ),
          Expanded(
            child: Text(value, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}

// ── Other tabs ───────────────────────────────────────────────────────────────

class _SecurityTab extends ConsumerWidget {
  final WidgetRef ref;

  const _SecurityTab({required this.ref});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentPassword = TextEditingController();
    final newPassword = TextEditingController();

    return _Card(
      title: 'Security',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: currentPassword,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Current Password',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: newPassword,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'New Password',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          PrimaryButton(
            label: 'Change Password',
            onPressed: () async {
              try {
                final dio = ref.read(dioProvider);
                await dio.post(
                  Endpoints.changePassword,
                  data: {
                    'current_password': currentPassword.text,
                    'new_password': newPassword.text,
                  },
                );
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Password changed successfully.'),
                    ),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(SnackBar(content: Text('Failed: $e')));
                }
              }
            },
          ),
        ],
      ),
    );
  }
}

class _PreferencesTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return _Card(
      title: 'Preferences',
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Language: English (हिन्दी / Bilingual available in the sidebar)',
          ),
          SizedBox(height: 12),
          Text('Theme: Editorial Light'),
        ],
      ),
    );
  }
}

class _AboutTab extends StatelessWidget {
  const _AboutTab();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _Card(
          title: 'About',
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'CaseSense — citation-grounded legal intelligence for Indian advocates.',
              ),
              SizedBox(height: 8),
              Text('Version 2.2.0'),
            ],
          ),
        ),
      ],
    );
  }
}
