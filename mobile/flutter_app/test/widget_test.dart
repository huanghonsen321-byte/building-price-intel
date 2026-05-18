import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/api_client.dart';
import 'package:flutter_app/models.dart';

void main() {
  test('page result parses backend pagination contract', () {
    final page = PageResult<PriceDaily>.fromJson({
      'items': [
        {
          'id': 1,
          'date': '2026-05-18',
          'category': 'steel',
          'region': '华北',
          'city': '北京',
          'product_name': '螺纹钢',
          'unit': '元/吨',
          'price': '3560.00',
          'tax_included': true,
          'source_name': 'mock-seed',
        }
      ],
      'total': 1,
      'page': 1,
      'page_size': 20,
    }, PriceDaily.fromJson);

    expect(page.total, 1);
    expect(page.pageSize, 20);
    expect(page.items.single.productName, '螺纹钢');
    expect(page.items.single.price, 3560.0);
  });

  test('api client accepts explicit base url', () {
    final api = ApiClient(baseUrl: 'http://127.0.0.1:9000');
    expect(api.baseUrl, 'http://127.0.0.1:9000');
  });

  test('quote result parses decimal strings and nullable amount', () {
    final quote = ScaffoldQuoteResult.fromJson({
      'scaffold_type': '盘扣',
      'region': '呼和浩特',
      'calculated_unit': '元/㎡',
      'reference_price': '62.50',
      'estimated_amount': null,
      'confidence': 'medium',
      'formula': '缺少 area_m2，无法按 元/㎡ 估算',
      'reference_count': 1,
    });

    expect(quote.referencePrice, 62.5);
    expect(quote.estimatedAmount, isNull);
    expect(quote.referenceCount, 1);
  });
}
