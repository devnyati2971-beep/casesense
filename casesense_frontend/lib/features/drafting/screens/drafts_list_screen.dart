import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/status_chip.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../matters/providers/matters_list_controller.dart';
import '../providers/drafts_controller.dart';

class DraftsListScreen extends ConsumerStatefulWidget {
  const DraftsListScreen({super.key});

  @override
  ConsumerState<DraftsListScreen> createState() => _DraftsListScreenState();
}

class _DraftsListScreenState extends ConsumerState<DraftsListScreen> {
  String? _selectedMatterId;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(mattersListControllerProvider.notifier).load();
    });
  }

  Future<void> _loadDraftsFor(String matterId) async {
    setState(() => _selectedMatterId = matterId);
    await ref.read(draftsControllerProvider.notifier).loadDrafts(matterId);
  }

  @override
  Widget build(BuildContext context) {
    final mattersState = ref.watch(mattersListControllerProvider);
    final draftsState = ref.watch(draftsControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/drafts_list'),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(64.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.edit_document, color: AppColors.charcoal, size: 28),
                          const SizedBox(width: 16),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Drafting', style: Theme.of(context).textTheme.displayMedium),
                              const SizedBox(height: 4),
                              Text('Your AI-assisted legal drafts', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                            ],
                          ),
                        ],
                      ),
                      draftsState.isLoading
                        ? const CircularProgressIndicator(color: AppColors.antiqueBrass)
                        : PrimaryButton(
                            label: '+ New Draft',
                            onPressed: () => context.push('/drafts/new'),
                          ),
                    ],
                  ),
                  const SizedBox(height: 32),

                  // Matter selector
                  if (mattersState.matters.isNotEmpty) ...[
                    Row(
                      children: [
                        Text('Matter:', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.subtleBronze)),
                        const SizedBox(width: 12),
                        DropdownButton<String>(
                          value: _selectedMatterId,
                          underline: const SizedBox.shrink(),
                          hint: const Text('Select a matter'),
                          items: [
                            for (final m in mattersState.matters)
                              DropdownMenuItem(
                                value: m['id']?.toString(),
                                child: Text(m['title'] ?? 'Untitled', overflow: TextOverflow.ellipsis),
                              ),
                          ],
                          onChanged: (v) {
                            if (v != null) _loadDraftsFor(v);
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                  ],

                  if (draftsState.error != null) ...[
                    Text(draftsState.error!, style: const TextStyle(color: AppColors.error)),
                    const SizedBox(height: 24),
                  ],

                  if (_selectedMatterId == null && mattersState.matters.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 80),
                      child: Center(
                        child: Column(
                          children: [
                            const Icon(Icons.edit_document, size: 64, color: AppColors.stone),
                            const SizedBox(height: 16),
                            Text('No matters yet', style: Theme.of(context).textTheme.headlineMedium),
                            const SizedBox(height: 8),
                            Text('Create a matter in History, then start drafting here.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                          ],
                        ),
                      ),
                    )
                  else if (draftsState.drafts.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 40),
                      child: Center(
                        child: Text(
                          'No drafts for this matter yet. Use “+ New Draft” to begin.',
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze),
                        ),
                      ),
                    )
                  else
                    for (final draft in draftsState.drafts)
                      _DraftListItem(
                        title: draft['title'] ?? 'Untitled Draft',
                        subtitle: '${draft['document_type'] ?? 'DRAFT'} • v${draft['version'] ?? 1}',
                        status: _statusLabel(draft['status']?.toString() ?? 'CREATED'),
                        onTap: () => context.push('/drafts/${draft['id']}'),
                      ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _statusLabel(String status) {
    switch (status.toUpperCase()) {
      case 'FINALIZED':
        return 'Finalized';
      case 'GENERATED':
      case 'LAWYER_REVIEW':
        return 'In Progress';
      case 'FAILED':
        return 'Failed';
      default:
        return 'Draft';
    }
  }
}

class _DraftListItem extends StatelessWidget {
  final String title;
  final String subtitle;
  final String status;
  final VoidCallback onTap;

  const _DraftListItem({
    required this.title,
    required this.subtitle,
    required this.status,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // Map string status to our StatusChip logic
    String chipStatus = 'PROCESSING';
    if (status == 'Finalized') chipStatus = 'PROCESSED';
    if (status == 'Archived' || status == 'Draft' || status == 'Failed') chipStatus = 'UPLOADED';

    return Padding(
      padding: const EdgeInsets.only(bottom: 24.0),
      child: Tactile3DCard(
        depth: 0.015,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.parchment,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.stone),
              boxShadow: [
                BoxShadow(
                  color: AppColors.nearBlack.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                )
              ],
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.charcoal,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.description, color: AppColors.ivory, size: 24),
                ),
                const SizedBox(width: 24),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 18)),
                      const SizedBox(height: 6),
                      Text(subtitle, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey)),
                    ],
                  ),
                ),
                StatusChip(status: chipStatus),
                const SizedBox(width: 24),
                const Icon(Icons.chevron_right, color: AppColors.charcoal),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
