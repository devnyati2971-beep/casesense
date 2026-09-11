import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../../shared/widgets/status_chip.dart';
import '../../auth/providers/auth_controller.dart';
import '../providers/research_controller.dart';
import '../providers/saved_citations_controller.dart';
import '../../authorities/providers/authorities_controller.dart';

class ResearchResultsScreen extends ConsumerStatefulWidget {
  final String sessionId;
  const ResearchResultsScreen({super.key, required this.sessionId});

  @override
  ConsumerState<ResearchResultsScreen> createState() =>
      _ResearchResultsScreenState();
}

class _ResearchResultsScreenState extends ConsumerState<ResearchResultsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(researchControllerProvider.notifier)
          .loadSession(widget.sessionId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final researchState = ref.watch(researchControllerProvider);
    final results = researchState.results;

    final groups = (results?['groups'] as List<dynamic>?) ?? [];

    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AppSidebar(currentRoute: '/finder'),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(
                horizontal: 64.0,
                vertical: 48.0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Research Results',
                            style: Theme.of(context).textTheme.displayMedium,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            groups.isEmpty
                                ? 'Session ${widget.sessionId}'
                                : '${groups.length} legal ${groups.length == 1 ? 'issue' : 'issues'} • ${_countJudgments(groups)} Authorities Found',
                            style: Theme.of(context).textTheme.bodyLarge
                                ?.copyWith(color: AppColors.subtleBronze),
                          ),
                        ],
                      ),
                      if (groups.isNotEmpty)
                        PrimaryButton(
                          label: 'Export Summary',
                          icon: Icons.download,
                          onPressed: () => _exportSummary(context, groups),
                        ),
                    ],
                  ),
                  const SizedBox(height: 48),

                  if (researchState.isLoading)
                    const Center(
                      child: CircularProgressIndicator(
                        color: AppColors.antiqueBrass,
                      ),
                    )
                  else if (groups.isEmpty)
                    _EmptyResults(sessionId: widget.sessionId)
                  else
                    for (final group in groups) ...[
                      Text(
                        'ISSUE: ${group['issue'] ?? 'Untitled Issue'}',
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(
                              color: AppColors.antiqueBrass,
                              letterSpacing: 1.2,
                            ),
                      ),
                      const SizedBox(height: 24),
                      for (final judgment
                          in (group['judgments'] as List<dynamic>? ?? []))
                        Padding(
                          padding: const EdgeInsets.only(bottom: 24),
                          child: _ResultCardWithActions(
                            judgmentData: judgment,
                            sessionId: widget.sessionId,
                          ),
                        ),
                      const SizedBox(height: 24),
                    ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  int _countJudgments(List<dynamic> groups) {
    var count = 0;
    for (final g in groups) {
      count += (g['judgments'] as List<dynamic>?)?.length ?? 0;
    }
    return count;
  }

  Future<void> _exportSummary(
    BuildContext context,
    List<dynamic> groups,
  ) async {
    final summary = StringBuffer('CaseSense Research Summary\n\n');
    for (final group in groups) {
      summary.writeln('ISSUE: ${group['issue'] ?? 'Untitled Issue'}');
      for (final item in (group['judgments'] as List<dynamic>? ?? const [])) {
        final judgment = item is Map<String, dynamic>
            ? (item['judgment'] as Map<String, dynamic>? ??
                  const <String, dynamic>{})
            : const <String, dynamic>{};
        final propositions = item is Map<String, dynamic>
            ? (item['propositions'] as List<dynamic>? ?? const [])
            : const [];
        final proposition =
            propositions.isNotEmpty &&
                propositions.first is Map<String, dynamic>
            ? propositions.first as Map<String, dynamic>
            : const <String, dynamic>{};
        final passages = proposition['passages'] as List<dynamic>? ?? const [];
        final passage =
            passages.isNotEmpty && passages.first is Map<String, dynamic>
            ? passages.first as Map<String, dynamic>
            : const <String, dynamic>{};
        summary.writeln('\n${judgment['case_name'] ?? 'Untitled Judgment'}');
        if (judgment['citation']?.toString().isNotEmpty == true) {
          summary.writeln(judgment['citation']);
        }
        summary.writeln('Court: ${judgment['court'] ?? '—'}');
        summary.writeln('Proposition: ${proposition['text'] ?? '—'}');
        summary.writeln('Source passage: ${passage['text'] ?? '—'}');
      }
      summary.writeln('\n${'=' * 72}\n');
    }
    final bytes = Uint8List.fromList(utf8.encode(summary.toString()));
    try {
      final result = await FilePicker.platform.saveFile(
        dialogTitle: 'Export research summary',
        fileName: 'casesense-research-summary.txt',
        type: FileType.custom,
        allowedExtensions: const ['txt'],
        bytes: bytes,
      );
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result == null ? 'Export cancelled.' : 'Research summary exported.',
          ),
        ),
      );
    } catch (_) {
      // Clipboard is a dependable fallback where a platform does not expose a
      // save dialog (for example, restricted browser embeds).
      await Clipboard.setData(ClipboardData(text: summary.toString()));
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Export file is unavailable here; the summary was copied to your clipboard.',
          ),
        ),
      );
    }
  }
}

