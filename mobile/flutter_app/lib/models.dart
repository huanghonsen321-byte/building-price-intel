
class PageResult<T> {
  const PageResult({required this.items, required this.total, required this.page, required this.pageSize});

  final List<T> items;
  final int total;
  final int page;
  final int pageSize;

  factory PageResult.fromJson(Map<String, dynamic> json, T Function(Map<String, dynamic>) fromJson) {
    return PageResult<T>(
      items: ((json['items'] as List?) ?? const []).whereType<Map<String, dynamic>>().map(fromJson).toList(),
      total: _asInt(json['total']),
      page: _asInt(json['page'], fallback: 1),
      pageSize: _asInt(json['page_size'], fallback: 20),
    );
  }
}

class HealthStatus {
  const HealthStatus({required this.status, required this.service});
  final String status;
  final String service;
  factory HealthStatus.fromJson(Map<String, dynamic> json) => HealthStatus(
        status: json['status']?.toString() ?? 'unknown',
        service: json['service']?.toString() ?? '',
      );
}

class PriceDaily {
  const PriceDaily({
    required this.id,
    required this.date,
    required this.category,
    required this.region,
    required this.city,
    required this.productName,
    required this.spec,
    required this.material,
    required this.unit,
    required this.price,
    required this.changeValue,
    required this.taxIncluded,
    required this.sourceName,
    required this.sourceUrl,
  });

  final int id;
  final DateTime? date;
  final String category;
  final String region;
  final String? city;
  final String productName;
  final String? spec;
  final String? material;
  final String unit;
  final double price;
  final double? changeValue;
  final bool taxIncluded;
  final String sourceName;
  final String? sourceUrl;

  factory PriceDaily.fromJson(Map<String, dynamic> json) => PriceDaily(
        id: _asInt(json['id']),
        date: _asDate(json['date']),
        category: json['category']?.toString() ?? '',
        region: json['region']?.toString() ?? '',
        city: _asString(json['city']),
        productName: json['product_name']?.toString() ?? '',
        spec: _asString(json['spec']),
        material: _asString(json['material']),
        unit: json['unit']?.toString() ?? '',
        price: _asDouble(json['price']),
        changeValue: _asNullableDouble(json['change_value']),
        taxIncluded: json['tax_included'] == true,
        sourceName: json['source_name']?.toString() ?? '',
        sourceUrl: _asString(json['source_url']),
      );
}

class PriceTrendPoint {
  const PriceTrendPoint({required this.date, required this.price, required this.productName, required this.region, required this.city, required this.unit});
  final DateTime? date;
  final double price;
  final String productName;
  final String region;
  final String? city;
  final String unit;
  factory PriceTrendPoint.fromJson(Map<String, dynamic> json) => PriceTrendPoint(
        date: _asDate(json['date']),
        price: _asDouble(json['price']),
        productName: json['product_name']?.toString() ?? '',
        region: json['region']?.toString() ?? '',
        city: _asString(json['city']),
        unit: json['unit']?.toString() ?? '',
      );
}

class ScaffoldBidCase {
  const ScaffoldBidCase({
    required this.id,
    required this.projectName,
    required this.province,
    required this.city,
    required this.buyer,
    required this.winner,
    required this.bidAmount,
    required this.scaffoldType,
    required this.procurementType,
    required this.areaM2,
    required this.tonnage,
    required this.rentalDays,
    required this.sourceUrl,
    required this.publishDate,
    required this.reviewStatus,
    required this.serviceScope,
  });

  final int id;
  final String projectName;
  final String? province;
  final String? city;
  final String? buyer;
  final String? winner;
  final double? bidAmount;
  final String? scaffoldType;
  final String? procurementType;
  final double? areaM2;
  final double? tonnage;
  final int? rentalDays;
  final String sourceUrl;
  final DateTime? publishDate;
  final String reviewStatus;
  final String? serviceScope;

  factory ScaffoldBidCase.fromJson(Map<String, dynamic> json) => ScaffoldBidCase(
        id: _asInt(json['id']),
        projectName: json['project_name']?.toString() ?? '',
        province: _asString(json['province']),
        city: _asString(json['city']),
        buyer: _asString(json['buyer']),
        winner: _asString(json['winner']),
        bidAmount: _asNullableDouble(json['bid_amount']),
        scaffoldType: _asString(json['scaffold_type']),
        procurementType: _asString(json['procurement_type']),
        areaM2: _asNullableDouble(json['area_m2']),
        tonnage: _asNullableDouble(json['tonnage']),
        rentalDays: _asNullableInt(json['rental_days']),
        sourceUrl: json['source_url']?.toString() ?? '',
        publishDate: _asDate(json['publish_date']),
        reviewStatus: json['review_status']?.toString() ?? '',
        serviceScope: _asString(json['service_scope']),
      );
}

class ScaffoldPriceReference {
  const ScaffoldPriceReference({required this.id, required this.bidCaseId, required this.priceType, required this.scaffoldType, required this.region, required this.calculatedUnit, required this.calculatedPrice, required this.formula, required this.confidence, required this.notes});
  final int id;
  final int bidCaseId;
  final String priceType;
  final String? scaffoldType;
  final String? region;
  final String calculatedUnit;
  final double calculatedPrice;
  final String formula;
  final String confidence;
  final String? notes;
  factory ScaffoldPriceReference.fromJson(Map<String, dynamic> json) => ScaffoldPriceReference(
        id: _asInt(json['id']),
        bidCaseId: _asInt(json['bid_case_id']),
        priceType: json['price_type']?.toString() ?? '',
        scaffoldType: _asString(json['scaffold_type']),
        region: _asString(json['region']),
        calculatedUnit: json['calculated_unit']?.toString() ?? '',
        calculatedPrice: _asDouble(json['calculated_price']),
        formula: json['formula']?.toString() ?? '',
        confidence: json['confidence']?.toString() ?? '',
        notes: _asString(json['notes']),
      );
}

class ScaffoldQuoteResult {
  const ScaffoldQuoteResult({required this.scaffoldType, required this.region, required this.calculatedUnit, required this.referencePrice, required this.estimatedAmount, required this.confidence, required this.formula, required this.referenceCount});
  final String scaffoldType;
  final String? region;
  final String calculatedUnit;
  final double referencePrice;
  final double? estimatedAmount;
  final String confidence;
  final String formula;
  final int referenceCount;
  factory ScaffoldQuoteResult.fromJson(Map<String, dynamic> json) => ScaffoldQuoteResult(
        scaffoldType: json['scaffold_type']?.toString() ?? '',
        region: _asString(json['region']),
        calculatedUnit: json['calculated_unit']?.toString() ?? '',
        referencePrice: _asDouble(json['reference_price']),
        estimatedAmount: _asNullableDouble(json['estimated_amount']),
        confidence: json['confidence']?.toString() ?? '',
        formula: json['formula']?.toString() ?? '',
        referenceCount: _asInt(json['reference_count']),
      );
}

String? _asString(Object? value) => value?.toString();
int _asInt(Object? value, {int fallback = 0}) => value is int ? value : int.tryParse(value?.toString() ?? '') ?? fallback;
int? _asNullableInt(Object? value) => int.tryParse(value?.toString() ?? '');
double _asDouble(Object? value, {double fallback = 0}) => value is num ? value.toDouble() : double.tryParse(value?.toString() ?? '') ?? fallback;
double? _asNullableDouble(Object? value) => value is num ? value.toDouble() : double.tryParse(value?.toString() ?? '');
DateTime? _asDate(Object? value) => DateTime.tryParse(value?.toString() ?? '');
