import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/auth_controller.dart';

class OAuthCallbackScreen extends ConsumerStatefulWidget {
  final String? code;
  final bool linkRequired;
  
  const OAuthCallbackScreen({super.key, this.code, this.linkRequired = false});

  @override
  ConsumerState<OAuthCallbackScreen> createState() => _OAuthCallbackScreenState();
}

class _OAuthCallbackScreenState extends ConsumerState<OAuthCallbackScreen> {
  @override
  void initState() {
    super.initState();
    _processOAuth();
  }

  Future<void> _processOAuth() async {
    final uri = Uri.base; // or GoRouterState.of(context).uri if accessible, but Uri.base works perfectly for flutter web routing
    final code = uri.queryParameters['code'];
    final stateParam = uri.queryParameters['state'];

    if (code == null || stateParam == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('OAuth login failed: Missing code or state.')));
        context.go('/login');
      }
      return;
    }

    final ok = await ref.read(authControllerProvider.notifier).oauthLogin(code, stateParam);

    if (mounted) {
      if (ok) {
        context.go('/dashboard');
      } else {
        final authState = ref.read(authControllerProvider);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(authState.error?.toString() ?? 'OAuth login failed.')));
        context.go('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.espresso,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(color: AppColors.antiqueBrass),
            const SizedBox(height: 24),
            Text('Securing your session...', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.ivory)),
          ],
        ),
      ),
    );
  }
}