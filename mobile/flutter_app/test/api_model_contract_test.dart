import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/models.dart';

void main() {
  test('CrawlRun.fromJson parses numbers, dates, and duplicate-skipped state', () {
    final run = CrawlRun.fromJson({
      'id': '8',
      'run_type': 'guangdong',
      'status': 'partial_success',
      'started_at': '2026-05-19T15:23:21',
      'finished_at': null,
      'total_sources': '3',
      'total_found': '8',
      'total_saved': '0',
      'total_attachments': null,
      'total_ai_extracted': '0',
      'total_review_tasks': 0,
      'notification_status': 'skipped',
      'error_message': null,
      'created_at': '2026-05-19T15:23:21',
    });

    expect(run.id, 8);
    expect(run.totalFound, 8);
    expect(run.totalSaved, 0);
    expect(run.hasDuplicateSkippedSignal, isTrue);
    expect(run.createdAt, isNotNull);
  });

  test('CrawlRunSource.fromJson tolerates missing and null fields', () {
    final source = CrawlRunSource.fromJson({
      'id': '22',
      'source_name': '广东省公共资源交易平台',
      'status': 'success',
      'total_found': '8',
      'total_saved': 8,
      'duration_ms': null,
    });

    expect(source.id, 22);
    expect(source.sourceName, '广东省公共资源交易平台');
    expect(source.totalFound, 8);
    expect(source.durationMs, isNull);
  });

  test('SourceLibraryStats.fromJson parses maps and missing fields safely', () {
    final stats = SourceLibraryStats.fromJson({
      'total_sources': '76',
      'enabled_sources': 9,
      'parser_ready_sources': '8',
      'blocked_sources': null,
      'national_sources': '7',
      'guangdong_sources': '26',
      'by_acquisition_method': {'public_api': 3},
      'by_parser_status': {'parser_ready': '8'},
    });

    expect(stats.totalSources, 76);
    expect(stats.blockedSources, 0);
    expect(stats.byAcquisitionMethod['public_api'], 3);
    expect(stats.byParserStatus['parser_ready'], 8);
  });

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
    final dashboard = CrawlDashboardSummary.fromJson({
      'blocked_source_count': '2',
      'blocked_reason_distribution': {'blocked_403': '1'},
      'available_source_count': 5,
      'today_successful_source_count': null,
      'guangdong_success_rate': '0.5',
      'national_success_rate': 1,
      'source_library_stats': {'total_sources': '76'},
    });
    expect(dashboard.blockedSourceCount, 2);
    expect(dashboard.blockedReasonDistribution['blocked_403'], 1);
    expect(dashboard.sourceLibraryStats.totalSources, 76);

    final attachment = Attachment.fromJson({'id': '1', 'file_name': 'a.pdf'});
    expect(attachment.id, 1);
    expect(attachment.fileName, 'a.pdf');

    final notification = NotificationLog.fromJson({'id': '2', 'status': 'sent'});
    expect(notification.id, 2);
    expect(notification.status, 'sent');

    final run = ManagedBrowserRun.fromJson({
      'id': '3',
      'source_name': '测试源',
      'visited_urls': null,
      'downloaded_files': ['a.pdf'],
    });
    expect(run.id, 3);
    expect(run.visitedUrls, isEmpty);
    expect(run.downloadedFiles, ['a.pdf']);
  });
}
