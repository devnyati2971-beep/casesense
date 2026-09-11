import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../../shared/widgets/status_chip.dart';
import '../providers/saved_citations_controller.dart';

class SavedCitationsScreen extends ConsumerStatefulWidget {
  const SavedCitationsScreen({super.key});

  @override
  ConsumerState<SavedCitationsScreen> createState() =>
      _SavedCitationsScreenState();
}

class _SavedCitationsScreenState extends ConsumerState<SavedCitationsScreen> {
  final TextEditingController _searchController = TextEditingController();
  Map<String, dynamic>? _selected;
  final Map<String, int> _counts = {};

  static const List<(String, String)> _filters = [
    ('all', 'All'),
    ('judgment', 'Judgments'),
    ('act', 'Acts'),
    ('article', 'Articles'),
    ('other', 'Others'),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    await ref.read(savedCitationsControllerProvider.notifier).load();
    _loadCounts();
  }

  Future<void> _loadCounts() async {
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get('/saved-citations/counts');
      final data = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : {};
      if (mounted) setState(() => _counts.addAll(data.cast<String, int>()));
    } catch (_) {}
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(savedCitationsControllerProvider);
    final isWide = MediaQuery.of(context).size.width > 1400;

    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/saved-citations'),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 6,
                  child: _ListLayout(
                    state: state,
                    searchController: _searchController,
                    counts: _counts,
                    filters: _filters,
                    onSelect: (c) => setState(() => _selected = c),
                    onFilter: (t) => ref
                        .read(savedCitationsControllerProvider.notifier)
                        .setFilter(t),
                    onSearch: (q) => ref
                        .read(savedCitationsControllerProvider.notifier)
                        .search(q),
                  ),
                ),
                if (_selected != null && isWide)
                  Expanded(
                    flex: 4,
                    child: Container(
                      decoration: const BoxDecoration(
                        border: Border(
                          left: BorderSide(color: AppColors.stone),
                        ),
                      ),
                      child: _DetailLayout(
                        citation: _selected!,
                        onBack: () => setState(() => _selected = null),
                        onTranslate: () => _translate(_selected!),
                        onShare: (text) => _share(text),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _translate(Map<String, dynamic> citation) async {
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(
        '/saved-citations/${citation['id']}/translate',
      );
      final translated = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      if (!mounted) return;
      setState(() => _selected = translated);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Hindi translation added. The detail now shows both languages.',
          ),
        ),
      );
      await _load();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Translation failed — try again.')),
      );
    }
  }

  Future<void> _share(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Citation copied to your clipboard.')),
    );
  }
}

// ── List layout (mockup left panel) ──────────────────────────────────────────

class _ListLayout extends StatelessWidget {
  final SavedCitationsState state;
  final TextEditingController searchController;
  final Map<String, int> counts;
  final List<(String, String)> filters;
  final void Function(Map<String, dynamic>) onSelect;
  final void Function(String) onFilter;
  final void Function(String) onSearch;

  const _ListLayout({
    required this.state,
    required this.searchController,
    required this.counts,
    required this.filters,
    required this.onSelect,
    required this.onFilter,
    required this.onSearch,
  });

  @override
  Widget build(BuildContext context) {
    final citations = state.citations;
    final activeFilter = state.filter;

    return Column(
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.fromLTRB(48, 40, 48, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Saved Citations',
                    style: Theme.of(context).textTheme.displayMedium,
                  ),
                  ElevatedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Add Citation'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.charcoal,
                      foregroundColor: AppColors.ivory,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 12,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Your collection of important judgments, cases, and legal authorities.',
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey),
              ),
              const SizedBox(height: 24),

