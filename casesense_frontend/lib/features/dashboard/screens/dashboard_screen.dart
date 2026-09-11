import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:ui';
import 'package:file_picker/file_picker.dart';
import '../../../core/providers/language_provider.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../auth/providers/auth_controller.dart';
import '../../matters/providers/matters_list_controller.dart';
import '../../research/providers/research_controller.dart';
import '../../research/providers/research_list_controller.dart';
import '../../research/providers/saved_citations_controller.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    final isAuthed =
        ref.read(authControllerProvider).value?.isAuthenticated ?? false;
    if (isAuthed) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref.read(savedCitationsControllerProvider.notifier).load();
          ref.read(researchListControllerProvider.notifier).load();
        }
      });
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _submitSearch() {
    final query = _searchController.text.trim();
    if (query.isEmpty) {
      context.push('/finder');
      return;
    }
    ref.read(researchControllerProvider.notifier).submitQuery(query).then((
      sessionId,
    ) {
      if (!mounted) return;
      // Guest used both free searches — send them to registration.
      if (ref.read(researchControllerProvider).guestLimitReached) {
        context.push('/register');
        return;
      }
      if (sessionId != null) {
        context.push('/research/$sessionId/status');
      }
    });
  }

  Future<void> _uploadDocument() async {
    if (ref.read(authControllerProvider).value?.isAuthenticated != true) {
      context.push('/login?from=/dashboard');
      return;
    }
    final files = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'docx', 'txt'],
      withData: true,
    );
    final file = files?.files.singleOrNull;
    if (file?.bytes == null || !mounted) return;
    final sessionId = await ref
        .read(researchControllerProvider.notifier)
        .submitDocument(file!.bytes!, file.name);
    if (!mounted) return;
    if (sessionId != null)
      context.push('/research/$sessionId/status');
    else
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not analyze that document.')),
      );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final isAuthed = authState.value?.isAuthenticated ?? false;
    final user = authState.value?.user ?? <String, dynamic>{};
    final fullName =
        (user['full_name'] as String?) ?? (isAuthed ? 'Advocate' : 'Guest');
    final firstName = fullName.split(' ').first;
    final language = ref.watch(languageProvider);
    final savedState = ref.watch(savedCitationsControllerProvider);
    final researchSessions = ref.watch(researchListControllerProvider).sessions;
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Good Morning'
        : hour < 17
        ? 'Good Afternoon'
        : 'Good Evening';

    return Scaffold(
      backgroundColor: AppColors.parchment,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/dashboard'),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 56.0,
                      vertical: 40.0,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Greeting row + language chip (mockup top-right)
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '$greeting, $firstName',
                                  style: Theme.of(context)
                                      .textTheme
                                      .displayLarge
                                      ?.copyWith(
                                        color: AppColors.nearBlack,
                                        fontSize: 44,
                                        height: 1.1,
                                        fontStyle: FontStyle.italic,
                                      ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  isAuthed
                                      ? 'Your legal work, simplified with AI.'
                                      : 'Try the AI Citation Finder free — no account needed.',
                                  style: Theme.of(context).textTheme.bodyLarge
                                      ?.copyWith(
                                        color: AppColors.charcoal,
                                        fontSize: 16,
                                      ),
                                ),
                              ],
                            ),
                            _LanguageChip(label: language.label),
                          ],
                        ),
                        const SizedBox(height: 40),

                        // AI-Powered Legal Assistant card (mockup hero card)
                        Container(
                          clipBehavior: Clip.hardEdge,
                          decoration: BoxDecoration(
                            color: AppColors.ivory,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: AppColors.stone),
                          ),
                          child: Stack(
                            children: [
                              Positioned.fill(
                                child: Opacity(
                                  opacity: 0.8,
                                  child: Image.asset(
                                    'assets/images/dashboard_img.png',
                                    fit: BoxFit.cover,
                                    errorBuilder: (_, __, ___) =>
                                        Container(color: AppColors.stone),
                                  ),
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.all(28),
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    begin: Alignment.centerLeft,
                                    end: Alignment.centerRight,
                                    colors: [
                                      AppColors.ivory.withOpacity(0.90),
                                      AppColors.ivory.withOpacity(0.75),
                                      AppColors.ivory.withOpacity(0.40),
                                      Colors.transparent,
                                    ],
                                    stops: const [0.0, 0.4, 0.6, 1.0],
                                  ),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        const Icon(
                                          Icons.auto_awesome,
                                          color: AppColors.antiqueBrass,
                                          size: 20,
                                        ),
                                        const SizedBox(width: 12),
                                        Text(
                                          'AI-Powered Legal Assistant',
                                          style: Theme.of(
                                            context,
                                          ).textTheme.titleMedium,
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 16),
                                    Text(
                                      'Generate Legal Documents',
                                      style: Theme.of(
                                        context,
                                      ).textTheme.displayMedium,
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      'Draft petitions, applications, and more with the power of AI.',
                                      style: Theme.of(
                                        context,
                                      ).textTheme.bodyLarge,
                                    ),
                                    const SizedBox(height: 24),
                                    // Global search bar
                                    Container(
                                      width: 600,
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 16,
                                        vertical: 6,
                                      ),
                                      decoration: BoxDecoration(
                                        color: AppColors.parchment,
                                        borderRadius: BorderRadius.circular(40),
                                        border: Border.all(
                                          color: AppColors.stone,
                                        ),
                                      ),
                                      child: Row(
                                        children: [
                                          const Icon(
                                            Icons.chat_bubble_outline,
                                            color: AppColors.charcoal,
                                            size: 20,
                                          ),
                                          const SizedBox(width: 12),
                                          Expanded(
                                            child: TextField(
                                              controller: _searchController,
                                              onSubmitted: (_) =>
                                                  _submitSearch(),
                                              style: Theme.of(
                                                context,
                                              ).textTheme.bodyLarge,
                                              decoration: InputDecoration(
                                                border: InputBorder.none,
                                                hintText:
                                                    'Tell CaseSense about your case...',
                                                hintStyle: Theme.of(context)
                                                    .textTheme
                                                    .bodyMedium
                                                    ?.copyWith(
                                                      color: AppColors.warmGrey,
                                                    ),
                                              ),
                                            ),
                                          ),
                                          ElevatedButton(
                                            onPressed: _submitSearch,
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor:
                                                  AppColors.charcoal,
                                              foregroundColor: AppColors.ivory,
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                    horizontal: 24,
                                                    vertical: 14,
                                                  ),
                                              shape: RoundedRectangleBorder(
                                                borderRadius:
                                                    BorderRadius.circular(30),
                                              ),
                                            ),
                                            child: const Icon(
                                              Icons.arrow_forward,
                                              size: 18,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(height: 16),
                                    OutlinedButton.icon(
                                      onPressed: _uploadDocument,
                                      icon: const Icon(
                                        Icons.upload_file,
                                        size: 18,
                                      ),
                                      label: const Text('Upload document'),
                                    ),
                                    const SizedBox(height: 24),
                                    Row(
                                      children: [
                                        _FeatureBadge(
                                          icon: Icons.translate,
                                          title: 'Multi-language',
                                          subtitle:
                                              'English / हिंदी / Bilingual',
                                        ),
                                        const SizedBox(width: 24),
                                        Container(
                                          height: 30,
                                          width: 1,
                                          color: AppColors.stone,
                                        ),
                                        const SizedBox(width: 24),
                                        _FeatureBadge(
                                          icon: Icons.verified_user_outlined,
                                          title: 'Court-ready',
                                          subtitle: 'With relevant citations',
                                        ),
                                        const SizedBox(width: 24),
                                        Container(
                                          height: 30,
                                          width: 1,
                                          color: AppColors.stone,
                                        ),
                                        const SizedBox(width: 24),
                                        _FeatureBadge(
                                          icon: Icons.lock_outline,
                                          title: 'Secure & Private',
                                          subtitle: 'Your data stays yours',
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.only(
                      left: 56.0,
                      right: 56.0,
                      bottom: 40.0,
                    ),
                    color: AppColors.parchment,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 40),
                        // Quick Actions (mockup: "Jump into what you need to do")
                        Text(
                          'Quick Actions',
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Jump into what you need to do.',
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(color: AppColors.warmGrey),
                        ),
                        const SizedBox(height: 20),
                        Row(
                          children: [
                            Expanded(
                              child: _QuickActionCard(
                                icon: Icons.edit_document,
                                title: 'Draft a Document',
                                subtitle: 'Generate legal documents',
                                onTap: () => context.push('/drafts_list'),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: _QuickActionCard(
                                icon: Icons.manage_search,
                                title: 'Find Citations',
                                subtitle: 'Search verified authorities',
                                onTap: () => context.push('/finder'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 40),

                        // Recent Drafts + Recent Searches (two columns) — authed only.
                        // Guests see a registration upsell card instead.
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 5,
                              child: isAuthed
                                  ? _RecentDraftsSection(firstName: firstName)
                                  : _GuestUpsellCard(),
                            ),
                            const SizedBox(width: 24),
                            Expanded(
                              flex: 4,
                              child: isAuthed
                                  ? Column(
                                      children: [
                                        _RecentSearchesSection(
                                          sessions: researchSessions,
                                        ),
                                        const SizedBox(height: 24),
                                        _SavedCitationsPreview(
                                          count: savedState.citations.length,
                                        ),
                                        const SizedBox(height: 24),
                                        _LibraryBrowseSection(),
                                      ],
                                    )
                                  : Column(
                                      children: [
                                        const _RecentSearchesSection(),
                                      ],
                                    ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Sections ──────────────────────────────────────────────────────────────────

class _GuestUpsellCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: AppColors.parchment.withOpacity(0.96),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.antiqueBrass.withOpacity(0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.workspace_premium,
                color: AppColors.antiqueBrass,
                size: 22,
              ),
              const SizedBox(width: 10),
              Text(
                'Unlock the full workspace',
                style: Theme.of(
                  context,
                ).textTheme.headlineMedium?.copyWith(fontSize: 20),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Create a free account to draft documents, save citations, keep your research history and build your library.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              ElevatedButton.icon(
                onPressed: () => context.push('/register'),
                icon: const Icon(Icons.person_add_alt_1, size: 16),
                label: const Text('Create Free Account'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.antiqueBrass,
                  foregroundColor: AppColors.ivory,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 14,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              TextButton(
                onPressed: () => context.push('/login'),
                child: const Text('Sign In'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LanguageChip extends StatelessWidget {
  final String label;
  const _LanguageChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.charcoal.withOpacity(0.6),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.stone.withOpacity(0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.language, color: AppColors.antiqueBrass, size: 16),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: AppColors.ivory,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

class _FeatureBadge extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _FeatureBadge({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.parchment,
            shape: BoxShape.circle,
            border: Border.all(color: AppColors.stone),
          ),
          child: Icon(icon, size: 16, color: AppColors.charcoal),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontSize: 13),
            ),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.warmGrey,
                fontSize: 11,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tactile3DCard(
      depth: 0.02,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.parchment,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.stone),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.charcoal,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: AppColors.ivory, size: 22),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(
                        context,
                      ).textTheme.titleMedium?.copyWith(fontSize: 15),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.subtleBronze,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.arrow_forward,
                color: AppColors.charcoal,
                size: 18,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RecentDraftsSection extends ConsumerWidget {
  final String firstName;
  const _RecentDraftsSection({required this.firstName});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mattersState = ref.watch(mattersListControllerProvider);

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.parchment.withOpacity(0.96),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.stone),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Recent Drafts',
                style: Theme.of(
                  context,
                ).textTheme.headlineMedium?.copyWith(fontSize: 20),
              ),
              InkWell(
                onTap: () => context.push('/drafts_list'),
                child: Text(
                  'View All →',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: AppColors.subtleBronze,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (mattersState.matters.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Text(
                'No drafts yet. Create a matter in History, then start drafting.',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
              ),
            )
          else
            ...mattersState.matters
                .take(4)
                .map(
                  (matter) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: InkWell(
                      onTap: () => context.push('/matters/${matter['id']}'),
                      borderRadius: BorderRadius.circular(8),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppColors.charcoal,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Icon(
                              Icons.description,
                              color: AppColors.ivory,
                              size: 16,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  matter['title'] ?? 'Untitled',
                                  style: Theme.of(context).textTheme.titleMedium
                                      ?.copyWith(fontSize: 14),
                                  overflow: TextOverflow.ellipsis,
                                ),
                                Text(
                                  '${matter['matter_type'] ?? 'matter'} • ${matter['court_name'] ?? '—'}',
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(
                                        color: AppColors.subtleBronze,
                                        fontSize: 11,
                                      ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.chevron_right,
                            color: AppColors.warmGrey,
                            size: 18,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}

class _RecentSearchesSection extends StatelessWidget {
  final List<Map<String, dynamic>> sessions;

  const _RecentSearchesSection({this.sessions = const []});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.ivory,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.stone),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Recent Searches',
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(fontSize: 20),
          ),
          const SizedBox(height: 16),
          if (sessions.isEmpty)
            Text(
              'Your searches will appear here.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
            )
          else
            for (final session in sessions.take(3))
              _SearchItem(
                context,
                session['query_text']?.toString() ?? 'Research query',
                onTap: () {
                  final id = session['id']?.toString();
                  if (id != null)
                    context.push(
                      session['status'] == 'COMPLETED'
                          ? '/research/$id/results'
                          : '/research/$id/status',
                    );
                },
              ),
          const SizedBox(height: 8),
          InkWell(
            onTap: () => context.push('/finder'),
            child: Text(
              'Open Citation Finder →',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: AppColors.subtleBronze,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _SearchItem(
    BuildContext context,
    String query, {
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          children: [
            const Icon(Icons.history, color: AppColors.warmGrey, size: 16),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                query,
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(fontSize: 13),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SavedCitationsPreview extends StatelessWidget {
  final int count;
  const _SavedCitationsPreview({required this.count});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.parchment.withOpacity(0.96),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.stone),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Saved Citations',
                style: Theme.of(
                  context,
                ).textTheme.headlineMedium?.copyWith(fontSize: 20),
              ),
              Text(
                '$count saved',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.subtleBronze,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => context.push('/saved-citations'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.charcoal,
                side: const BorderSide(color: AppColors.stone),
              ),
              child: const Text('View All Saved Citations'),
            ),
          ),
        ],
      ),
    );
  }
}

class _LibraryBrowseSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.espresso,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.charcoal),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.local_library,
                color: AppColors.antiqueBrass,
                size: 20,
              ),
              const SizedBox(width: 10),
              Text(
                'Library',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontSize: 20,
                  color: AppColors.ivory,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Browse matter documents and legal references.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: AppColors.warmGrey,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => context.push('/library'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.ivory,
                side: const BorderSide(color: AppColors.charcoal),
              ),
              child: const Text('Browse Library'),
            ),
          ),
        ],
      ),
    );
  }
}
