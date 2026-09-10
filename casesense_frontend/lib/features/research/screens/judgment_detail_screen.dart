import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/services.dart';
import 'dart:ui';
import '../../../core/api/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../research/providers/saved_citations_controller.dart';

/// Judgment Detail — immersive dark reading view backed by GET /judgments/{id}.
class JudgmentDetailScreen extends ConsumerStatefulWidget {
  final String? judgmentId;

  const JudgmentDetailScreen({super.key, this.judgmentId});

  @override
  ConsumerState<JudgmentDetailScreen> createState() => _JudgmentDetailScreenState();
}

class _JudgmentDetailScreenState extends ConsumerState<JudgmentDetailScreen> {
  Map<String, dynamic>? _judgment;
  List<Map<String, dynamic>> _paragraphs = [];
  bool _loading = true;
  String? _error;
  int _activeTabIndex = 0;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final id = widget.judgmentId;
    if (id == null || id == '0') {
      setState(() => _loading = false);
      return;
    }
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.get('/judgments/$id');
      final raw = res.data is Map<String, dynamic> ? res.data as Map<String, dynamic> : <String, dynamic>{};
      setState(() {
        _judgment = (raw['judgment'] ?? raw) as Map<String, dynamic>;
        _paragraphs = ((raw['paragraphs'] ?? const []) as List<dynamic>)
            .whereType<Map<String, dynamic>>()
            .toList();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _saveToCollection() async {
    final j = _judgment;
    if (j == null) return;
    final firstPassage = _paragraphs.isNotEmpty ? _paragraphs.first : null;
    final ok = await ref.read(savedCitationsControllerProvider.notifier).saveCitation({
      'case_name': j['case_name'] ?? 'Unknown Case',
      'citation_text': j['citation'],
      'court': j['court'],
      'decided_on': j['decided_on'],
      'judgment_id': j['id'],
      'passage_text': firstPassage?['text'],
      'location_label': firstPassage?['location_label'],
      'support_state': 'VERIFIED',
      'citation_type': 'judgment',
    });
    if (!mounted) return;
    setState(() => _saved = ok);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? 'Saved to your citations.' : 'Could not save — try again.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.nearBlack,
      body: Stack(
        children: [
          // 1. Immersive Architectural Background
          Positioned(
            top: 0,
            right: 0,
            bottom: 0,
            width: MediaQuery.of(context).size.width * 0.6,
            child: Image.asset(
              'assets/images/court_bg.jpg',
              fit: BoxFit.cover,
              alignment: Alignment.centerRight,
              color: AppColors.nearBlack.withOpacity(0.4),
              colorBlendMode: BlendMode.srcATop,
              errorBuilder: (_, __, ___) => Container(color: AppColors.espresso),
            ),
          ),

          // 2. Heavy Gradient
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [
                    AppColors.nearBlack,
                    AppColors.nearBlack.withOpacity(0.9),
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.4, 1.0],
                ),
              ),
            ),
          ),

          // 3. Main Content
          Column(
            children: [
              _buildTopBar(context),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
                    : _error != null
                        ? Center(
                            child: Text('Could not load judgment.\n$_error',
                              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey),
                              textAlign: TextAlign.center))
                        : SingleChildScrollView(
                            padding: const EdgeInsets.symmetric(horizontal: 64.0, vertical: 24.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Hero Typography
                                Text(
                                  _caseName,
                                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                                    color: AppColors.ivory,
                                    fontSize: 44,
                                    height: 1.1,
                                  ),
                                ),
                                const SizedBox(height: 16),
                                Row(
                                  children: [
                                    Text((_judgment?['court'] ?? '—').toString().toUpperCase(),
                                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.warmGrey, letterSpacing: 1.5)),
                                    const SizedBox(width: 16),
                                    const Text('•', style: TextStyle(color: AppColors.subtleBronze)),
                                    const SizedBox(width: 16),
                                    Text((_judgment?['decided_on'] ?? '—').toString().split('T').first,
                                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.warmGrey)),
                                    const SizedBox(width: 16),
                                    const Text('•', style: TextStyle(color: AppColors.subtleBronze)),
                                    const SizedBox(width: 16),
                                    Text((_judgment?['citation'] ?? '—').toString(),
                                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.warmGrey)),
                                  ],
                                ),
                                const SizedBox(height: 48),

                                // Tabs
                                Row(
                                  children: [
                                    _buildTab(0, 'Overview'),
                                    const SizedBox(width: 32),
                                    _buildTab(1, 'Judgment'),
                                    const SizedBox(width: 32),
                                    _buildTab(2, 'Citations'),
                                  ],
                                ),

                                Container(
                                  height: 1,
                                  width: double.infinity,
                                  color: AppColors.charcoal,
                                  margin: const EdgeInsets.only(bottom: 48),
                                ),

