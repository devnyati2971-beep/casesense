import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/auth_scaffold.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../providers/auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter both email and password.')),
      );
      return;
    }

    await ref.read(authControllerProvider.notifier).login(email, password);

    final authState = ref.read(authControllerProvider);
    if (authState.hasValue && authState.value!.isAuthenticated && mounted) {
      // Return the user to where they were heading (guest → auth upgrade).
      final from = GoRouterState.of(context).uri.queryParameters['from'];
      context.go(from ?? '/dashboard');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);

    final form = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('CaseSense', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.antiqueBrass, letterSpacing: 1.2, fontWeight: FontWeight.w700)),
        const SizedBox(height: 32),
        Text('Welcome back.', style: Theme.of(context).textTheme.displayMedium),
        const SizedBox(height: 8),
        Text('Sign in to your legal workspace.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
        const SizedBox(height: 36),

        AppTextField(
          controller: _emailController,
          label: 'Email Address',
          hint: 'advocate@example.com',
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 20),
        AppTextField(
          controller: _passwordController,
          label: 'Password',
          isPassword: true,
        ),

        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => context.push('/forgot-password'),
            style: TextButton.styleFrom(foregroundColor: AppColors.subtleBronze),
            child: const Text('Forgot Password?'),
          ),
        ),

        const SizedBox(height: 20),

        if (authState.hasError) ...[
          Text('Invalid credentials. Please try again.', style: const TextStyle(color: AppColors.error)),
          const SizedBox(height: 16),
        ],

        SizedBox(
          width: double.infinity,
          child: authState.isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
            : PrimaryButton(
                label: 'Sign In',
                onPressed: _handleLogin,
              ),
        ),

        const SizedBox(height: 16),
        Center(
          child: TextButton(
            onPressed: () => context.push('/register'),
            style: TextButton.styleFrom(foregroundColor: AppColors.charcoal),
            child: const Text('Don\'t have an account? Create one'),
          ),
        ),

        const SizedBox(height: 8),
        Row(
          children: [
            const Expanded(child: Divider(color: AppColors.stone)),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text('OR', style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.subtleBronze)),
            ),
            const Expanded(child: Divider(color: AppColors.stone)),
          ],
        ),
        const SizedBox(height: 16),

        // OAuth Button
        OutlinedButton.icon(
          onPressed: () => context.push('/oauth/callback'),
          icon: const Icon(Icons.g_mobiledata, size: 28),
          label: const Text('Continue with Google'),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.charcoal,
            side: const BorderSide(color: AppColors.stone),
            minimumSize: const Size(double.infinity, 50),
          ),
        ),

        const SizedBox(height: 16),
        // v2.2 guest tier — browsing Home + Citation Finder needs no account.
        Center(
          child: TextButton(
            onPressed: () => context.go('/dashboard'),
            child: Text(
              'Continue without account — try the Citation Finder free',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppColors.antiqueBrass),
            ),
          ),
        ),
      ],
    );

    return AuthScaffold(formChild: form);
  }
}
