import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../drafting/providers/drafts_controller.dart';
import '../../research/providers/saved_citations_controller.dart';
import '../../research/providers/research_list_controller.dart';
import '../providers/matters_list_controller.dart';

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});

  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  int _selected = -1;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(mattersListControllerProvider.notifier).load();
      ref.read(draftsControllerProvider.notifier).loadAllDrafts();
      ref.read(researchListControllerProvider.notifier).load();
      ref.read(savedCitationsControllerProvider.notifier).load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final draftsState = ref.watch(draftsControllerProvider);
    final researchState = ref.watch(researchListControllerProvider);
    final savedState = ref.watch(savedCitationsControllerProvider);

    // Combined history entries: drafts + research + citations (+ matters)
    final entries = <_HistoryEntry>[
      for (final d in draftsState.allDrafts)
        _HistoryEntry(
          icon: Icons.edit_document,
          type: 'Draft',
          title: d['title']?.toString() ?? 'Untitled Draft',
          subtitle: '${d['document_type'] ?? ''} • ${d['matter_title'] ?? ''}',
          when: d['updated_at']?.toString(),
          color: AppColors.antiqueBrass,
          data: d,
          kind: _HistoryKind.draft,
        ),
      for (final r in researchState.sessions)
        _HistoryEntry(
          icon: Icons.manage_search,
          type: 'Research',
          title: r['query_text']?.toString() ?? 'Case research',
          subtitle: r['mode']?.toString() ?? 'QUERY',
          when: r['created_at']?.toString(),
          color: AppColors.success,
          data: r,
          kind: _HistoryKind.research,
        ),
      for (final c in savedState.citations)
        _HistoryEntry(
          icon: Icons.bookmark,
          type: 'Citation',
          title: c['case_name']?.toString() ?? 'Saved citation',
          subtitle: c['citation_text']?.toString() ?? '',
          when: c['created_at']?.toString(),
          color: AppColors.error,
          data: c,
          kind: _HistoryKind.citation,
        ),
    ];

    return Scaffold(
      backgroundColor: AppColors.parchment,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/history'),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(48.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('History', style: Theme.of(context).textTheme.displayMedium),
                          const SizedBox(height: 8),
                          Text('View and manage all your past cases, drafts and research.',
                            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                        ],
                      ),
                      PrimaryButton(label: '+ New Matter', onPressed: _showCreateMatterDialog),
                    ],
                  ),
                  const SizedBox(height: 32),
                  Expanded(
                    child: entries.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Icon(Icons.history, size: 64, color: AppColors.stone),
                                const SizedBox(height: 16),
                                Text('Nothing here yet', style: Theme.of(context).textTheme.headlineMedium),
                                const SizedBox(height: 8),
                                Text('Drafts, research runs and saved citations will appear here.',
                                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                              ],
                            ),
                          )
                        : Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // List column
                              Expanded(
                                flex: 5,
                                child: ListView.builder(
                                  itemCount: entries.length,
                                  itemBuilder: (context, index) {
                                    final entry = entries[index];
                                    return Padding(
                                      padding: const EdgeInsets.only(bottom: 12),
                                      child: _HistoryCard(
                                        entry: entry,
                                        isSelected: _selected == index,
                                        onTap: () => setState(() => _selected = index),
                                      ),
                                    );
                                  },
                                ),
                              ),
                              const SizedBox(width: 24),
                              // Detail column
                              Expanded(
                                flex: 3,
                                child: _selected >= 0 && _selected < entries.length
                                    ? _HistoryDetail(entry: entries[_selected])
                                    : Container(
                                        padding: const EdgeInsets.all(32),
                                        decoration: BoxDecoration(
                                          color: AppColors.parchment,
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(color: AppColors.stone),
                                        ),
                                        child: Center(
                                          child: Text(
                                            'Select an item to preview it.',
                                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
                                          ),
                                        ),
                                      ),
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

  Future<void> _showCreateMatterDialog() async {
    final titleController = TextEditingController();
    final caseNumberController = TextEditingController();
    final courtController = TextEditingController();

    final matterId = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: AppColors.ivory,
          title: const Text('New Matter'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleController,
                decoration: const InputDecoration(labelText: 'Title *', hintText: 'State v. Ramesh Kumar'),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: caseNumberController,
                decoration: const InputDecoration(labelText: 'Case Number', hintText: 'BAIL/2026/104'),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: courtController,
                decoration: const InputDecoration(labelText: 'Court', hintText: 'Supreme Court of India'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            PrimaryButton(
              label: 'Create',
              onPressed: () async {
                if (titleController.text.trim().isEmpty) return;
                final id = await ref.read(mattersListControllerProvider.notifier).createMatter(
                  title: titleController.text.trim(),
                  caseNumber: caseNumberController.text.trim().isEmpty ? null : caseNumberController.text.trim(),
                  courtName: courtController.text.trim().isEmpty ? null : courtController.text.trim(),
                );
                if (dialogContext.mounted) Navigator.pop(dialogContext, id);
              },
            ),
          ],
        );
      },
    );

    if (matterId != null && mounted) {
      context.push('/matters/$matterId');
    }
  }
}

