import 'package:flutter/material.dart';

class AppColors {
  // Deep immersive backgrounds (Sidebar & Hero)
  static const Color nearBlack = Color(0xFF0F172A); // Slate 900
  static const Color espresso = Color(0xFF1E293B); // Slate 800
  static const Color charcoal = Color(0xFF334155); // Slate 700
  
  // Clean UI Canvas
  static const Color ivory = Color(0xFFFFFFFF); // White for cards
  static const Color parchment = Color(0xFFF8F9FA); // Off-white for background
  static const Color stone = Color(0xFFE2E8F0); // Borders / Slate 200
  
  // Accents (CaseSense Gold/Bronze)
  static const Color antiqueBrass = Color(0xFFC5A059);
  static const Color subtleBronze = Color(0xFFA68553);
  static const Color warmGrey = Color(0xFF64748B); // Slate 500

  // States
  static const Color success = Color(0xFF3B7A57);
  static const Color warning = Color(0xFFD4A373);
  static const Color error = Color(0xFF9E2A2B);
}

class AppTheme {
  static ThemeData get theme => lightTheme;

  static ThemeData get lightTheme {
    return ThemeData(
      scaffoldBackgroundColor: AppColors.parchment,
      primaryColor: AppColors.antiqueBrass,
      
      // Editorial Typography
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontFamily: 'PlayfairDisplay', color: AppColors.nearBlack, fontWeight: FontWeight.bold, letterSpacing: -1.0),
        displayMedium: TextStyle(fontFamily: 'PlayfairDisplay', color: AppColors.nearBlack, fontWeight: FontWeight.w600, fontSize: 32, letterSpacing: -0.5),
        headlineMedium: TextStyle(fontFamily: 'PlayfairDisplay', color: AppColors.nearBlack, fontWeight: FontWeight.w600, fontSize: 24),
        titleMedium: TextStyle(fontFamily: 'Inter', color: AppColors.nearBlack, fontWeight: FontWeight.w600, fontSize: 16),
        bodyLarge: TextStyle(fontFamily: 'Inter', color: AppColors.charcoal, fontSize: 16, height: 1.6),
        bodyMedium: TextStyle(fontFamily: 'Inter', color: AppColors.charcoal, fontSize: 14, height: 1.5),
        labelSmall: TextStyle(fontFamily: 'Inter', color: AppColors.warmGrey, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 1.2),
      ),
      
      colorScheme: ColorScheme.light(
        primary: AppColors.antiqueBrass,
        secondary: AppColors.subtleBronze,
        surface: AppColors.ivory,
        error: AppColors.error,
        onPrimary: AppColors.ivory,
      ),
    );
  }
}