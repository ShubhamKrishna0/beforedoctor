import 'package:beforedoctor/core/constants/colors.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static ThemeData lightTheme() {
    final textTheme = GoogleFonts.dmSansTextTheme();
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: AppColors.surface,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primaryBlue,
        primary: AppColors.primaryBlue,
        secondary: AppColors.medicalGreen,
        surface: AppColors.surface,
      ),
      textTheme: textTheme.copyWith(
        headlineMedium: textTheme.headlineMedium?.copyWith(
          color: AppColors.ink,
          fontWeight: FontWeight.w700,
        ),
        bodyMedium: textTheme.bodyMedium?.copyWith(
          color: AppColors.ink.withValues(alpha: 0.82),
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      ),
    );
  }
}
