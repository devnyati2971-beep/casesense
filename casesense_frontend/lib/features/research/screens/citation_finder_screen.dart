import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../auth/providers/auth_controller.dart';
import '../providers/research_controller.dart';
import '../providers/research_list_controller.dart';

// --- Helper Widgets Below ---

class CitationFinderScreen extends ConsumerStatefulWidget {
  const CitationFinderScreen({super.key});

  @override
  ConsumerState<CitationFinderScreen> createState() =>
      _CitationFinderScreenState();
}

class _CitationFinderScreenState extends ConsumerState<CitationFinderScreen> {
  final TextEditingController _queryController = TextEditingController();

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (ref.read(authControllerProvider).value?.isAuthenticated ?? false) {
        ref.read(researchListControllerProvider.notifier).load();
      }
    });
  }

  void _submitQuery() async {
    final query = _queryController.text.trim();
    if (query.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a legal query first.')),
      );
      return;
    }

    final sessionId = await ref
        .read(researchControllerProvider.notifier)
        .submitQuery(query);

    if (!mounted) return;

    // v2.2 guest tier: both free searches used — offer registration.
    if (ref.read(researchControllerProvider).guestLimitReached) {
      _showGuestLimitDialog();
      return;
    }

    if (sessionId != null) {
      context.push('/research/$sessionId/status');
    }
  }

  void _showGuestLimitDialog() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.parchment,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const Icon(Icons.lock_outline, color: AppColors.antiqueBrass),
            const SizedBox(width: 12),
            Text(
              'Free searches used',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'You have used both free Citation Finder searches. Create a free account to continue searching, save citations, and unlock drafting, history and your library.',
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(color: AppColors.charcoal),
            ),
            const SizedBox(height: 16),
            Text(
              'Guest quota resets after 24 hours.',
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: AppColors.subtleBronze),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Maybe later'),
          ),
          FilledButton.icon(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              context.push('/register');
            },
            icon: const Icon(Icons.person_add_alt_1, size: 16),
            label: const Text('Create Free Account'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.antiqueBrass,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _uploadDocument() async {
    if (ref.read(authControllerProvider).value?.isAuthenticated != true) {
      context.push('/login?from=/finder');
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
    final isAuthed =
        ref.watch(authControllerProvider).value?.isAuthenticated ?? false;
    final recentSearches = ref.watch(researchListControllerProvider).sessions;

    return Scaffold(
      backgroundColor: AppColors.parchment,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/finder'),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(40.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header section
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.arrow_back, size: 20),
                            onPressed: () => context.pop(),
                          ),
                        ],
                      ),
                      Row(
                        children: [
                          const Icon(
                            Icons.notifications_none,
                            color: AppColors.charcoal,
                            size: 20,
                          ),
                          const SizedBox(width: 16),
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: AppColors.nearBlack,
                            child: const Text(
                              'K',
                              style: TextStyle(
                                color: AppColors.ivory,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // Dark Hero Search Card
                  Container(
                    width: double.infinity,
                    clipBehavior: Clip.hardEdge,
                    decoration: BoxDecoration(
                      color: AppColors.nearBlack,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Stack(
                      children: [
                        Positioned(
                          right: -50,
                          top: -50,
                          bottom: -50,
                          width: 400,
                          child: Opacity(
                            opacity: 0.5,
                            child: Image.asset(
                              'assets/images/dashboard_img.png',
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const SizedBox(),
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 40,
                            vertical: 48,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Find the Right Authority',
                                style: Theme.of(context).textTheme.displayMedium
                                    ?.copyWith(color: AppColors.ivory),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Search from a vast database of judgments, acts, and legal provisions.',
                                style: Theme.of(context).textTheme.bodyLarge
                                    ?.copyWith(color: AppColors.stone),
                              ),
                              const SizedBox(height: 32),

                              // Search Input
                              Container(
                                width: 700,
                                decoration: BoxDecoration(
                                  color: AppColors.ivory,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Row(
                                  children: [
                                    const Padding(
                                      padding: EdgeInsets.symmetric(
                                        horizontal: 16,
                                      ),
                                      child: Icon(
                                        Icons.search,
                                        color: AppColors.warmGrey,
                                      ),
                                    ),
                                    Expanded(
                                      child: TextField(
                                        controller: _queryController,
                                        onSubmitted: (_) => _submitQuery(),
                                        style: Theme.of(
                                          context,
                                        ).textTheme.bodyLarge,
                                        decoration: InputDecoration(
                                          border: InputBorder.none,
                                          hintText:
                                              'E.g. Article 21, bail, criminal procedure, landmark judgment...',
                                          hintStyle: Theme.of(context)
                                              .textTheme
                                              .bodyMedium
                                              ?.copyWith(
                                                color: AppColors.warmGrey,
                                              ),
                                        ),
                                      ),
                                    ),
                                    Container(
                                      margin: const EdgeInsets.all(4),
                                      child: ElevatedButton(
                                        onPressed: _submitQuery,
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: AppColors.nearBlack,
                                          foregroundColor: AppColors.ivory,
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(
                                              6,
                                            ),
                                          ),
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 24,
                                            vertical: 14,
                                          ),
                                        ),
                                        child: const Icon(
                                          Icons.search,
                                          size: 20,
                                        ),
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
                                  color: AppColors.ivory,
                                  size: 18,
                                ),
                                label: const Text(
                                  'Upload a document',
                                  style: TextStyle(color: AppColors.ivory),
                                ),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(
                                    color: AppColors.stone,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 40),

                  // Recent Searches List
                  if (isAuthed) ...[
                    Text(
                      'Recent Searches',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 16),
                    if (recentSearches.isEmpty)
                      Text(
                        'Your completed and in-progress searches will appear here.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: AppColors.warmGrey,
                        ),
                      )
                    else
                      for (final search in recentSearches.take(8))
                        _RecentSearchItem(
                          query:
                              search['query_text']?.toString() ??
                              'Research query',
                          time:
                              search['created_at']
                                  ?.toString()
                                  .split('T')
                                  .first ??
                              '',
                          onTap: () {
                            final id = search['id']?.toString();
                            if (id == null) return;
                            context.push(
                              search['status'] == 'COMPLETED'
                                  ? '/research/$id/results'
                                  : '/research/$id/status',
                            );
                          },
                        ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentSearchItem extends StatelessWidget {
  final String query;
  final String time;
  final VoidCallback onTap;

  const _RecentSearchItem({
    required this.query,
    required this.time,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: AppColors.ivory,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.stone),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                const Icon(Icons.search, color: AppColors.warmGrey, size: 18),
                const SizedBox(width: 12),
                Text(
                  query,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(fontSize: 15),
                ),
              ],
            ),
            Row(
              children: [
                Text(
                  time,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.warmGrey,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(width: 16),
                const Icon(
                  Icons.chevron_right,
                  color: AppColors.warmGrey,
                  size: 20,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
