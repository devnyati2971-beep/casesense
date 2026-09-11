import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/auth_scaffold.dart';
import '../../../shared/widgets/primary_button.dart';
import '../providers/auth_controller.dart';

class VerifyEmailScreen extends ConsumerStatefulWidget {
  const VerifyEmailScreen({super.key});

  @override
  ConsumerState<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends ConsumerState<VerifyEmailScreen> {
  bool _checking = false;
  final TextEditingController _codeController = TextEditingController();

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _verifyCode() async {
    final code = _codeController.text.trim();
    if (!RegExp(r'^\d{6}$').hasMatch(code)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter the six-digit code from your email.'),
        ),
      );
      return;
    }
    setState(() => _checking = true);
    await ref.read(authControllerProvider.notifier).verifyEmail(code);
    if (!mounted) return;
    setState(() => _checking = false);

    final auth = ref.read(authControllerProvider);
    if (auth.value?.isVerified == true) {
      context.go('/dashboard');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            auth.error?.toString() ??
                'That verification code is invalid or expired.',
          ),
        ),
      );
    }
  }

  Future<void> _resendEmail() async {
    final user = ref.read(authControllerProvider).value?.user;
    final email = user?['email']?.toString();
    if (email == null || email.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not determine your email address.'),
        ),
      );
      return;
    }
    try {
      final dio = ref.read(dioProvider);
      await dio.post(Endpoints.resendVerification, data: {'email': email});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Verification email sent again.')),
      );
    } catch (e) {
      if (!mounted) return;
      final code = (e as dynamic).response?.statusCode;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            code == 429
                ? 'Please wait a minute before requesting another email.'
                : 'Could not resend right now — try again shortly.',
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authControllerProvider).value?.user;
    final email = user?['email']?.toString() ?? 'your email';

    final form = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'CaseSense',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: AppColors.antiqueBrass,
            letterSpacing: 1.2,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 32),
        const Icon(
          Icons.mark_email_read_outlined,
          size: 56,
          color: AppColors.antiqueBrass,
        ),
        const SizedBox(height: 24),
        Text(
          'Verify your email',
          style: Theme.of(context).textTheme.displayMedium,
        ),
        const SizedBox(height: 16),
        Text(
          'We sent a six-digit verification code to $email.',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Icon(Icons.timer_outlined, size: 14, color: AppColors.subtleBronze),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                'Codes expire after 10 minutes. Emails can be resent once per minute.',
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(color: AppColors.subtleBronze),
              ),
            ),
          ],
        ),
        const SizedBox(height: 32),
        SizedBox(
          width: double.infinity,
          child: _checking
              ? const Center(
                  child: CircularProgressIndicator(
                    color: AppColors.antiqueBrass,
                  ),
                )
              : Column(
                  children: [
                    TextField(
                      controller: _codeController,
                      autofocus: true,
                      keyboardType: TextInputType.number,
                      maxLength: 6,
                      textAlign: TextAlign.center,
                      style: Theme.of(
                        context,
                      ).textTheme.headlineMedium?.copyWith(letterSpacing: 10),
                      decoration: const InputDecoration(
                        labelText: 'Verification code',
                        hintText: '000000',
                        counterText: '',
                        border: OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _verifyCode(),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: PrimaryButton(
                        label: 'Verify email',
                        onPressed: _verifyCode,
                      ),
                    ),
                  ],
                ),
        ),
        const SizedBox(height: 12),
        Center(
          child: TextButton(
            onPressed: _resendEmail,
            child: const Text('Resend Email'),
          ),
        ),
      ],
    );

    return AuthScaffold(formChild: form, showBrandStrip: false);
  }
}
