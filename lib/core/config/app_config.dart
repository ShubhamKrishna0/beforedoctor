class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://beforedoctor.onrender.com/api/v1',
  );
}
