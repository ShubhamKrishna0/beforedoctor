import 'package:beforedoctor/app.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('Before Doctor renders landing content', (tester) async {
    await tester.pumpWidget(const BeforeDoctorApp());

    expect(find.text('Before Doctor'), findsOneWidget);
    expect(find.textContaining('Describe symptoms'), findsOneWidget);
  });
}
