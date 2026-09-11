import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../../../shared/widgets/auth_scaffold.dart';
import '../../../shared/widgets/primary_button.dart';

class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key});

  @override
  ConsumerState<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _passwordController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final token = GoRouterState.of(context).uri.queryParameters['token'];
    final password = _passwordController.text;
    if (token == null || token.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This password-reset link is invalid.')),
      );
      return;
    }
    if (password.length < 8 ||
        !password.contains(RegExp(r'[A-Z]')) ||
        !password.contains(RegExp(r'[0-9]'))) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Use 8+ characters with an uppercase letter and a number.')),
      );
      return;
    }

    setState(() => _submitting = true);
    try {
      await ref.read(dioProvider).post(
        Endpoints.resetPassword,
        data: {'token': token, 'new_password': password},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password reset. You can now sign in.')),
      );
      context.go('/login');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This reset link is invalid or has expired.')),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      showBrandStrip: false,
      formChild: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('CaseSense', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: AppColors.antiqueBrass, letterSpacing: 1.2, fontWeight: FontWeight.w700)),
          const SizedBox(height: 32),
          Text('Choose a new password', style: Theme.of(context).textTheme.displayMedium),
          const SizedBox(height: 12),
          Text('Use at least 8 characters, including an uppercase letter and a number.', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.warmGrey)),
          const SizedBox(height: 28),
          AppTextField(controller: _passwordController, label: 'New password', isPassword: true),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: _submitting
                ? const Center(child: CircularProgressIndicator(color: AppColors.antiqueBrass))
                : PrimaryButton(label: 'Reset Password', onPressed: _submit),
          ),
        ],
      ),
    );
  }
}
