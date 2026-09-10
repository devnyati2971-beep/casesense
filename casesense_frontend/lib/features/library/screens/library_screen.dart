import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_sidebar.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/tactile_3d_card.dart';
import '../../matters/providers/matters_list_controller.dart';
import '../../research/providers/saved_citations_controller.dart';

/// Library — the user's organized view of matter documents and legal references.
/// Backed by matters (with documents) + saved citations.
class LibraryScreen extends ConsumerStatefulWidget {
  const LibraryScreen({super.key});

  @override
  ConsumerState<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends ConsumerState<LibraryScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _tab = 'matters'; // matters | citations

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
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final mattersState = ref.watch(mattersListControllerProvider);
    final savedState = ref.watch(savedCitationsControllerProvider);
    final query = _searchController.text.trim().toLowerCase();

    final matters = mattersState.matters.where((m) {
      if (query.isEmpty) return true;
      return (m['title']?.toString().toLowerCase().contains(query) ?? false) ||
          (m['court_name']?.toString().toLowerCase().contains(query) ?? false);
    }).toList();

    final citations = savedState.citations.where((c) {
      if (query.isEmpty) return true;
      return (c['case_name']?.toString().toLowerCase().contains(query) ?? false);
    }).toList();

    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: Row(
        children: [
          const AppSidebar(currentRoute: '/library'),
          Expanded(
            child: SingleChildScrollView(
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
                          Text('Legal Library', style: Theme.of(context).textTheme.displayMedium),
                          const SizedBox(height: 8),
                          Text('Your organized view of matter documents and legal references.',
                            style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
                        ],
                      ),
                      PrimaryButton(
                        label: 'Upload Document',
                        icon: Icons.upload_file,
                        onPressed: () => context.push('/history'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // Tab toggle + search
                  Row(
                    children: [
                      _Toggle(label: 'Matters (${mattersState.matters.length})', isActive: _tab == 'matters', onTap: () => setState(() => _tab = 'matters')),
                      const SizedBox(width: 12),
                      _Toggle(label: 'Citations (${savedState.citations.length})', isActive: _tab == 'citations', onTap: () => setState(() => _tab = 'citations')),
                      const SizedBox(width: 24),
                      Expanded(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.parchment,
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(color: AppColors.stone),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.search, color: AppColors.subtleBronze, size: 18),
                              const SizedBox(width: 10),
                              Expanded(
                                child: TextField(
                                  controller: _searchController,
                                  onChanged: (_) => setState(() {}),
                                  decoration: const InputDecoration(
                                    border: InputBorder.none,
                                    hintText: 'Search the library...',
                                    isDense: true,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 32),

                  if (_tab == 'matters') ...[
                    if (matters.isEmpty)
                      _Empty(icon: Icons.folder_open, title: 'No matters in your library', message: 'Create a matter and upload documents to build your library.')
                    else
                      GridView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 3, mainAxisSpacing: 16, crossAxisSpacing: 16, childAspectRatio: 2.2,
                        ),
                        itemCount: matters.length,
                        itemBuilder: (context, index) {
                          final matter = matters[index];
                          return Tactile3DCard(
                            depth: 0.015,
                            child: InkWell(
                              onTap: () => context.push('/matters/${matter['id']}'),
                              borderRadius: BorderRadius.circular(8),
                              child: Container(
                                padding: const EdgeInsets.all(20),
                                decoration: BoxDecoration(
                                  color: AppColors.parchment,
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppColors.stone),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Row(
                                      children: [
                                        const Icon(Icons.folder, color: AppColors.antiqueBrass, size: 20),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: Text(matter['title'] ?? 'Untitled',
                                            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 15),
                                            overflow: TextOverflow.ellipsis),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      '${matter['case_number'] ?? 'No case no.'} • ${matter['court_name'] ?? '—'}',
                                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 12),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                  ] else ...[
                    if (citations.isEmpty)
                      _Empty(icon: Icons.bookmark_outline, title: 'No saved citations', message: 'Save citations from the Citation Finder to see them here.')
                    else
                      for (final citation in citations)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Container(
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: AppColors.parchment,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppColors.stone),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.bookmark, color: AppColors.error, size: 18),
                                const SizedBox(width: 14),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(citation['case_name'] ?? 'Untitled',
                                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontSize: 15),
                                        overflow: TextOverflow.ellipsis),
                                      if (citation['citation_text']?.toString().isNotEmpty == true)
                                        Text(citation['citation_text'].toString(),
                                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warmGrey, fontSize: 12)),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.chevron_right, color: AppColors.warmGrey),
                              ],
                            ),
                          ),
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

class _Toggle extends StatelessWidget {
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _Toggle({required this.label, required this.isActive, required this.onTap});

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
          border: Border.all(color: isActive ? AppColors.charcoal : AppColors.stone),
        ),
        child: Text(label, style: Theme.of(context).textTheme.titleMedium?.copyWith(
          color: isActive ? AppColors.ivory : AppColors.subtleBronze, fontSize: 13)),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  final IconData icon;
  final String title;
  final String message;

  const _Empty({required this.icon, required this.title, required this.message});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 80),
      child: Center(
        child: Column(
          children: [
            Icon(icon, size: 64, color: AppColors.stone),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 8),
            Text(message, style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
          ],
        ),
      ),
    );
  }
}
