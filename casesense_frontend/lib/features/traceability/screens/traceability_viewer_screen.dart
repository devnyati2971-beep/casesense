import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/tactile_3d_card.dart';

class TraceabilityViewerScreen extends StatefulWidget {
  final String draftId;
  const TraceabilityViewerScreen({super.key, required this.draftId});

  @override
  State<TraceabilityViewerScreen> createState() => _TraceabilityViewerScreenState();
}

class _TraceabilityViewerScreenState extends State<TraceabilityViewerScreen> {
  int _currentStep = 0; // 0: Argument, 1: Proposition, 2: Passage, 3: Judgment

  void _nextStep() {
    if (_currentStep < 3) setState(() => _currentStep++);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.nearBlack,
      body: Stack(
        children: [
          // Background Gradient
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: Alignment.center,
                radius: 1.2,
                colors: [AppColors.charcoal, AppColors.nearBlack],
              ),
            ),
          ),
          
          // Header
          Positioned(
            top: 40, left: 40,
            child: IconButton(
              icon: const Icon(Icons.close, color: AppColors.ivory, size: 32),
              onPressed: () => context.pop(),
            ),
          ),
          
          // Spatial 3D Stack
          Center(
            child: SizedBox(
              height: 600,
              width: 800,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  _buildNode(3, 'Original Source', 'Judgment details and exact file.', AppColors.espresso, _currentStep >= 3),
                  _buildNode(2, 'Verified Passage', 'Exact verbatim quote from the judgment.', AppColors.charcoal, _currentStep >= 2),
                  _buildNode(1, 'Legal Proposition', 'The extracted principle supported by the passage.', AppColors.stone, _currentStep >= 1, isDark: false),
                  _buildNode(0, 'Draft Argument', 'The claim made in your document.', AppColors.ivory, _currentStep >= 0, isDark: false),
                ],
              ),
            ),
          ),

          // Stepper Controls
          Positioned(
            bottom: 60, left: 0, right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (_currentStep > 0)
                  TextButton.icon(
                    onPressed: () => setState(() => _currentStep--),
                    icon: const Icon(Icons.arrow_upward, color: AppColors.warmGrey),
                    label: const Text('Back up the chain', style: TextStyle(color: AppColors.warmGrey)),
                  ),
                const SizedBox(width: 32),
                if (_currentStep < 3)
                  ElevatedButton.icon(
                    onPressed: _nextStep,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.antiqueBrass,
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                    ),
                    icon: const Icon(Icons.arrow_downward, color: AppColors.ivory),
                    label: const Text('Trace Deeper', style: TextStyle(color: AppColors.ivory)),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNode(int index, String title, String subtitle, Color bgColor, bool isVisible, {bool isDark = true}) {
    // 3D Math for stacking and moving cards out of the way
    final isPassed = _currentStep > index;
    final scale = isVisible ? (isPassed ? 1.1 : 1.0) : 0.8;
    final opacity = isVisible ? (isPassed ? 0.0 : 1.0) : 0.0;
    final translateY = isVisible ? (isPassed ? -200.0 : 0.0) : 100.0; // Drops in from bottom, flies up when passed

    return AnimatedPositioned(
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeInOutCubic,
      top: 100 + translateY + (index * 15), // Slight stacking offset
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 400),
        opacity: opacity,
        child: Transform.scale(
          scale: scale,
          child: Tactile3DCard(
            depth: 0.03,
            child: Container(
              width: 600,
              padding: const EdgeInsets.all(48),
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(8),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 30, offset: const Offset(0, 15)),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('STEP ${index + 1}', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.antiqueBrass)),
                  const SizedBox(height: 16),
                  Text(title, style: Theme.of(context).textTheme.displayMedium?.copyWith(color: isDark ? AppColors.ivory : AppColors.nearBlack)),
                  const SizedBox(height: 16),
                  Text(subtitle, style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: isDark ? AppColors.warmGrey : AppColors.charcoal)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}