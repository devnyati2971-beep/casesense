import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/auth_scaffold.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../providers/auth_controller.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleRegister() async {
    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (name.isEmpty || email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields.')),
      );
      return;
    }

    final ok = await ref.read(authControllerProvider.notifier).register(
      fullName: name,
      email: email,
      password: password,
    );

    if (!mounted) return;
    if (ok) {
      // v2.1 flow — verify email next.
      context.go('/verify-email');
    } else {
      final authState = ref.read(authControllerProvider);
      final error = authState.error;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error?.toString() ?? 'Registration failed. Please try again.')),
      );
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
        Text('Create an account.', style: Theme.of(context).textTheme.displayMedium),
        const SizedBox(height: 8),
        Text('Join the premium legal intelligence platform.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.subtleBronze)),
        const SizedBox(height: 32),

        AppTextField(
          controller: _nameController,
          label: 'Full Name',
          hint: 'Advocate Name',
        ),
        const SizedBox(height: 20),
        AppTextField(
          controller: _emailController,
          label: 'Email Address',
          hint: 'advocate@example.com',
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 20),
        AppTextField(
          controller: _passwordController,
          label: 'Password (min. 8 characters)',
          isPassword: true,
        ),

        if (authState.hasError) ...[
          const SizedBox(height: 16),
          Text(
            authState.error.toString(),
            style: const TextStyle(color: AppColors.error),
          ),
        ],

        const SizedBox(height: 28),
        SizedBox(
          width: double.infinity,
          child: authState.isLoading
            ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
            : PrimaryButton(
                label: 'Create Account',
                onPressed: _handleRegister,
              ),
        ),
        const SizedBox(height: 16),
        Center(
          child: TextButton(
            onPressed: () => context.go('/login'),
            style: TextButton.styleFrom(foregroundColor: AppColors.charcoal),
            child: const Text('Already have an account? Sign in'),
          ),
        ),
        const SizedBox(height: 4),
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
