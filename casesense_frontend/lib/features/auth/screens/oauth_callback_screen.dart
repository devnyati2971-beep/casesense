import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';

class OAuthCallbackScreen extends StatefulWidget {
  final String? code;
  final bool linkRequired;
  
  const OAuthCallbackScreen({super.key, this.code, this.linkRequired = false});

  @override
  State<OAuthCallbackScreen> createState() => _OAuthCallbackScreenState();
}

class _OAuthCallbackScreenState extends State<OAuthCallbackScreen> {
  @override
  void initState() {
    super.initState();
    _processOAuth();
  }

  Future<void> _processOAuth() async {
    // Simulate backend token exchange
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) {
      if (widget.linkRequired) {
        // v2.1 Explicit Linking Flow
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please sign in first to link your Google account.')));
        context.go('/login');
      } else {
        context.go('/dashboard');
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