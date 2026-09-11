import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

void main() {
  usePathUrlStrategy();
  runApp(
    // ProviderScope is required for Riverpod state management
    const ProviderScope(
      child: CaseSenseApp(),
    ),
  );
}

class CaseSenseApp extends ConsumerWidget {
  const CaseSenseApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch the router provider to handle navigation, auth guarding, and screens
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'CaseSense',
      theme: AppTheme.lightTheme,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}