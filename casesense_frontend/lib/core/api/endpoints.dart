class Endpoints {
  static const String baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000/api/v1');

  // Auth (v2.1)
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String refresh = '/auth/refresh';
  static const String logout = '/auth/logout';
  static const String logoutAll = '/auth/logout-all';
  static const String me = '/auth/me';
  static const String verifyEmail = '/auth/verify-email';
  static const String resendVerification = '/auth/resend-verification';
  static const String forgotPassword = '/auth/forgot-password';
  static const String resetPassword = '/auth/reset-password';
  static const String changePassword = '/auth/change-password';

  // Users
  static const String updateMe = '/users/me';

  // Matters
  static const String matters = '/matters';
  static String matterDetail(String id) => '/matters/$id';
  static String matterArchive(String id) => '/matters/$id/archive';
  static String matterRestore(String id) => '/matters/$id/restore';
  static String matterDelete(String id) => '/matters/$id/delete';
  static String matterDocuments(String id) => '/matters/$id/documents';
  static String matterIntelligence(String id) => '/matters/$id/intelligence';
  static String matterBrief(String id) => '/matters/$id/brief';

  // Research
  static const String queryResearch = '/research/query';
  static String caseResearch(String id) => '/matters/$id/research';
  static String researchSession(String sid) => '/research/$sid';
  static const String listResearch = '/research';

  // Authorities
  static String selectAuthority(String sid) => '/research/$sid/authorities';
  static String authorityDetail(String id) => '/authorities/$id';
  static String authorityNotes(String id) => '/authorities/$id/notes';

  // Drafting
  static String drafts(String matterId) => '/matters/$matterId/drafts';
  static String draftDetail(String draftId) => '/drafts/$draftId';
  static String draftGenerate(String draftId) => '/drafts/$draftId/generate';
  static String draftRegenerate(String draftId) => '/drafts/$draftId/regenerate';
  static String draftSections(String draftId) => '/drafts/$draftId/sections';
  static String draftQuestionnaire(String draftId) => '/drafts/$draftId/questionnaire';
  static String draftBrief(String draftId) => '/drafts/$draftId/brief';
  static String draftFinalize(String draftId) => '/drafts/$draftId/finalize';
  static String draftExport(String draftId) => '/drafts/$draftId/exports';
  static String draftTraceability(String draftId) => '/drafts/$draftId/traceability';

  // Saved Citations (v2.2)
  static const String savedCitations = '/saved-citations';
  static String savedCitationDetail(String id) => '/saved-citations/$id';

  // Judgments
  static const String judgments = '/judgments';
  static String judgmentDetail(String id) => '/judgments/$id';

  // Audit
  static const String auditLogs = '/audit/logs';
}