import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

// Auth Controller
import '../../features/auth/providers/auth_controller.dart';

// Auth Screens
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/auth/screens/verify_email_screen.dart';
import '../../features/auth/screens/forgot_password_screen.dart';
import '../../features/auth/screens/reset_password_screen.dart';
import '../../features/auth/screens/oauth_callback_screen.dart';
import '../../features/account/screens/account_screen.dart';

// Dashboard & Matters
import '../../features/dashboard/screens/dashboard_screen.dart';
import '../../features/matters/screens/matter_detail_screen.dart';
import '../../features/matters/screens/history_screen.dart';

// Research Screens
import '../../features/research/screens/citation_finder_screen.dart';
import '../../features/research/screens/run_status_screen.dart';
import '../../features/research/screens/research_results_screen.dart';
import '../../features/research/screens/judgment_detail_screen.dart';
import '../../features/research/screens/saved_citations_screen.dart';

// Drafting & Traceability Screens
import '../../features/drafting/screens/draft_wizard_screen.dart';
import '../../features/drafting/screens/drafts_list_screen.dart';
import '../../features/drafting/screens/draft_questionnaire_screen.dart';
import '../../features/drafting/screens/draft_brief_screen.dart';
import '../../features/drafting/screens/draft_editor_screen.dart';
import '../../features/traceability/screens/traceability_viewer_screen.dart';

// Library
import '../../features/library/screens/library_screen.dart';

// Helper for premium page transitions
CustomTransitionPage buildPageWithDefaultTransition({
  required BuildContext context, 
  required GoRouterState state, 
  required Widget child,
}) {
  return CustomTransitionPage(
    key: state.pageKey,
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      return FadeTransition(
        opacity: CurveTween(curve: Curves.easeInOut).animate(animation),
        child: SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, 0.02),
            end: Offset.zero,
          ).animate(CurveTween(curve: Curves.easeOutQuart).animate(animation)),
          child: child,
        ),
      );
    },
  );
}

/// v2.2 guest tier — these destinations are browsable without an account.
/// The Citation Finder allows 2 free searches / 24h (backend-enforced §75.1);
/// every other service requires sign-in.
const publicLocations = <String>{
  '/dashboard',
  '/finder',
};

bool _isPublicLocation(String location) {
  if (publicLocations.contains(location)) return true;
  // Guest search flow (status + results of their own session).
  if (location.startsWith('/research/') &&
      (location.endsWith('/status') || location.endsWith('/results'))) {
    return true;
  }
  return false;
}

final routerProvider = Provider<GoRouter>((ref) {
  // GoRouter owns navigation state. Recreating it on every auth-state change
  // resets it to `initialLocation`, which made a successful login appear to
  // land on the dashboard as a guest. Keep one router and refresh redirects.
  late final GoRouter router;
  router = GoRouter(
    initialLocation: '/dashboard',
    redirect: (context, state) {
      final authController = ref.read(authControllerProvider);
      final location = state.matchedLocation;
      final isAuthRoute = location == '/login' ||
          location == '/register' ||
          location == '/verify-email' ||
          location == '/forgot-password' ||
          location == '/reset-password' ||
          location.startsWith('/oauth/callback');
      // A reset link must remain reachable even in a browser that already has
      // a valid session; it is a token-authorized action, not a sign-in page.
      final isPostAuthRoute = location == '/login' ||
          location == '/register' ||
          location == '/forgot-password' ||
          location.startsWith('/oauth/callback');

      final authState = authController.value;
      final isAuthed = authState?.isAuthenticated ?? false;
      final isVerified = authState?.isVerified ?? false;

      // Wait for auth check to finish before redirecting.
      if (authController.isLoading) return null;

      if (!isAuthed && !isAuthRoute && !_isPublicLocation(location)) {
        // Remember where the user was heading so login can return them there.
        final from = state.uri.toString();
        return '/login?from=$from';
      }

      if (isAuthed) {
        if (!isVerified && location != '/verify-email') {
          return '/verify-email';
        }
        if (isVerified && isPostAuthRoute) {
          return '/dashboard';
        }
      }

      return null;
    },
    routes: [
      GoRoute(path: '/', redirect: (context, state) => '/dashboard'),
      
      // Auth Routes
      GoRoute(path: '/login', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const LoginScreen())),
      GoRoute(path: '/register', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const RegisterScreen())),
      GoRoute(path: '/verify-email', builder: (context, state) => const VerifyEmailScreen()),
      GoRoute(path: '/forgot-password', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const ForgotPasswordScreen())),
      GoRoute(path: '/reset-password', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const ResetPasswordScreen())),
      GoRoute(
        path: '/oauth/callback', 
        pageBuilder: (context, state) {
          final linkRequired = state.uri.queryParameters['link_required'] == 'true';
          return buildPageWithDefaultTransition(context: context, state: state, child: OAuthCallbackScreen(linkRequired: linkRequired));
        }
      ),

      // Public (guest) Routes — dashboard + Citation Finder, v2.2 guest tier
      GoRoute(path: '/dashboard', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const DashboardScreen())),
      GoRoute(path: '/finder', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const CitationFinderScreen())),
      GoRoute(path: '/research/:sid/status', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: RunStatusScreen(sessionId: state.pathParameters['sid']!))),
      GoRoute(path: '/research/:sid/results', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: ResearchResultsScreen(sessionId: state.pathParameters['sid']!))),

      // Authenticated Routes
      GoRoute(path: '/account', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const AccountScreen())),
      GoRoute(path: '/library', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const LibraryScreen())),
      GoRoute(path: '/history', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const HistoryScreen())),
      
      // Research & Citations
      GoRoute(path: '/saved-citations', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const SavedCitationsScreen())),
      GoRoute(
        path: '/judgment/:id',
        pageBuilder: (context, state) => buildPageWithDefaultTransition(
          context: context,
          state: state,
          child: JudgmentDetailScreen(judgmentId: state.pathParameters['id']),
        ),
      ),
      
      // Drafting
      GoRoute(path: '/drafts/new', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const DraftWizardScreen())),
      GoRoute(path: '/drafts_list', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const DraftsListScreen())),
      GoRoute(path: '/matters/:id/drafts/new', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: DraftQuestionnaireScreen(matterId: state.pathParameters['id']!))),
      GoRoute(path: '/matters/:id/drafts/brief', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: DraftBriefScreen(matterId: state.pathParameters['id']!))),
      GoRoute(path: '/drafts/:id', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: const DraftEditorScreen())),
      GoRoute(path: '/drafts/:id/chain', pageBuilder: (context, state) => buildPageWithDefaultTransition(context: context, state: state, child: TraceabilityViewerScreen(draftId: state.pathParameters['id']!))),
      
      // Matters
      GoRoute(
        path: '/matters/:id',
        pageBuilder: (context, state) {
          final matterId = state.pathParameters['id']!;
          final tab = state.uri.queryParameters['tab'];
          return buildPageWithDefaultTransition(
            context: context, state: state, 
            child: MatterDetailScreen(matterId: matterId, initialTab: tab),
          );
        },
      ),
    ],
  );

  ref.listen<AsyncValue<AuthState>>(authControllerProvider, (_, __) {
    router.refresh();
  });
  ref.onDispose(router.dispose);
  return router;
});
