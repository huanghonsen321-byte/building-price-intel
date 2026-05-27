import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/models.dart';

void main() {
  test('PriceTodaySummary.fromJson parses null/missing fields safely', () {
    final summary = TodayPriceSummary.fromJson({
      'date': '2026-05-19',
      'total_records': '12',
      'summary_text': null,
      'regions': {'广东': {'count': 5}},
      'anomalies': null,
    });

    expect(summary.totalRecords, 12);
    expect(summary.summaryText, '');
    expect(summary.regions['广东'], isA<Map>());
    expect(summary.anomalies, isEmpty);
  });

  test('ScaffoldBidCase.fromJson parses snake_case fields safely', () {
    final bid = ScaffoldBidCase.fromJson({
      'id': '10',
      'project_name': '脚手架租赁项目',
      'province': '广东',
      'city': null,
      'bid_amount': '12345.67',
      'area_m2': '1000',
      'rental_days': '30',
      'source_url': 'https://example.com/bid/10',
      'publish_date': '2026-05-19',
      'review_status': 'pending',
      'missing_fields': null,
      'raw_evidence_snippets': ['证据'],
      'extraction_confidence': '0.82',
    });

    expect(bid.id, 10);
    expect(bid.bidAmount, 12345.67);
    expect(bid.areaM2, 1000);
    expect(bid.rentalDays, 30);
    expect(bid.missingFields, isEmpty);
    expect(bid.rawEvidenceSnippets, ['证据']);
  });

  test('RegionalPriceItem.fromJson exists but remains unused when backend route is absent', () {
    final item = RegionalPriceItem.fromJson({
      'province': '广东',
      'city': null,
      'product_name': '盘扣脚手架',
      'avg_price': '12.5',
      'sample_count': '3',
      'latest_date': '2026-05-19',
    });

    expect(item.province, '广东');
    expect(item.avgPrice, 12.5);
    expect(item.sampleCount, 3);
  });

  test('Operational models parse missing/null fields without crashing', () {
    final attachment = Attachment.fromJson({'id': '1', 'file_name': 'a.pdf'});
    expect(attachment.id, 1);
    expect(attachment.fileName, 'a.pdf');

    final notification = NotificationLog.fromJson({'id': '2', 'status': 'sent'});
    expect(notification.id, 2);
    expect(notification.status, 'sent');
  });
}
