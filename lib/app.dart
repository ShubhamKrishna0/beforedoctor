import 'package:beforedoctor/core/themes/app_theme.dart';
import 'package:beforedoctor/presentation/pages/home_page.dart';
import 'package:flutter/material.dart';

class BeforeDoctorApp extends StatelessWidget {
  const BeforeDoctorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Before Doctor',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme(),
      home: const HomePage(),
    );
  }
}
