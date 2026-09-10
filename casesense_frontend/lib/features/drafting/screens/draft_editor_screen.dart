import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/ghost_button.dart';
import '../../../shared/widgets/tactile_3d_card.dart';

class DraftEditorScreen extends StatefulWidget {
  const DraftEditorScreen({super.key});

  @override
  State<DraftEditorScreen> createState() => _DraftEditorScreenState();
}

class _DraftEditorScreenState extends State<DraftEditorScreen> {
  String _selectedLanguage = 'English'; // v2.2 Feature

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.nearBlack,
      body: Stack(
        children: [
          Positioned.fill(
            child: Image.asset(
              'assets/images/dashboard_img.png', 
              fit: BoxFit.cover,
              color: AppColors.nearBlack.withOpacity(0.65),
              colorBlendMode: BlendMode.darken,
            ),
          ),
          Column(
            children: [
              _buildTopBar(context),
              Expanded(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildLeftRail(context),
                    Expanded(
                      flex: 6,
                      child: _buildPhysicalPaperCanvas(context),
                    ),
                    _buildRightRail(context),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTopBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      decoration: BoxDecoration(
        color: AppColors.espresso.withOpacity(0.8),
        border: const Border(bottom: BorderSide(color: AppColors.charcoal)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              IconButton(icon: const Icon(Icons.arrow_back, color: AppColors.ivory), onPressed: () => context.pop()),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Bail Application - Supreme Court', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.check_circle, color: AppColors.success, size: 12),
                      const SizedBox(width: 4),
                      Text('Draft Saved • v3', style: Theme.of(context).textTheme.labelSmall),
                    ],
                  )
                ],
              ),
            ],
          ),
          Row(
            children: [
              // v2.2 Language Selector
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.charcoal,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppColors.stone.withOpacity(0.2)),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _selectedLanguage,
                    dropdownColor: AppColors.espresso,
                    icon: const Icon(Icons.language, color: AppColors.subtleBronze, size: 16),
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.ivory),
                    onChanged: (String? newValue) => setState(() => _selectedLanguage = newValue!),
                    items: <String>['English', 'हिंदी', 'Bilingual'].map<DropdownMenuItem<String>>((String value) {
                      return DropdownMenuItem<String>(value: value, child: Padding(padding: const EdgeInsets.only(right: 8.0), child: Text(value)));
                    }).toList(),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              GhostButton(label: 'Share', icon: Icons.share_outlined, onPressed: () {}),
              const SizedBox(width: 16),
              PrimaryButton(label: 'Download PDF', onPressed: () {}), // v2.2 action
            ],
          )
        ],
      ),
    );
  }

  Widget _buildLeftRail(BuildContext context) {
    return Container(
      width: 250,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: AppColors.espresso.withOpacity(0.5), border: const Border(right: BorderSide(color: AppColors.charcoal))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Document Outline', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.warmGrey)),
          const SizedBox(height: 24),
          _OutlineItem(title: 'Title & Jurisdiction', isActive: false),
          _OutlineItem(title: 'Parties', isActive: false),
          _OutlineItem(title: 'Facts of the Case', isActive: false),
          _OutlineItem(title: 'Grounds for Bail', isActive: true),
          _OutlineItem(title: 'Prayer', isActive: false),
        ],
      ),
    );
  }

  Widget _buildPhysicalPaperCanvas(BuildContext context) {
    return Center(
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.95, end: 1.0),
        duration: const Duration(milliseconds: 800),
        curve: Curves.elasticOut,
        builder: (context, value, child) {
          return Transform.scale(scale: value, child: Opacity(opacity: (value - 0.95) * 20, child: child));
        },
        child: Container(
          width: 800,
          margin: const EdgeInsets.symmetric(vertical: 32),
          decoration: BoxDecoration(
            color: AppColors.ivory,
            borderRadius: BorderRadius.circular(2),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.5), blurRadius: 40, offset: const Offset(0, 20))],
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 80, vertical: 80),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(child: Text('GROUNDS FOR BAIL', style: Theme.of(context).textTheme.headlineMedium?.copyWith(letterSpacing: 2))),
                const SizedBox(height: 48),
                Text('1. That the prolonged incarceration of the applicant without a speedy trial constitutes a direct violation of the fundamental rights guaranteed under Article 21 of the Constitution of India.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.8)),
                const SizedBox(height: 16),
                Tactile3DCard(
                  depth: 0.02,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(color: AppColors.parchment, border: Border.all(color: AppColors.antiqueBrass.withOpacity(0.3)), borderRadius: BorderRadius.circular(4)),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.bookmark, color: AppColors.antiqueBrass, size: 14),
                        const SizedBox(width: 8),
                        Text('Kesavananda Bharati v. State of Kerala (1973)', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.charcoal)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Text('2. That the charge-sheet has already been filed, and no further custodial interrogation is required, mitigating any risk of evidence tampering.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.8)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRightRail(BuildContext context) {
    return Container(
      width: 320,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(color: AppColors.espresso.withOpacity(0.9), border: const Border(left: BorderSide(color: AppColors.charcoal))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.antiqueBrass, size: 18),
              const SizedBox(width: 8),
              Text('Gemini Assistant', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
            ],
          ),
          const SizedBox(height: 32),
          Tactile3DCard(
            depth: 0.04,
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: AppColors.charcoal, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.stone.withOpacity(0.1))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Missing Authority', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.warning)),
                  const SizedBox(height: 8),
                  Text('Consider citing a precedent on post-chargesheet bail to strengthen Ground 2.', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.ivory)),
                  const SizedBox(height: 16),
                  PrimaryButton(label: 'Search Precedents', onPressed: () {}),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }
}

class _OutlineItem extends StatelessWidget {
  final String title;
  final bool isActive;
  const _OutlineItem({required this.title, required this.isActive});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Row(
        children: [
          Container(width: 2, height: 16, color: isActive ? AppColors.antiqueBrass : Colors.transparent),
          const SizedBox(width: 12),
          Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(color: isActive ? AppColors.ivory : AppColors.warmGrey, fontWeight: isActive ? FontWeight.w600 : FontWeight.w400, fontSize: 14)),
        ],
      ),
    );
  }
}