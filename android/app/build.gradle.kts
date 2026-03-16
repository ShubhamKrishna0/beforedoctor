plugins {
    id("com.android.application")
    id("kotlin-android")
    // Flutter plugin must be after Android & Kotlin plugins
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.example.beforedoctor"

    // Use latest stable compile SDK
    compileSdk = 36

    // REQUIRED by audio plugins
    ndkVersion = "27.0.12077973"

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = "11"
    }

    defaultConfig {
        applicationId = "com.example.beforedoctor"

        // REQUIRED by record_android plugin
        minSdk = flutter.minSdkVersion

        targetSdk = 34

        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

flutter {
    source = "../.."
}
