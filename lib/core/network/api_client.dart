import 'package:beforedoctor/core/config/app_config.dart';
import 'package:dio/dio.dart';

class ApiClient {
  ApiClient()
      : dio = Dio(
          BaseOptions(
            baseUrl: AppConfig.apiBaseUrl,
            connectTimeout: const Duration(seconds: 20),
            receiveTimeout: const Duration(seconds: 60),
          ),
        );

  final Dio dio;
}