                                _buildTabContent(context),
                              ],
                            ),
                          ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String get _caseName {
    final name = _judgment?['case_name']?.toString() ?? 'Judgment';
    // Break long case names onto two lines like the mockup.
    final idx = name.indexOf(' v. ');
    if (idx > 0 && name.length < 80) {
      return '${name.substring(0, idx + 3)}\n${name.substring(idx + 4)}';
    }
    return name;
  }

  Widget _buildTopBar(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          InkWell(
            onTap: () => context.pop(),
            borderRadius: BorderRadius.circular(20),
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  const Icon(Icons.arrow_back, color: AppColors.ivory, size: 18),
                  const SizedBox(width: 8),
                  Text('Case View', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
                ],
              ),
            ),
          ),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: _saved ? null : _saveToCollection,
                icon: Icon(_saved ? Icons.bookmark : Icons.bookmark_border, color: AppColors.ivory, size: 16),
                label: Text(_saved ? 'Saved ✓' : 'Save',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.ivory)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.charcoal),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(40)),
                ),
              ),
              const SizedBox(width: 16),
              IconButton(
                onPressed: () {
                  final j = _judgment;
                  if (j == null) return;
                  Clipboard.setData(ClipboardData(
                    text: '${j['case_name']}\n${j['citation'] ?? ''}',
                  ));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Citation copied to clipboard.')),
                  );
                },
                icon: const Icon(Icons.share_outlined, color: AppColors.ivory),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTab(int index, String label) {
    final isActive = _activeTabIndex == index;
    return GestureDetector(
      onTap: () => setState(() => _activeTabIndex = index),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: isActive ? AppColors.ivory : AppColors.warmGrey,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            height: 2,
            width: 40,
            color: isActive ? AppColors.ivory : Colors.transparent,
          ),
        ],
      ),
    );
  }

  Widget _buildTabContent(BuildContext context) {
    switch (_activeTabIndex) {
      case 0:
        return _buildOverview(context);
      case 1:
        return _buildJudgmentText(context);
      default:
        return _buildCitations(context);
    }
  }

  Widget _buildOverview(BuildContext context) {
    final sourceUrl = _judgment?['source_url']?.toString();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 5,
          child: Column(
            children: [
              _FactItem(
                icon: Icons.gavel,
                title: 'Court',
                description: (_judgment?['court'] ?? '—').toString(),
              ),
              const SizedBox(height: 40),
              _FactItem(
                icon: Icons.event,
                title: 'Decided On',
                description: (_judgment?['decided_on'] ?? '—').toString().split('T').first,
              ),
              const SizedBox(height: 40),
              _FactItem(
                icon: Icons.people,
                title: 'Bench',
                description: ((_judgment?['judges'] as List<dynamic>?) ?? const []).join(', ').isEmpty
                    ? '—'
                    : ((_judgment?['judges'] as List<dynamic>?) ?? const []).join(', '),
              ),
            ],
          ),
        ),
        const SizedBox(width: 64),
        Expanded(
          flex: 4,
          child: _buildKeyPassageCard(context, sourceUrl),
        ),
      ],
    );
  }

  Widget _buildKeyPassageCard(BuildContext context, String? sourceUrl) {
    final firstPassage = _paragraphs.isNotEmpty ? _paragraphs.first : null;
    final passageText = firstPassage?['text']?.toString() ??
        'Passages will appear here once the judgment text has been analyzed.';
    final location = firstPassage?['location_label']?.toString();

    return Tactile3DCard(
      depth: 0.05,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
          child: Container(
            padding: const EdgeInsets.all(40),
            decoration: BoxDecoration(
              color: AppColors.charcoal.withOpacity(0.6),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.stone.withOpacity(0.15)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.antiqueBrass.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text('Key Passage${location != null ? ' • $location' : ''}',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.antiqueBrass)),
                ),
                const SizedBox(height: 24),
                Text(
                  '“$passageText”',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: AppColors.ivory,
                    height: 1.5,
                    fontStyle: FontStyle.italic,
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(width: 20, height: 1, color: AppColors.subtleBronze, margin: const EdgeInsets.only(top: 10)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${_judgment?['case_name'] ?? ''}\n${_judgment?['citation'] ?? ''}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 40),
                if (sourceUrl?.isNotEmpty == true)
                  PrimaryButton(
                    label: 'View Full Judgment',
                    onPressed: () {
                      // External source link — handled by the deployment's web view.
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Source: $sourceUrl')),
                      );
                    },
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildJudgmentText(BuildContext context) {
    if (_paragraphs.isEmpty) {
      return Text(
        'Full judgment text has not been analyzed yet for this judgment.',
        style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final p in _paragraphs)
          Padding(
            padding: const EdgeInsets.only(bottom: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (p['location_label'] != null)
                  Text(p['location_label'].toString(),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.antiqueBrass)),
                const SizedBox(height: 6),
                Text(
                  p['text']?.toString() ?? '',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.ivory.withOpacity(0.85), height: 1.8),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildCitations(BuildContext context) {
    return Text(
      'Citations referencing this judgment will appear here as your research runs link them.',
      style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey),
    );
  }
}

class _FactItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;

  const _FactItem({required this.icon, required this.title, required this.description});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.espresso,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.charcoal),
          ),
          child: Icon(icon, color: AppColors.ivory, size: 20),
        ),
        const SizedBox(width: 20),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
              const SizedBox(height: 8),
              Text(description, style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey, height: 1.6)),
            ],
          ),
        ),
      ],
    );
  }
}
