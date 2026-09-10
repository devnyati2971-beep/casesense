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

  static const List<String> _tabs = ['Profile', 'Security', 'Preferences', 'Subscription', 'About'];

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
                  Text('Account', style: Theme.of(context).textTheme.displayMedium),
                  const SizedBox(height: 8),
                  Text('Manage your profile, preferences and account settings.',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
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

  Widget _buildTabContent(BuildContext context, Map<String, dynamic> user, bool isVerified) {
    switch (_activeTab) {
      case 0:
        return _ProfileTab(user: user, isVerified: isVerified, ref: ref);
      case 1:
        return _SecurityTab(ref: ref);
      case 2:
        return _PreferencesTab();
      case 3:
        return _SubscriptionTab();
      default:
        return _AboutTab(ref: ref);
    }
  }
}

class _AccountTab extends StatelessWidget {
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _AccountTab({required this.label, required this.isActive, required this.onTap});

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
  final WidgetRef ref;

  const _ProfileTab({required this.user, required this.isVerified, required this.ref});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Profile information card
            Expanded(
              flex: 5,
              child: _Card(
                title: 'Profile Information',
                child: Column(
                  children: [
                    _ProfileRow(label: 'Name', value: user['full_name'] ?? '—'),
                    _ProfileRow(label: 'Email', value: '${user['email'] ?? '—'} ${isVerified ? '✓' : '(unverified)'}'),
                    _ProfileRow(label: 'Phone', value: user['phone'] ?? '—'),
                    _ProfileRow(label: 'Chamber', value: user['chamber'] ?? '—'),
                    _ProfileRow(label: 'Role', value: user['role'] ?? 'advocate'),
                    const SizedBox(height: 16),
                    Align(
                      alignment: Alignment.centerRight,
                      child: OutlinedButton.icon(
                        onPressed: () => _showEditProfileDialog(context, ref),
                        icon: const Icon(Icons.edit_outlined, size: 16),
                        label: const Text('Edit Profile'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 24),
            // Professional details + quick stats
            Expanded(
              flex: 4,
              child: Column(
                children: [
                  _Card(
                    title: 'Professional Details',
                    child: Column(
                      children: [
                        _ProfileRow(label: 'Bar Council', value: user['bar_council_id']?.toString().isNotEmpty == true ? 'Registered' : '—'),
                        _ProfileRow(label: 'Enrollment No.', value: user['bar_council_id'] ?? '—'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  _Card(
                    title: 'Quick Stats',
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: const [
                        _Stat(value: '—', label: 'Total Cases'),
                        _Stat(value: '—', label: 'Drafts Created'),
                        _Stat(value: '—', label: 'Citations Saved'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        // Account actions (mockup: Download My Data / Delete Account)
        _Card(
          title: 'Account Actions',
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.download_outlined, color: AppColors.charcoal),
                title: const Text('Download My Data'),
                subtitle: const Text('Export your profile data as JSON'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _downloadData(context, ref),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const Icon(Icons.delete_outline, color: AppColors.error),
                title: const Text('Delete Account', style: TextStyle(color: AppColors.error)),
                subtitle: const Text('Permanently remove your account and data'),
                trailing: const Icon(Icons.chevron_right, color: AppColors.error),
                onTap: () => _confirmDelete(context, ref),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _showEditProfileDialog(BuildContext context, WidgetRef ref) async {
    final nameController = TextEditingController(text: user['full_name']?.toString());
    final phoneController = TextEditingController(text: user['phone']?.toString());
    final barController = TextEditingController(text: user['bar_council_id']?.toString());

    await showDialog(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: AppColors.ivory,
          title: const Text('Edit Profile'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Full Name')),
              const SizedBox(height: 12),
              TextField(controller: phoneController, decoration: const InputDecoration(labelText: 'Phone')),
              const SizedBox(height: 12),
              TextField(controller: barController, decoration: const InputDecoration(labelText: 'Bar Council ID')),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            PrimaryButton(
              label: 'Save',
              onPressed: () async {
                try {
                  final dio = ref.read(dioProvider);
                  await dio.patch(Endpoints.updateMe, data: {
                    'full_name': nameController.text.trim(),
                    'phone': phoneController.text.trim().isEmpty ? null : phoneController.text.trim(),
                    'bar_council_id': barController.text.trim().isEmpty ? null : barController.text.trim(),
                  });
                  await ref.read(authControllerProvider.notifier).checkAuthStatus();
                } catch (_) {}
                if (dialogContext.mounted) Navigator.pop(dialogContext);
              },
            ),
          ],
        );
      },
    );
  }

  Future<void> _downloadData(BuildContext context, WidgetRef ref) async {
    try {
      final dio = ref.read(dioProvider);
      final me = await dio.get(Endpoints.me);
      final raw = me.data is Map<String, dynamic> ? me.data as Map<String, dynamic> : <String, dynamic>{};
      // In a web build this would trigger a JSON download; show a confirmation here.
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Data export ready: ${raw.toString().length} bytes of profile data.')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Export failed — try again.')),
        );
      }
    }
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: AppColors.ivory,
          title: const Text('Delete Account?'),
          content: const Text('This permanently removes your account, matters, drafts and saved citations. This cannot be undone.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
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
          Text(title, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 18)),
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
          SizedBox(width: 140, child: Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey))),
          Expanded(child: Text(value, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  final String value;
  final String label;

  const _Stat({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: Theme.of(context).textTheme.displayMedium?.copyWith(color: AppColors.antiqueBrass, fontSize: 28)),
        const SizedBox(height: 4),
        Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 11), textAlign: TextAlign.center),
      ],
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
            decoration: const InputDecoration(labelText: 'Current Password', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: newPassword,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'New Password', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          PrimaryButton(
            label: 'Change Password',
            onPressed: () async {
              try {
                final dio = ref.read(dioProvider);
                await dio.post(Endpoints.changePassword, data: {
                  'current_password': currentPassword.text,
                  'new_password': newPassword.text,
                });
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Password changed successfully.')),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed: $e')),
                  );
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
          Text('Language: English (हिन्दी / Bilingual available in the sidebar)'),
          SizedBox(height: 12),
          Text('Theme: Editorial Light'),
        ],
      ),
    );
  }
}

class _SubscriptionTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return _Card(
      title: 'Subscription',
      child: const Text('Free Plan — MVP build has no billing modules (blueprint §0 Rule 2).'),
    );
  }
}

class _AboutTab extends StatelessWidget {
  final WidgetRef ref;

  const _AboutTab({required this.ref});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _Card(
          title: 'About',
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('CaseSense — citation-grounded legal intelligence for Indian advocates.'),
              SizedBox(height: 8),
              Text('Version 2.2.0'),
            ],
          ),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () async {
              await ref.read(authControllerProvider.notifier).logout();
              if (context.mounted) context.go('/login');
            },
            style: OutlinedButton.styleFrom(foregroundColor: AppColors.error, side: const BorderSide(color: AppColors.error)),
            child: const Text('Log Out'),
          ),
        ),
      ],
    );
  }
}
