import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../auth/providers/auth_controller.dart';
import '../providers/research_controller.dart';

// --- Helper Widgets Below ---

class CitationFinderScreen extends ConsumerStatefulWidget {
  const CitationFinderScreen({super.key});

  @override
  ConsumerState<CitationFinderScreen> createState() => _CitationFinderScreenState();
}

class _CitationFinderScreenState extends ConsumerState<CitationFinderScreen> {
  final TextEditingController _queryController = TextEditingController();

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  void _submitQuery() async {
    final query = _queryController.text.trim();
    if (query.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a legal query first.')),
      );
      return;
    }

    final sessionId = await ref.read(researchControllerProvider.notifier).submitQuery(query);

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
            Text('Free searches used', style: Theme.of(context).textTheme.titleLarge),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'You have used both free Citation Finder searches. Create a free account to continue searching, save citations, and unlock drafting, history and your library.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.charcoal),
            ),
            const SizedBox(height: 16),
            Text(
              'Guest quota resets after 24 hours.',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.subtleBronze),
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
            style: FilledButton.styleFrom(backgroundColor: AppColors.antiqueBrass),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final researchState = ref.watch(researchControllerProvider);
    final isAuthed = ref.watch(authControllerProvider).value?.isAuthenticated ?? false;

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
                          IconButton(icon: const Icon(Icons.arrow_back, size: 20), onPressed: () => context.pop()),
                        ],
                      ),
                      Row(
                        children: [
                          const Icon(Icons.notifications_none, color: AppColors.charcoal, size: 20),
                          const SizedBox(width: 16),
                          CircleAvatar(
                            radius: 14,
                            backgroundColor: AppColors.nearBlack,
                            child: const Text('K', style: TextStyle(color: AppColors.ivory, fontSize: 12)),
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
                          padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 48),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Find the Right Authority',
                                style: Theme.of(context).textTheme.displayMedium?.copyWith(color: AppColors.ivory),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Search from a vast database of judgments, acts, and legal provisions.',
                                style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.stone),
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
                                      padding: EdgeInsets.symmetric(horizontal: 16),
                                      child: Icon(Icons.search, color: AppColors.warmGrey),
                                    ),
                                    Expanded(
                                      child: TextField(
                                        controller: _queryController,
                                        onSubmitted: (_) => _submitQuery(),
                                        style: Theme.of(context).textTheme.bodyLarge,
                                        decoration: InputDecoration(
                                          border: InputBorder.none,
                                          hintText: 'E.g. Article 21, bail, criminal procedure, landmark judgment...',
                                          hintStyle: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
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
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                                        ),
                                        child: const Icon(Icons.search, size: 20),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 24),
                              
                              // Filter Chips
                              Row(
                                children: [
                                  _FilterChip(label: 'All', isSelected: true),
                                  const SizedBox(width: 12),
                                  _FilterChip(label: 'Judgments'),
                                  const SizedBox(width: 12),
                                  _FilterChip(label: 'Acts'),
                                  const SizedBox(width: 12),
                                  _FilterChip(label: 'Rules'),
                                  const SizedBox(width: 12),
                                  _FilterChip(label: 'Legal Provisions'),
                                  const SizedBox(width: 12),
                                  _FilterChip(label: 'Articles'),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  
                  const SizedBox(height: 40),
                  
                  // Popular Searches
                  Text('Popular Searches', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      _PopularSearchChip(label: 'Article 21'),
                      const SizedBox(width: 12),
                      _PopularSearchChip(label: 'Bail'),
                      const SizedBox(width: 12),
                      _PopularSearchChip(label: 'Criminal Procedure Code'),
                      const SizedBox(width: 12),
                      _PopularSearchChip(label: 'Fundamental Rights'),
                      const SizedBox(width: 12),
                      _PopularSearchChip(label: 'Supreme Court'),
                      const SizedBox(width: 12),
                      _PopularSearchChip(label: 'High Court'),
                    ],
                  ),
                  
                  const SizedBox(height: 40),
                  
                  // Recent Searches List
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Recent Searches', style: Theme.of(context).textTheme.titleMedium),
                      Text('View all →', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 13)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _RecentSearchItem(query: 'bail under section 439', time: '2 hours ago'),
                  _RecentSearchItem(query: 'article 226 writ petition', time: '4 hours ago'),
                  _RecentSearchItem(query: 'landmark judgment on privacy', time: '1 day ago'),
                  _RecentSearchItem(query: 'section 302 ipc', time: '1 day ago'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;

  const _FilterChip({required this.label, this.isSelected = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: isSelected ? AppColors.ivory : Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: isSelected ? AppColors.ivory : AppColors.warmGrey),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: isSelected ? AppColors.nearBlack : AppColors.ivory,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
        ),
      ),
    );
  }
}

class _PopularSearchChip extends StatelessWidget {
  final String label;

  const _PopularSearchChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.ivory,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.stone),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.charcoal, fontSize: 13),
      ),
    );
  }
}

class _RecentSearchItem extends StatelessWidget {
  final String query;
  final String time;

  const _RecentSearchItem({required this.query, required this.time});

  @override
  Widget build(BuildContext context) {
    return Container(
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
              Text(query, style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontSize: 15)),
            ],
          ),
          Row(
            children: [
              Text(time, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 13)),
              const SizedBox(width: 16),
              const Icon(Icons.chevron_right, color: AppColors.warmGrey, size: 20),
            ],
          ),
        ],
      ),
    );
  }
}