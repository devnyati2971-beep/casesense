import 'package:flutter_riverpod/legacy.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum AppLanguage { english, hindi, bilingual }

class LanguageState {
  final AppLanguage language;
  const LanguageState({this.language = AppLanguage.english});

  String get label {
    switch (language) {
      case AppLanguage.english:
        return 'English';
      case AppLanguage.hindi:
        return 'हिन्दी';
      case AppLanguage.bilingual:
        return 'Bilingual';
    }
  }
}

class LanguageController extends StateNotifier<LanguageState> {
  LanguageController() : super(const LanguageState()) {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('casesense_language') ?? 'english';
    final match = AppLanguage.values.where((l) => l.name == raw).firstOrNull;
    if (match != null) {
      state = LanguageState(language: match);
    }
  }

  Future<void> setLanguage(AppLanguage language) async {
    state = LanguageState(language: language);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('casesense_language', language.name);
  }
}

final languageProvider =
    StateNotifierProvider<LanguageController, LanguageState>((ref) {
  return LanguageController();
});
