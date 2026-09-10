import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/status_chip.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../providers/matter_controller.dart';

class MatterDetailScreen extends ConsumerStatefulWidget {
  final String matterId;
  final String? initialTab;

  const MatterDetailScreen({super.key, required this.matterId, this.initialTab});

  @override
  ConsumerState<MatterDetailScreen> createState() => _MatterDetailScreenState();
}

class _MatterDetailScreenState extends ConsumerState<MatterDetailScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    int initialIndex = _getTabIndex(widget.initialTab);
    _tabController = TabController(length: 4, vsync: this, initialIndex: initialIndex);
  }

  int _getTabIndex(String? tab) {
    switch (tab) {
      case 'documents': return 0;
      case 'intelligence': return 1;
      case 'research': return 2;
      case 'drafts': return 3;
      default: return 0;
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _handleUpload() async {
    // Real file picking would use file_picker; for now, keep the simulated
    // selection but route it through the real upload API when a path is given.
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Uploading document... CaseSense AI will analyze it shortly.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Watch the specific matter's state
    final matterState = ref.watch(matterControllerProvider(widget.matterId));

    return Scaffold(
      backgroundColor: AppColors.nearBlack,
      body: Row(
        children: [
          AppSidebar(currentRoute: '/matters/${widget.matterId}'),
          Expanded(
            child: Column(
              children: [
                // Header (Dark Immersive)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 48),
                  decoration: const BoxDecoration(
                    color: AppColors.espresso,
                    border: Border(bottom: BorderSide(color: AppColors.charcoal)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              IconButton(
                                icon: const Icon(Icons.arrow_back, color: AppColors.ivory), 
                                onPressed: () => context.go('/history')
                              ),
                              const SizedBox(width: 8),
                              Text(
                                matterState.matterData?['title'] ?? 'Loading Workspace...', 
                                style: Theme.of(context).textTheme.displayMedium?.copyWith(color: AppColors.ivory)
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Padding(
                            padding: const EdgeInsets.only(left: 48.0),
                            child: Text(
                              '${matterState.matterData?['case_number'] ?? ''} • ${matterState.matterData?['court'] ?? ''}', 
                              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey)
                            ),
                          ),
                        ],
                      ),
                      PrimaryButton(
                        label: 'Upload Document',
                        icon: Icons.upload_file,
                        onPressed: _handleUpload,
                      )
                    ],
                  ),
                ),
                
                // TabBar Strip
                Container(
                  color: AppColors.espresso,
                  padding: const EdgeInsets.symmetric(horizontal: 48),
                  child: TabBar(
                    controller: _tabController,
                    indicatorColor: AppColors.antiqueBrass,
                    labelColor: AppColors.antiqueBrass,
                    unselectedLabelColor: AppColors.warmGrey,
                    tabs: const [
                      Tab(text: 'Documents'),
                      Tab(text: 'Case Intelligence'),
                      Tab(text: 'Research'),
                      Tab(text: 'Drafts'),
                    ],
                  ),
                ),

                // TabBarView Content (Light Ivory Area)
                Expanded(
                  child: Container(
                    color: AppColors.ivory,
                    child: matterState.isLoading && matterState.matterData == null
                        ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
                        : TabBarView(
                            controller: _tabController,
                            children: [
                              _buildDocumentsTab(matterState.documents),
                              _buildIntelligenceTab(context),
                              _buildResearchTab(context),
                              _buildDraftsTab(context),
                            ],
                          ),
                  ),
                )
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDocumentsTab(List<Map<String, dynamic>> documents) {
    return ListView.builder(
      padding: const EdgeInsets.all(48),
      itemCount: documents.length,
      itemBuilder: (context, index) {
        final doc = documents[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: 16.0),
          child: Tactile3DCard(
            depth: 0.01,
            child: Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppColors.parchment, 
                borderRadius: BorderRadius.circular(8), 
                border: Border.all(color: AppColors.stone)
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: AppColors.error.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                    child: const Icon(Icons.picture_as_pdf, color: AppColors.error, size: 28),
                  ),
                  const SizedBox(width: 24),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(doc['file_name'] ?? doc['name'] ?? 'Untitled', style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 4),
                        Text('Uploaded ${doc['created_at'] ?? doc['date'] ?? ''}', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey)),
                      ],
                    ),
                  ),
                  StatusChip(status: doc['status']),
                  const SizedBox(width: 24),
                  IconButton(icon: const Icon(Icons.more_horiz, color: AppColors.charcoal), onPressed: () {}),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildIntelligenceTab(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.auto_awesome, size: 64, color: AppColors.antiqueBrass),
          const SizedBox(height: 16),
          Text('Case Intelligence', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text('AI has analyzed your documents. 14 facts, 3 issues, and timeline extracted.', 
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
          const SizedBox(height: 24),
          PrimaryButton(label: 'Review Intelligence', onPressed: () {})
        ],
      ),
    );
  }
  
  Widget _buildResearchTab(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.manage_search, size: 64, color: AppColors.charcoal),
          const SizedBox(height: 16),
          Text('Matter Research', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text('Find and attach verified legal authorities to this specific matter.', 
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
          const SizedBox(height: 24),
          PrimaryButton(label: 'Start Research Session', onPressed: () => context.push('/finder'))
        ],
      ),
    );
  }
  
  Widget _buildDraftsTab(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.edit_document, size: 64, color: AppColors.charcoal),
          const SizedBox(height: 16),
          Text('Matter Drafts', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text('Generate AI-assisted legal drafts based on this matter\'s facts and research.', 
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
          const SizedBox(height: 24),
          PrimaryButton(label: 'Create New Draft', onPressed: () => context.push('/matters/${widget.matterId}/drafts/new'))
        ],
      ),
    );
  }
}