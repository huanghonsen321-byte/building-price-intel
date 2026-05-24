import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => statusCode == null ? message : '[${statusCode}] $message';
}

class ApiClient {
  ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? defaultBaseUrl {
    dio = Dio(
      BaseOptions(
        baseUrl: this.baseUrl,
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 12),
      ),
    );
  }

  static const configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  static String get defaultBaseUrl {
    if (configuredBaseUrl.isNotEmpty) return configuredBaseUrl;
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:9000';
    }
    return 'http://127.0.0.1:9000';
  }

  final String baseUrl;
  late final Dio dio;

  Future<HealthStatus> health() async => HealthStatus.fromJson(
    (await dio.get('/api/health')).data as Map<String, dynamic>,
  );

  Future<List<PriceDaily>> todayPrices() async {
    final data = (await dio.get('/api/prices/today')).data as List;
    return data
        .whereType<Map<String, dynamic>>()
        .map(PriceDaily.fromJson)
        .toList();
  }

  Future<TodayPriceSummary> todaySummary() async => TodayPriceSummary.fromJson(
    (await dio.get('/api/prices/today/summary')).data as Map<String, dynamic>,
  );

  Future<PageResult<PriceDaily>> prices({
    String? category,
    String? region,
    String? city,
    String? productName,
    int page = 1,
    int pageSize = 20,
  }) async {
    return _getPaged(
      '/api/prices',
      PriceDaily.fromJson,
      queryParameters: _clean({
        'category': category,
        'region': region,
        'city': city,
        'product_name': productName,
        'page': page,
        'page_size': pageSize,
      }),
    );
  }

  Future<List<PriceTrendPoint>> trends({
    String category = 'steel',
    String? productName,
    int days = 30,
  }) async {
    final data =
        (await dio.get(
              '/api/prices/trends',
              queryParameters: _clean({
                'category': category,
                'product_name': productName,
                'days': days,
              }),
            )).data
            as List;
    return data
        .whereType<Map<String, dynamic>>()
        .map(PriceTrendPoint.fromJson)
        .toList();
  }

  Future<PageResult<ScaffoldBidCase>> scaffoldBids({
    String? keyword,
    String? province,
    String? city,
    String? scaffoldType,
    String? procurementType,
    String? reviewStatus,
    int page = 1,
    int pageSize = 20,
  }) async {
    return _getPaged(
      '/api/scaffold/bids',
      ScaffoldBidCase.fromJson,
      queryParameters: _clean({
        'keyword': keyword,
        'province': province,
        'city': city,
        'scaffold_type': scaffoldType,
        'procurement_type': procurementType,
        'review_status': reviewStatus,
        'page': page,
        'page_size': pageSize,
      }),
    );
  }

  Future<void> reviewBidCase(
    int caseId, {
    required String status,
    String? reviewerNote,
  }) async {
    await dio.post(
      '/api/scaffold/bids/$caseId/review',
      data: _clean({'status': status, 'reviewer_note': reviewerNote}),
    );
  }

  Future<PageResult<ScaffoldPriceReference>> scaffoldReferences({
    String? region,
    String? scaffoldType,
    String? calculatedUnit,
    String? confidence,
    int page = 1,
    int pageSize = 20,
  }) async {
    return _getPaged(
      '/api/scaffold/prices/reference',
      ScaffoldPriceReference.fromJson,
      queryParameters: _clean({
        'region': region,
        'scaffold_type': scaffoldType,
        'calculated_unit': calculatedUnit,
        'confidence': confidence,
        'page': page,
        'page_size': pageSize,
      }),
    );
  }

  Future<ScaffoldQuoteResult> calculateQuote({
    String scaffoldType = '盘扣',
    String? region,
    String? pricingMethod,
    double? areaM2,
    double? rentalDays,
    double? rentalMonths,
    double? tonnage,
    double? setupDismantleFee,
    double? transportFee,
    double? lossRate,
    double? taxRate,
    double? profitRate,
    double? fixedTotalPrice,
  }) async {
    final res = await dio.post(
      '/api/quote/scaffold/calculate',
      data: _clean({
        'scaffold_type': scaffoldType,
        'region': region,
        'pricing_method': pricingMethod,
        'area_m2': areaM2,
        'rental_days': rentalDays,
        'rental_months': rentalMonths,
        'tonnage': tonnage,
        'setup_dismantle_fee': setupDismantleFee,
        'transport_fee': transportFee,
        'loss_rate': lossRate,
        'tax_rate': taxRate,
        'profit_rate': profitRate,
        'fixed_total_price': fixedTotalPrice,
      }),
    );
    return ScaffoldQuoteResult.fromJson(res.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> _getJsonMap(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final res = await dio.get(path, queryParameters: queryParameters);
      return res.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  Future<PageResult<T>> _getPaged<T>(
    String path,
    T Function(Map<String, dynamic>) fromJson, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final map = await _getJsonMap(path, queryParameters: queryParameters);
    return PageResult.fromJson(map, fromJson);
  }

  ApiException _mapError(DioException error) {
    final code = error.response?.statusCode;
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final msg = data['detail'] ?? data['message'] ?? data['error'];
      if (msg != null && msg.toString().isNotEmpty) {
        return ApiException(msg.toString(), statusCode: code);
      }
    }
    return ApiException(error.message ?? '网络请求失败', statusCode: code);
  }

  Map<String, dynamic> _clean(Map<String, dynamic> input) => Map.fromEntries(
    input.entries.where(
      (e) => e.value != null && e.value.toString().isNotEmpty,
    ),
  );

  Future<IngestStatusOverview> ingestStatusOverview() async =>
      IngestStatusOverview.fromJson(
        await _getJsonMap('/api/ingest/status'),
      );

  // ---- Crawl orchestrator ----

  Future<CrawlOrchestratorHealth> crawlOrchestratorHealth() async =>
      CrawlOrchestratorHealth.fromJson(
        (await dio.get('/api/crawl-orchestrator/health')).data
            as Map<String, dynamic>,
      );

  Future<List<CrawlRunSource>> crawlOrchestratorFailures({int limit = 30}) async {
    final data =
        (await dio.get('/api/crawl-orchestrator/failures', queryParameters: {'limit': limit})).data
            as List;
    return data
        .whereType<Map<String, dynamic>>()
        .map(CrawlRunSource.fromJson)
        .toList();
  }

  Future<PageResult<CrawlRun>> crawlOrchestratorRuns({
    int page = 1,
    int pageSize = 20,
  }) async {
    return _getPaged(
      '/api/crawl-orchestrator/runs',
      CrawlRun.fromJson,
      queryParameters: _clean({'page': page, 'page_size': pageSize}),
    );
  }

  Future<CrawlRunDetail> crawlOrchestratorRunDetail(int id) async =>
      CrawlRunDetail.fromJson(
        (await dio.get('/api/crawl-orchestrator/runs/$id')).data
            as Map<String, dynamic>,
      );

  Future<CrawlRunDetail> crawlOrchestratorLatest() async =>
      CrawlRunDetail.fromJson(
        (await dio.get('/api/crawl-orchestrator/latest')).data
            as Map<String, dynamic>,
      );
}
