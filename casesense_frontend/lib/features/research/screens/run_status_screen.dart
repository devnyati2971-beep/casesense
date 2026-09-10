import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/research_controller.dart';

class RunStatusScreen extends ConsumerStatefulWidget {
  final String sessionId;
  const RunStatusScreen({super.key, required this.sessionId});

  @override
  ConsumerState<RunStatusScreen> createState() => _RunStatusScreenState();
}

class _RunStatusScreenState extends ConsumerState<RunStatusScreen> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  bool _hasNavigated = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat(reverse: true);
    
    // Start polling the backend job status via Riverpod Controller
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(researchControllerProvider.notifier).pollSessionStatus(widget.sessionId);
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Listen for state changes to trigger navigation
    ref.listen<ResearchState>(researchControllerProvider, (previous, next) {
      if (next.currentStage == 'COMPLETED' && !_hasNavigated) {
        _hasNavigated = true;
        context.pushReplacement('/research/${widget.sessionId}/results');
      }
    });

    final researchState = ref.watch(researchControllerProvider);

    return Scaffold(
      backgroundColor: AppColors.espresso, // Dark immersive loading
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                return Transform.scale(
                  scale: 1.0 + (_pulseController.value * 0.05),
                  child: const Icon(Icons.travel_explore, size: 80, color: AppColors.antiqueBrass),
                );
              },
            ),
            const SizedBox(height: 40),
            Text(
              _getLoadingText(researchState.currentStage), 
              style: Theme.of(context).textTheme.displayMedium?.copyWith(color: AppColors.ivory)
            ),
            const SizedBox(height: 16),
            Text(
              'Session ID: ${widget.sessionId}', 
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey)
            ),
            const SizedBox(height: 48),
            const SizedBox(
              width: 300,
              child: LinearProgressIndicator(color: AppColors.antiqueBrass, backgroundColor: AppColors.charcoal),
            )
          ],
        ),
      ),
    );
  }

  String _getLoadingText(String stage) {
    switch (stage) {
      case 'RETRIEVING': return 'Retrieving Judgments...';
      case 'ANALYZING': return 'Analyzing Legal Concepts...';
      case 'VERIFYING': return 'Verifying Citations...';
      case 'COMPLETED': return 'Redirecting...';
      default: return 'Starting AI Engine...';
    }
  }
}