enum _HistoryKind { draft, research, citation }

class _HistoryEntry {
  final IconData icon;
  final String type;
  final String title;
  final String subtitle;
  final String? when;
  final Color color;
  final Map<String, dynamic> data;
  final _HistoryKind kind;

  _HistoryEntry({
    required this.icon,
    required this.type,
    required this.title,
    required this.subtitle,
    required this.when,
    required this.color,
    required this.data,
    required this.kind,
  });
}

class _HistoryCard extends StatelessWidget {
  final _HistoryEntry entry;
  final bool isSelected;
  final VoidCallback onTap;

  const _HistoryCard({required this.entry, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Tactile3DCard(
      depth: 0.01,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.ivory : AppColors.ivory.withOpacity(0.5),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: isSelected ? AppColors.antiqueBrass : AppColors.stone, width: isSelected ? 2 : 1),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: entry.color.withOpacity(0.12), borderRadius: BorderRadius.circular(8)),
                child: Icon(entry.icon, color: entry.color, size: 20),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(entry.title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 15), overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 4),
                    Text(
                      '${entry.type}${entry.subtitle.isNotEmpty ? ' • ${entry.subtitle}' : ''}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 12),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              if (entry.when != null)
                Text(
                  entry.when.toString().split('T').first,
                  style: Theme.of(context).textTheme.labelSmall,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HistoryDetail extends ConsumerWidget {
  final _HistoryEntry entry;

  const _HistoryDetail({required this.entry});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: AppColors.ivory,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.stone),
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: entry.color.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(entry.type.toUpperCase(), style: Theme.of(context).textTheme.labelSmall?.copyWith(color: entry.color)),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(entry.title, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 22)),
            if (entry.subtitle.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(entry.subtitle, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey)),
            ],
            const SizedBox(height: 24),
            ..._buildActions(context, ref),
            const SizedBox(height: 24),
            _buildBody(context),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildActions(BuildContext context, WidgetRef ref) {
    switch (entry.kind) {
      case _HistoryKind.draft:
        return [
          SizedBox(
            width: double.infinity,
            child: PrimaryButton(
              label: 'Open Draft',
              onPressed: () => context.push('/drafts/${entry.data['id']}'),
            ),
          ),
        ];
      case _HistoryKind.research:
        final sid = entry.data['id']?.toString() ?? '';
        final status = entry.data['status']?.toString() ?? '';
        return [
          SizedBox(
            width: double.infinity,
            child: PrimaryButton(
              label: status == 'COMPLETED' ? 'View Results' : 'View Status',
              onPressed: () => context.push(
                status == 'COMPLETED' ? '/research/$sid/results' : '/research/$sid/status',
              ),
            ),
          ),
        ];
      case _HistoryKind.citation:
        return [
          SizedBox(
            width: double.infinity,
            child: PrimaryButton(
              label: 'View Saved Citation',
              onPressed: () => context.push('/saved-citations'),
            ),
          ),
        ];
    }
  }

  Widget _buildBody(BuildContext context) {
    final notes = entry.data['note'];
    final status = entry.data['status'];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (status != null)
          _DetailRow(label: 'Status', value: status.toString()),
        if (entry.when != null)
          _DetailRow(label: 'When', value: entry.when.toString().split('.').first),
        if (entry.data['document_type'] != null)
          _DetailRow(label: 'Document Type', value: entry.data['document_type'].toString()),
        if (entry.data['version'] != null)
          _DetailRow(label: 'Version', value: entry.data['version'].toString()),
        if (notes?.toString().isNotEmpty == true) ...[
          const SizedBox(height: 12),
          Text('Note', style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 4),
          Text(notes.toString(), style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontStyle: FontStyle.italic)),
        ],
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 120, child: Text(label, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey))),
          Expanded(child: Text(value, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}