// ── Result card with v2.2 actions (Save / Translate / Share / Select) ────────

class _ResultCardWithActions extends ConsumerStatefulWidget {
  final dynamic judgmentData;
  final String sessionId;

  const _ResultCardWithActions({
    required this.judgmentData,
    required this.sessionId,
  });
  @override
  ConsumerState<_ResultCardWithActions> createState() =>
      _ResultCardWithActionsState();
}

class _ResultCardWithActionsState
    extends ConsumerState<_ResultCardWithActions> {
  bool _saving = false;
  bool _saved = false;
  String? _translated;
  bool _translating = false;

  bool get _isAuthed =>
      ref.read(authControllerProvider).value?.isAuthenticated ?? false;

  /// v2.2 guest tier: saving/translating/selecting require an account.
  /// Returns true when the caller may proceed.
  bool _requireAuth() {
    if (_isAuthed) return true;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Create a free account to save citations and translate.'),
        duration: Duration(seconds: 3),
      ),
    );
    context.push('/login?from=/research/${widget.sessionId}/results');
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final Map<String, dynamic> judgment =
        widget.judgmentData is Map<String, dynamic>
        ? widget.judgmentData
        : <String, dynamic>{};
    final j =
        (judgment['judgment'] as Map<String, dynamic>?) ?? <String, dynamic>{};
    final caseName = j['case_name'] ?? 'Unknown Case';
    final citation = j['citation'];
    final court = j['court'] ?? 'Unknown Court';
    final sourceUrl = j['source_url'];

    final propositions = (judgment['propositions'] as List<dynamic>?) ?? [];
    final proposition =
        propositions.isNotEmpty && propositions.first is Map<String, dynamic>
        ? propositions.first as Map<String, dynamic>
        : <String, dynamic>{};
    final propText = proposition['text'] ?? '';
    final relevance = proposition['relevance_label'] ?? 'RELEVANT';
    final explanation = proposition['relevance_explanation'];
    final propositionId = proposition['id']?.toString();

    final passages = (proposition['passages'] as List<dynamic>?) ?? [];
    final passage =
        passages.isNotEmpty && passages.first is Map<String, dynamic>
        ? passages.first as Map<String, dynamic>
        : <String, dynamic>{};
    final passageText = passage['text'] ?? '';
    final location = passage['location_label'];
    final supportState = passage['support_state'] ?? 'VERIFIED';

    return Tactile3DCard(
      depth: 0.015,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.parchment,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.stone),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: Judgment Info
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              court,
                              style: Theme.of(context).textTheme.labelSmall,
                            ),
                            const SizedBox(width: 12),
                            Text(
                              '•',
                              style: TextStyle(color: AppColors.subtleBronze),
                            ),
                            const SizedBox(width: 12),
                            Text(
                              relevance,
                              style: Theme.of(context).textTheme.labelSmall
                                  ?.copyWith(color: AppColors.antiqueBrass),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          caseName,
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        if (citation?.toString().isNotEmpty == true) ...[
                          const SizedBox(height: 4),
                          Text(
                            citation.toString(),
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(color: AppColors.warmGrey),
                          ),
                        ],
                        if (explanation?.toString().isNotEmpty == true) ...[
                          const SizedBox(height: 8),
                          Text(
                            explanation.toString(),
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(
                                  color: AppColors.subtleBronze,
                                  fontStyle: FontStyle.italic,
                                ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (sourceUrl?.toString().isNotEmpty == true)
                    PrimaryButton(
                      label: 'Read Judgment',
                      onPressed: () =>
                          context.push('/judgment/${j['id'] ?? '0'}'),
                    ),
                ],
              ),
            ),
            const Divider(height: 1),
            // Body: Proposition and Passage
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'AI Proposition',
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          propText,
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 48),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(16),
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
                                style: Theme.of(context).textTheme.labelSmall
                                    ?.copyWith(color: AppColors.warmGrey),
                              ),
                              StatusChip(status: supportState),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            '“$passageText”',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(
                                  color: AppColors.ivory,
                                  fontStyle: FontStyle.italic,
                                ),
                          ),
                          if (_translated != null) ...[
                            const SizedBox(height: 14),
                            Container(
                              padding: const EdgeInsets.all(12),
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
                                        size: 13,
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        'हिन्दी अनुवाद',
                                        style: Theme.of(context)
                                            .textTheme
                                            .labelSmall
                                            ?.copyWith(
                                              color: AppColors.antiqueBrass,
                                            ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    _translated!,
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(color: AppColors.ivory),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Action bar (mockup 2: Save Citation → Translate to Hindi → Share)
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              child: Row(
                children: [
                  // Save Citation (authed only — guests get the sign-in CTA)
                  OutlinedButton.icon(
                    onPressed: _saved || _saving
                        ? null
                        : () {
                            if (_requireAuth())
                              _saveCitation(j, passage, propText);
                          },
                    icon: Icon(
                      _saved ? Icons.bookmark : Icons.bookmark_border,
                      size: 16,
                    ),
                    label: Text(_saved ? 'Saved ✓' : 'Save Citation'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: _saved
                          ? AppColors.success
                          : AppColors.charcoal,
                      side: BorderSide(
                        color: _saved ? AppColors.success : AppColors.stone,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Translate to Hindi (authed only — AI quota is per user)
                  OutlinedButton.icon(
                    onPressed: _translating
                        ? null
                        : () {
                            if (_requireAuth()) _translatePassage(passageText);
                          },
                    icon: _translating
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.g_translate, size: 16),
                    label: Text(
                      _translated == null
                          ? 'Translate to Hindi'
                          : 'Bilingual View ✓',
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.charcoal,
                      side: const BorderSide(color: AppColors.stone),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Share
                  OutlinedButton.icon(
                    onPressed: () => _shareCitation(
                      '$caseName\n${citation ?? ''}\n\n“$passageText” ${location ?? ''}'
                          .trim(),
                    ),
                    icon: const Icon(Icons.share_outlined, size: 16),
                    label: const Text('Share'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.charcoal,
                      side: const BorderSide(color: AppColors.stone),
                    ),
                  ),
                  const Spacer(),
                  // Select as Authority (existing research flow, authed only)
                  if (propositionId != null)
                    TextButton.icon(
                      onPressed: () {
                        if (_requireAuth()) _selectAuthority(propositionId, j);
                      },
                      icon: const Icon(Icons.check_circle_outline, size: 16),
                      label: const Text('Select as Authority'),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _saveCitation(
    Map<String, dynamic> judgment,
    Map<String, dynamic> passage,
    String propText,
  ) async {
    setState(() => _saving = true);
    final ok = await ref
        .read(savedCitationsControllerProvider.notifier)
        .saveCitation({
          'case_name': judgment['case_name'] ?? 'Unknown Case',
          'citation_text': judgment['citation'],
          'court': judgment['court'],
          'decided_on': judgment['decided_on'],
          'judgment_id': judgment['id'],
          'passage_text': passage['text'],
          'location_label': passage['location_label'],
          'support_state': passage['support_state'] ?? 'VERIFIED',
          'proposition_text': propText,
          'citation_type': 'judgment',
        });
    if (!mounted) return;
    setState(() {
      _saving = false;
      _saved = ok;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok
              ? 'Citation saved to your collection.'
              : 'Could not save citation.',
        ),
      ),
    );
  }

  Future<void> _translatePassage(String passageText) async {
    if (passageText.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('There is no source passage available to translate.'),
        ),
      );
      return;
    }
    setState(() => _translating = true);
    try {
      final dio = ref.read(dioProvider);
      final res = await dio.post(
        '/translate',
        data: {'text': passageText, 'target_language': 'hi'},
      );
      final raw = res.data is Map<String, dynamic>
          ? res.data as Map<String, dynamic>
          : <String, dynamic>{};
      final translated = raw['translated_text']?.toString();
      if (translated == null || translated.isEmpty) {
        throw StateError('No translation returned');
      }
      if (mounted) {
        setState(() {
          _translated = translated;
          _translating = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Hindi translation added. The card now shows both languages.',
            ),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _translating = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Could not translate this passage right now. Please try again.',
            ),
          ),
        );
      }
    }
  }

  Future<void> _shareCitation(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Citation copied to your clipboard — ready to paste into email, WhatsApp, or a brief.',
        ),
      ),
    );
  }

  Future<void> _selectAuthority(
    String propositionId,
    Map<String, dynamic> judgment,
  ) async {
    final ok = await ref
        .read(authoritiesControllerProvider.notifier)
        .selectAuthority(
          widget.sessionId,
          propositionId,
          judgment['id']?.toString() ?? '',
          judgment,
        );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          ok
              ? 'Authority selected for this session.'
              : 'Failed to select authority.',
        ),
      ),
    );
  }
}

class _EmptyResults extends StatelessWidget {
  final String sessionId;
  const _EmptyResults({required this.sessionId});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 80),
      child: Column(
        children: [
          const Icon(Icons.travel_explore, size: 64, color: AppColors.stone),
          const SizedBox(height: 16),
          Text(
            'No results yet',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Results for session $sessionId will appear here once the research run completes.',
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
