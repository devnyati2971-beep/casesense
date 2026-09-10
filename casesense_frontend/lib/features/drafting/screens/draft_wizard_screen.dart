import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/ghost_button.dart';
import '../../matters/providers/matters_list_controller.dart';
import '../../research/providers/saved_citations_controller.dart';
import '../providers/drafts_controller.dart';

class DraftWizardScreen extends ConsumerStatefulWidget {
  const DraftWizardScreen({super.key});

  @override
  ConsumerState<DraftWizardScreen> createState() => _DraftWizardScreenState();
}

class _DraftWizardScreenState extends ConsumerState<DraftWizardScreen> {
  int _step = 0;
  String? _selectedMatterId;
  String? _selectedType;
  final _caseInfoController = TextEditingController();
  final _queryController = TextEditingController();
  bool _useExistingResearch = false;
  bool _useSavedCitations = false;
  final List<String> _uploadedFiles = [];

  static const List<Map<String, String>> _documentTypes = [
    {'id': 'BAIL_APPLICATION', 'name': 'Bail Application', 'desc': 'Applications under Section 439 CrPC / BNSS'},
    {'id': 'WRIT_PETITION', 'name': 'Writ Petition', 'desc': 'Article 226 / Article 32 petitions'},
    {'id': 'LEGAL_NOTICE', 'name': 'Legal Notice', 'desc': 'Pre-litigation notices'},
    {'id': 'COUNTER_AFFIDAVIT', 'name': 'Counter Affidavit', 'desc': 'Reply affidavits'},
    {'id': 'CIVIL_SUIT', 'name': 'Civil Suit Plaint', 'desc': 'Institution of civil suits'},
    {'id': 'SLP', 'name': 'SLP', 'desc': 'Special Leave Petition under Article 136'},
    {'id': 'OTHER', 'name': 'Other Document', 'desc': 'Any other legal document'},
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(mattersListControllerProvider.notifier).load();
      ref.read(savedCitationsControllerProvider.notifier).load();
    });
  }

  @override
  void dispose() {
    _caseInfoController.dispose();
    _queryController.dispose();
    super.dispose();
  }

  void _next() => setState(() => _step = (_step + 1).clamp(0, 3));
  void _back() => setState(() => _step = (_step - 1).clamp(0, 3));

  Future<void> _createAndGenerate() async {
    final matterId = _selectedMatterId;
    final docType = _selectedType;
    if (matterId == null || docType == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select a matter and a document type first.')),
      );
      return;
    }

    final draftId = await ref.read(draftsControllerProvider.notifier).createDraft(
      matterId,
      docType,
      title: _caseInfoController.text.trim().isNotEmpty
          ? _caseInfoController.text.trim()
          : null,
    );
    if (draftId == null || !mounted) return;

    // Kick off generation right away (blueprint §22.5 / §D23).
    await ref.read(draftsControllerProvider.notifier).generateDraft(draftId);
    if (!mounted) return;

    context.pushReplacement('/drafts/$draftId');
  }

  @override
  Widget build(BuildContext context) {
    final mattersState = ref.watch(mattersListControllerProvider);
    final savedState = ref.watch(savedCitationsControllerProvider);
    final draftsState = ref.watch(draftsControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.nearBlack,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/drafts_list'),
          Expanded(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 900),
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(vertical: 48),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Drafting', style: Theme.of(context).textTheme.displayMedium?.copyWith(color: AppColors.ivory)),
                      const SizedBox(height: 8),
                      Text('Create AI-assisted legal drafts in four guided steps.',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.stone)),
                      const SizedBox(height: 32),

                      // Step indicator
                      Row(
                        children: [
                          for (var i = 0; i < 4; i++) ...[
                            _StepIndicator(
                              index: i + 1,
                              label: _stepLabels[i],
                              isActive: _step == i,
                              isDone: _step > i,
                              onTap: () => setState(() => _step = i),
                            ),
                            if (i < 3) Expanded(child: Container(height: 1, color: AppColors.stone.withOpacity(0.3))),
                          ],
                        ],
                      ),
                      const SizedBox(height: 40),

                      _buildStep(mattersState, savedState, draftsState),

                      const SizedBox(height: 48),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          if (_step > 0) GhostButton(label: 'Back', onPressed: _back) else const SizedBox.shrink(),
                          if (_step < 3)
                            PrimaryButton(label: 'Continue', onPressed: _next)
                          else
                            draftsState.isLoading
                                ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
                                : PrimaryButton(label: 'Create Draft & Generate', onPressed: _createAndGenerate),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  static const List<String> _stepLabels = [
    'Choose Document Type',
    'Case Information',
    'Case Query / Instructions',
    'Upload Supporting Documents',
  ];

  Widget _buildStep(
    MattersListState mattersState,
    SavedCitationsState savedState,
    DraftsState draftsState,
  ) {
    switch (_step) {
      case 0:
        return _stepChooseType();
      case 1:
        return _stepCaseInfo(mattersState);
      case 2:
        return _stepQuery(savedState);
      case 3:
        return _stepUpload(savedState);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _stepChooseType() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('1. Choose Document Type', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: AppColors.ivory)),
        const SizedBox(height: 8),
        Text('What document do you need CaseSense to help draft?',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.stone)),
        const SizedBox(height: 24),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            mainAxisSpacing: 16,
            crossAxisSpacing: 16,
            childAspectRatio: 2.4,
          ),
          itemCount: _documentTypes.length,
          itemBuilder: (context, index) {
            final type = _documentTypes[index];
            final selected = _selectedType == type['id'];
            return InkWell(
              onTap: () => setState(() => _selectedType = type['id']),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: selected ? AppColors.antiqueBrass.withOpacity(0.15) : AppColors.charcoal,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: selected ? AppColors.antiqueBrass : AppColors.stone.withOpacity(0.2), width: selected ? 2 : 1),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      children: [
                        Icon(
                          selected ? Icons.check_circle : Icons.description,
                          color: selected ? AppColors.antiqueBrass : AppColors.stone,
                          size: 18,
                        ),
                        const SizedBox(width: 8),
                        Expanded(child: Text(type['name']!, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 14, color: AppColors.ivory), overflow: TextOverflow.ellipsis)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(type['desc']!, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.stone, fontSize: 11), overflow: TextOverflow.ellipsis),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _stepCaseInfo(MattersListState mattersState) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('2. Case Information', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: AppColors.ivory)),
        const SizedBox(height: 8),
        Text('Which matter is this draft for? You can also provide party names.',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.stone)),
        const SizedBox(height: 24),
        if (mattersState.matters.isEmpty)
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.charcoal,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.stone.withOpacity(0.2)),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline, color: AppColors.ivory),
                const SizedBox(width: 12),
                Expanded(child: Text('No matters yet. Create one in History first.', style: TextStyle(color: AppColors.ivory))),
                TextButton(
                  onPressed: () => context.push('/history'),
                  child: const Text('Go to History', style: TextStyle(color: AppColors.antiqueBrass)),
                ),
              ],
            ),
          )
        else
          Theme(
            data: Theme.of(context).copyWith(
              canvasColor: AppColors.charcoal,
            ),
            child: DropdownButtonFormField<String>(
              initialValue: _selectedMatterId,
              style: const TextStyle(color: AppColors.ivory),
              decoration: InputDecoration(
                labelText: 'Select Matter',
                labelStyle: const TextStyle(color: AppColors.stone),
                enabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: AppColors.stone)),
                focusedBorder: const OutlineInputBorder(borderSide: BorderSide(color: AppColors.antiqueBrass)),
              ),
              items: [
                for (final m in mattersState.matters)
                  DropdownMenuItem(
                    value: m['id']?.toString(),
                    child: Text(m['title'] ?? 'Untitled', overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) => setState(() => _selectedMatterId = v),
            ),
          ),
        const SizedBox(height: 20),
        TextField(
          controller: _caseInfoController,
          maxLines: 2,
          style: const TextStyle(color: AppColors.ivory),
          decoration: InputDecoration(
            labelText: 'Title / Case Information (optional)',
            hintText: 'E.g., Bail Application for Ramesh Kumar, FIR No. 128/2025, PS Civil Lines',
            labelStyle: const TextStyle(color: AppColors.stone),
            hintStyle: const TextStyle(color: AppColors.stone),
            enabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: AppColors.stone)),
            focusedBorder: const OutlineInputBorder(borderSide: BorderSide(color: AppColors.antiqueBrass)),
          ),
        ),
      ],
    );
  }

  Widget _stepQuery(SavedCitationsState savedState) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('3. Add Your Case Query / Instructions', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: AppColors.ivory)),
        const SizedBox(height: 8),
        Text('Tell the AI what to emphasise, include, or avoid in this draft.',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.stone)),
        const SizedBox(height: 24),
        TextField(
          controller: _queryController,
          maxLines: 6,
          style: const TextStyle(color: AppColors.ivory),
          decoration: InputDecoration(
            hintText: 'E.g., Prepare a bail application focusing on prolonged incarceration (3+ years) and delay in trial conclusion. Cite Article 21 jurisprudence and the Najeeb principles.',
            hintStyle: const TextStyle(color: AppColors.stone),
            enabledBorder: const OutlineInputBorder(borderSide: BorderSide(color: AppColors.stone)),
            focusedBorder: const OutlineInputBorder(borderSide: BorderSide(color: AppColors.antiqueBrass)),
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 20),
        Theme(
          data: Theme.of(context).copyWith(
            unselectedWidgetColor: AppColors.stone,
          ),
          child: CheckboxListTile(
            value: _useExistingResearch,
            onChanged: (v) => setState(() => _useExistingResearch = v ?? false),
            title: const Text('Use Existing Research', style: TextStyle(color: AppColors.ivory)),
            subtitle: const Text('Include authorities from prior research sessions', style: TextStyle(color: AppColors.stone)),
            controlAffinity: ListTileControlAffinity.leading,
            activeColor: AppColors.antiqueBrass,
            checkColor: AppColors.nearBlack,
          ),
        ),
      ],
    );
  }

  Widget _stepUpload(SavedCitationsState savedState) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('4. Upload Supporting Documents', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: AppColors.ivory)),
        const SizedBox(height: 8),
        Text('Attach case files (FIR, orders, pleadings) that inform this draft.',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.stone)),
        const SizedBox(height: 24),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: AppColors.charcoal,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.stone.withOpacity(0.2), style: BorderStyle.solid, width: 1),
          ),
          child: Column(
            children: [
              const Icon(Icons.upload_file, size: 40, color: AppColors.ivory),
              const SizedBox(height: 12),
              const Text('Drag & drop files here, or click to browse', style: TextStyle(color: AppColors.ivory)),
              const SizedBox(height: 4),
              Text('PDF, DOCX up to 25 MB (upload via the matter workspace)',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.stone, fontSize: 12)),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => context.push('/history'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.ivory,
                  side: const BorderSide(color: AppColors.stone),
                ),
                child: const Text('Open Matter Workspace to Upload'),
              ),
            ],
          ),
        ),
        if (_uploadedFiles.isNotEmpty) ...[
          const SizedBox(height: 16),
          for (final f in _uploadedFiles)
            ListTile(leading: const Icon(Icons.description, color: AppColors.ivory), title: Text(f, style: const TextStyle(color: AppColors.ivory))),
        ],
        const SizedBox(height: 20),
        Theme(
          data: Theme.of(context).copyWith(
            unselectedWidgetColor: AppColors.stone,
          ),
          child: CheckboxListTile(
            value: _useSavedCitations,
            onChanged: (v) => setState(() => _useSavedCitations = v ?? false),
            title: Text('Use Saved Citations (${savedState.citations.length})', style: const TextStyle(color: AppColors.ivory)),
            subtitle: const Text('Weave your saved authorities into this draft', style: TextStyle(color: AppColors.stone)),
            controlAffinity: ListTileControlAffinity.leading,
            activeColor: AppColors.antiqueBrass,
            checkColor: AppColors.nearBlack,
          ),
        ),
      ],
    );
  }
}

class _StepIndicator extends StatelessWidget {
  final int index;
  final String label;
  final bool isActive;
  final bool isDone;
  final VoidCallback onTap;

  const _StepIndicator({
    required this.index,
    required this.label,
    required this.isActive,
    required this.isDone,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = isDone ? AppColors.success : isActive ? AppColors.antiqueBrass : AppColors.stone.withOpacity(0.5);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: isActive || isDone ? color : Colors.transparent, 
                shape: BoxShape.circle,
                border: Border.all(color: color, width: isActive || isDone ? 0 : 2)
              ),
              child: Center(
                child: isDone
                    ? const Icon(Icons.check, color: AppColors.nearBlack, size: 16)
                    : Text('$index', style: TextStyle(color: isActive ? AppColors.nearBlack : AppColors.stone, fontWeight: FontWeight.bold, fontSize: 13)),
              ),
            ),
            const SizedBox(width: 10),
            Text(
              label,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontSize: 12,
                color: isActive ? AppColors.ivory : AppColors.stone,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