              // Count chips: All (12) Judgments (8) Acts (2)...
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (final (type, label) in filters)
                    _CountChip(
                      label: counts[type] != null && type != 'all'
                          ? '$label (${counts[type]})'
                          : type == 'all' && counts['all'] != null
                          ? '$label (${counts['all']})'
                          : label,
                      isActive: activeFilter == type,
                      onTap: () => onFilter(type),
                    ),
                ],
              ),
              const SizedBox(height: 16),

              // Search + sort row
              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.parchment,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: AppColors.stone),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.search,
                            color: AppColors.subtleBronze,
                            size: 18,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: TextField(
                              controller: searchController,
                              onChanged: onSearch,
                              decoration: const InputDecoration(
                                border: InputBorder.none,
                                hintText: 'Search saved citations...',
                                isDense: true,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(
                      color: AppColors.parchment,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: AppColors.stone),
                    ),
                    child: DropdownButton<String>(
                      value: 'recent',
                      underline: const SizedBox.shrink(),
                      borderRadius: BorderRadius.circular(12),
                      items: const [
                        DropdownMenuItem(
                          value: 'recent',
                          child: Text(
                            'Recently Saved',
                            style: TextStyle(fontSize: 13),
                          ),
                        ),
                      ],
                      onChanged: (_) {},
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // List
        Expanded(
          child: state.isLoading && citations.isEmpty
              ? const Center(
                  child: CircularProgressIndicator(
                    color: AppColors.antiqueBrass,
                  ),
                )
              : citations.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.bookmark_outline,
                        size: 64,
                        color: AppColors.stone,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'No saved citations yet',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Use the Citation Finder to save verified authorities.',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: AppColors.subtleBronze,
                        ),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(48, 8, 48, 40),
                  itemCount: citations.length,
                  itemBuilder: (context, index) {
                    final citation = citations[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: _CitationCard(
                        citation: citation,
                        onTap: () => onSelect(citation),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

// ── Citation card (mockup row) ───────────────────────────────────────────────

class _CitationCard extends StatelessWidget {
  final Map<String, dynamic> citation;
  final VoidCallback onTap;

  const _CitationCard({required this.citation, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final caseName = citation['case_name'] ?? 'Untitled';
    final citationText = citation['citation_text'];
    final court = citation['court'];
    final decidedOn = citation['decided_on'];
    final passageText =
        citation['passage_text'] ?? citation['proposition_text'];
    final type = (citation['citation_type'] ?? 'judgment').toString();
    final tags = (citation['tags'] as List<dynamic>?) ?? const [];
    final location = citation['location_label'];

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppColors.ivory,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.stone),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    citationText != null && citationText.toString().isNotEmpty
                        ? '$caseName $citationText'
                        : caseName,
                    style: Theme.of(
                      context,
                    ).textTheme.headlineMedium?.copyWith(fontSize: 20),
                  ),
                ),
                StatusChip(status: type.toUpperCase()),
              ],
            ),
            const SizedBox(height: 10),
            // Meta row: court • date
            Wrap(
              spacing: 12,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (court?.toString().isNotEmpty == true) ...[
                  const Icon(
                    Icons.account_balance,
                    size: 13,
                    color: AppColors.warmGrey,
                  ),
                  Text(
                    court.toString(),
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
                if (decidedOn != null) ...[
                  const Icon(Icons.event, size: 13, color: AppColors.warmGrey),
                  Text(
                    decidedOn.toString().split('T').first,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
                for (final tag in tags.take(3))
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.antiqueBrass.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      tag.toString(),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: AppColors.subtleBronze,
                        fontSize: 10,
                      ),
                    ),
                  ),
              ],
            ),
            if (passageText?.toString().isNotEmpty == true) ...[
              const SizedBox(height: 14),
              Text(
                '“$passageText”',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontStyle: FontStyle.italic,
                  color: AppColors.charcoal,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            if (location?.toString().isNotEmpty == true) ...[
              const SizedBox(height: 6),
              Text(
                location.toString(),
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ── Detail layout (mockup right panel) ───────────────────────────────────────

class _DetailLayout extends StatelessWidget {
  final Map<String, dynamic> citation;
  final VoidCallback onBack;
  final Future<void> Function() onTranslate;
  final Future<void> Function(String text) onShare;

  const _DetailLayout({
    required this.citation,
    required this.onBack,
    required this.onTranslate,
    required this.onShare,
  });

  @override
  Widget build(BuildContext context) {
    final caseName = citation['case_name'] ?? 'Untitled';
    final citationText = citation['citation_text'];
    final court = citation['court'];
    final decidedOn = citation['decided_on'];
    final judges = (citation['judges'] as List<dynamic>?) ?? const [];
    const category = null; // shown via tags/provisions below
    final provisions =
        (citation['related_provisions'] as List<dynamic>?) ?? const [];
    final summary = citation['summary'];
    final passageText =
        citation['passage_text'] ?? citation['proposition_text'];
    final translated = citation['translated_passage'];
    final location = citation['location_label'];
    final supportState = citation['support_state'] ?? 'VERIFIED';
    assert(category == null);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(48, 40, 48, 40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(icon: const Icon(Icons.arrow_back), onPressed: onBack),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Saved Citation',
                  style: Theme.of(
                    context,
                  ).textTheme.displayMedium?.copyWith(fontSize: 28),
                ),
              ),
              // Action row (mockup: Save ✓ | Translate to Hindi | Share)
              OutlinedButton.icon(
                onPressed: () => Clipboard.setData(
                  ClipboardData(text: '$caseName ${citationText ?? ''}'.trim()),
                ),
                icon: const Icon(Icons.bookmark, size: 16),
                label: const Text('Saved'),
              ),
              const SizedBox(width: 10),
              OutlinedButton.icon(
                onPressed: () => onTranslate(),
                icon: const Icon(Icons.g_translate, size: 16),
                label: const Text('Translate to Hindi'),
              ),
              const SizedBox(width: 10),
              OutlinedButton.icon(
                onPressed: () =>
                    onShare('$caseName\n${citationText ?? ''}\n\n$passageText'),
                icon: const Icon(Icons.share_outlined, size: 16),
                label: const Text('Share'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            caseName,
            style: Theme.of(
              context,
            ).textTheme.displayMedium?.copyWith(fontSize: 34),
          ),
          if (citationText?.toString().isNotEmpty == true)
            Text(
              citationText.toString(),
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey),
            ),
          const SizedBox(height: 20),

          // Meta grid (mockup: Judgment | Court | Date | Bench | Citation | Category | Related Articles)
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.parchment,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.stone),
            ),
            child: Column(
              children: [
                if (court?.toString().isNotEmpty == true)
                  _MetaRow(label: 'Court', value: court.toString()),
                if (decidedOn != null)
                  _MetaRow(
                    label: 'Decided On',
                    value: decidedOn.toString().split('T').first,
                  ),
                if (judges.isNotEmpty)
                  _MetaRow(label: 'Bench', value: judges.join(', ')),
                if (citationText?.toString().isNotEmpty == true)
                  _MetaRow(label: 'Citation', value: citationText.toString()),
                if (provisions.isNotEmpty)
                  _MetaRow(
                    label: 'Related Provisions',
                    value: provisions.join(', '),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Key Excerpt
          if (passageText?.toString().isNotEmpty == true) ...[
            _SectionTitle('Key Excerpt'),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppColors.charcoal,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Source Passage${location != null ? ' ($location)' : ''}',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.warmGrey,
                        ),
                      ),
                      StatusChip(status: supportState),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    '“$passageText”\n\n— $caseName${citationText != null ? ' $citationText' : ''}',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppColors.ivory,
                      fontStyle: FontStyle.italic,
                      height: 1.7,
                    ),
                  ),
                  if (translated?.toString().isNotEmpty == true) ...[
                    const SizedBox(height: 20),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.espresso,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.g_translate,
                                color: AppColors.antiqueBrass,
                                size: 14,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                'हिन्दी अनुवाद (Hindi Translation)',
                                style: Theme.of(context).textTheme.labelSmall
                                    ?.copyWith(color: AppColors.antiqueBrass),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            translated.toString(),
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: AppColors.ivory, height: 1.7),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],

          // Full Judgment (Summary)
          if (summary?.toString().isNotEmpty == true) ...[
            _SectionTitle('Full Judgment (Summary)'),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppColors.parchment,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.stone),
              ),
              child: Text(
                summary.toString(),
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(height: 1.7),
              ),
            ),
            const SizedBox(height: 24),
          ],

          // Note (lawyer's own)
          if (citation['note']?.toString().isNotEmpty == true) ...[
            _SectionTitle('Your Note'),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.antiqueBrass.withOpacity(0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: AppColors.antiqueBrass.withOpacity(0.3),
                ),
              ),
              child: Text(
                citation['note'].toString(),
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _MetaRow extends StatelessWidget {
  final String label;
  final String value;

  const _MetaRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 170,
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: AppColors.antiqueBrass,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}

// ── Widgets ──────────────────────────────────────────────────────────────────

class _CountChip extends StatelessWidget {
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _CountChip({
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
        decoration: BoxDecoration(
          color: isActive ? AppColors.charcoal : AppColors.parchment,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isActive ? AppColors.charcoal : AppColors.stone,
          ),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: isActive ? AppColors.ivory : AppColors.subtleBronze,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}
