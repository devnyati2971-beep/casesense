import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/auth_scaffold.dart';
import '../../../shared/widgets/primary_button.dart';
import '../../../shared/widgets/app_text_field.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final TextEditingController _emailController = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _sendResetLink() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your email address.')),
      );
      return;
    }

    setState(() => _sending = true);
    String? errorText;
    try {
      final dio = ref.read(dioProvider);
      await dio.post(Endpoints.forgotPassword, data: {'email': email});
    } catch (e) {
      // v2.1: generic response regardless of account existence — except 429,
      // which the user should actually see (1 request per minute, §75.1).
      final code = (e as dynamic).response?.statusCode;
      if (code == 429) {
        errorText = 'Please wait a minute before requesting another reset link.';
      }
    }
    if (!mounted) return;
    setState(() => _sending = false);

    if (errorText != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(errorText)),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('If that address exists, a reset link is on its way.')),
    );
    context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final form = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('CaseSense', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.antiqueBrass, letterSpacing: 1.2, fontWeight: FontWeight.w700)),
        const SizedBox(height: 32),
        Text('Reset Password', style: Theme.of(context).textTheme.displayMedium),
        const SizedBox(height: 16),
        Text('If that address exists, a link is on its way. Please enter your email below.', // Strict v2.1 generic wording
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey)),
        const SizedBox(height: 40),
        AppTextField(
          controller: _emailController,
          label: 'Email Address',
          hint: 'advocate@example.com',
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Icon(Icons.timer_outlined, size: 14, color: AppColors.subtleBronze),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                'For security, reset links can be requested once per minute.',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.subtleBronze),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: _sending
              ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
              : PrimaryButton(label: 'Send Reset Link', onPressed: _sendResetLink),
        ),
        const SizedBox(height: 12),
        Center(
          child: TextButton(
            onPressed: () => context.pop(),
            child: const Text('Back to Sign In'),
          ),
        ),
      ],
    );

    return AuthScaffold(formChild: form, showBrandStrip: false);
  }
}
