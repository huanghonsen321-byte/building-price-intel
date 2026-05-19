class PageResult<T> {
  const PageResult({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final List<T> items;
  final int total;
  final int page;
  final int pageSize;

  factory PageResult.fromJson(
    Map<String, dynamic> json,
    T Function(Map<String, dynamic>) fromJson,
  ) {
    return PageResult<T>(
      items: ((json['items'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(fromJson)
          .toList(),
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

class TodayPriceSummary {
  const TodayPriceSummary({
    required this.date,
    required this.totalRecords,
    required this.summaryText,
    required this.regions,
    required this.anomalies,
    required this.updatedAt,
  });
  final DateTime? date;
  final int totalRecords;
  final String summaryText;
  final Map<String, dynamic> regions;
  final List<Map<String, dynamic>> anomalies;
  final DateTime? updatedAt;
  factory TodayPriceSummary.fromJson(Map<String, dynamic> json) =>
      TodayPriceSummary(
        date: _asDate(json['date']),
        totalRecords: _asInt(json['total_records']),
        summaryText: json['summary_text']?.toString() ?? '',
        regions:
            (json['regions'] as Map?)?.map(
              (key, value) => MapEntry(key.toString(), value),
            ) ??
            const {},
        anomalies: ((json['anomalies'] as List?) ?? const [])
            .whereType<Map>()
            .map((e) => e.map((key, value) => MapEntry(key.toString(), value)))
            .toList(),
        updatedAt: _asDate(json['updated_at']),
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
  const PriceTrendPoint({
    required this.date,
    required this.price,
    required this.productName,
    required this.region,
    required this.city,
    required this.unit,
  });
  final DateTime? date;
  final double price;
  final String productName;
  final String region;
  final String? city;
  final String unit;
  factory PriceTrendPoint.fromJson(Map<String, dynamic> json) =>
      PriceTrendPoint(
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
    required this.aiSummary,
    required this.missingFields,
    required this.rawEvidenceSnippets,
    required this.extractionConfidence,
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
  final String? aiSummary;
  final List<String> missingFields;
  final List<String> rawEvidenceSnippets;
  final double extractionConfidence;

  factory ScaffoldBidCase.fromJson(Map<String, dynamic> json) =>
      ScaffoldBidCase(
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
        aiSummary: _asString(json['ai_summary']),
        missingFields: _asStringList(json['missing_fields']),
        rawEvidenceSnippets: _asStringList(json['raw_evidence_snippets']),
        extractionConfidence: _asDouble(json['extraction_confidence']),
      );
}

class ScaffoldPriceReference {
  const ScaffoldPriceReference({
    required this.id,
    required this.bidCaseId,
    required this.priceType,
    required this.scaffoldType,
    required this.region,
    required this.calculatedUnit,
    required this.calculatedPrice,
    required this.formula,
    required this.confidence,
    required this.notes,
  });
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
  factory ScaffoldPriceReference.fromJson(Map<String, dynamic> json) =>
      ScaffoldPriceReference(
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

class ScaffoldQuoteCostBreakdown {
  const ScaffoldQuoteCostBreakdown({
    required this.baseRentalFee,
    required this.setupDismantleFee,
    required this.transportFee,
    required this.lossFee,
    required this.subtotalBeforeTaxProfit,
    required this.taxFee,
    required this.profitFee,
    required this.totalAmount,
  });
  final double baseRentalFee;
  final double setupDismantleFee;
  final double transportFee;
  final double lossFee;
  final double subtotalBeforeTaxProfit;
  final double taxFee;
  final double profitFee;
  final double totalAmount;
  factory ScaffoldQuoteCostBreakdown.fromJson(Map<String, dynamic>? json) =>
      ScaffoldQuoteCostBreakdown(
        baseRentalFee: _asDouble(json?['base_rental_fee']),
        setupDismantleFee: _asDouble(json?['setup_dismantle_fee']),
        transportFee: _asDouble(json?['transport_fee']),
        lossFee: _asDouble(json?['loss_fee']),
        subtotalBeforeTaxProfit: _asDouble(json?['subtotal_before_tax_profit']),
        taxFee: _asDouble(json?['tax_fee']),
        profitFee: _asDouble(json?['profit_fee']),
        totalAmount: _asDouble(json?['total_amount']),
      );
}

class ScaffoldQuoteResult {
  const ScaffoldQuoteResult({
    required this.scaffoldType,
    required this.region,
    required this.pricingMethod,
    required this.calculatedUnit,
    required this.referencePrice,
    required this.estimatedAmount,
    required this.unitAreaPrice,
    required this.unitTonDayPrice,
    required this.costBreakdown,
    required this.confidence,
    required this.formula,
    required this.referenceCount,
  });
  final String scaffoldType;
  final String? region;
  final String pricingMethod;
  final String calculatedUnit;
  final double referencePrice;
  final double? estimatedAmount;
  final double? unitAreaPrice;
  final double? unitTonDayPrice;
  final ScaffoldQuoteCostBreakdown costBreakdown;
  final String confidence;
  final String formula;
  final int referenceCount;
  factory ScaffoldQuoteResult.fromJson(Map<String, dynamic> json) =>
      ScaffoldQuoteResult(
        scaffoldType: json['scaffold_type']?.toString() ?? '',
        region: _asString(json['region']),
        pricingMethod: json['pricing_method']?.toString() ?? '',
        calculatedUnit: json['calculated_unit']?.toString() ?? '',
        referencePrice: _asDouble(json['reference_price']),
        estimatedAmount: _asNullableDouble(json['estimated_amount']),
        unitAreaPrice: _asNullableDouble(json['unit_area_price']),
        unitTonDayPrice: _asNullableDouble(json['unit_ton_day_price']),
        costBreakdown: ScaffoldQuoteCostBreakdown.fromJson(
          json['cost_breakdown'] as Map<String, dynamic>?,
        ),
        confidence: json['confidence']?.toString() ?? '',
        formula: json['formula']?.toString() ?? '',
        referenceCount: _asInt(json['reference_count']),
      );
}

String? _asString(Object? value) => value?.toString();
List<String> _asStringList(Object? value) =>
    value is List ? value.map((e) => e.toString()).toList() : const [];
int _asInt(Object? value, {int fallback = 0}) =>
    value is int ? value : int.tryParse(value?.toString() ?? '') ?? fallback;
int? _asNullableInt(Object? value) => int.tryParse(value?.toString() ?? '');
double _asDouble(Object? value, {double fallback = 0}) => value is num
    ? value.toDouble()
    : double.tryParse(value?.toString() ?? '') ?? fallback;
double? _asNullableDouble(Object? value) =>
    value is num ? value.toDouble() : double.tryParse(value?.toString() ?? '');
DateTime? _asDate(Object? value) => DateTime.tryParse(value?.toString() ?? '');
bool _asBool(Object? value) {
  if (value is bool) return value;
  final text = value?.toString().toLowerCase();
  return text == 'true' || text == '1' || text == 'yes';
}
Map<String, int> _asIntMap(Object? value) =>
    (value as Map?)?.map((key, val) => MapEntry(key.toString(), _asInt(val))) ??
    const {};

// ---------------------------------------------------------------------------
// Crawl orchestrator models
// ---------------------------------------------------------------------------

class CrawlOrchestratorHealth {
  const CrawlOrchestratorHealth({
    required this.totalRuns,
    required this.latestRun,
    required this.latestStatus,
  });
  final int totalRuns;
  final int? latestRun;
  final String latestStatus;
  factory CrawlOrchestratorHealth.fromJson(Map<String, dynamic> json) =>
      CrawlOrchestratorHealth(
        totalRuns: _asInt(json['total_runs']),
        latestRun: _asNullableInt(json['latest_run']),
        latestStatus: json['latest_status']?.toString() ?? 'no_runs',
      );
}

class CrawlRun {
  const CrawlRun({
    required this.id,
    required this.runType,
    required this.status,
    required this.startedAt,
    required this.finishedAt,
    required this.totalSources,
    required this.totalFound,
    required this.totalSaved,
    required this.totalAttachments,
    required this.totalAiExtracted,
    required this.totalReviewTasks,
    required this.notificationStatus,
    required this.errorMessage,
    required this.createdAt,
  });
  final int id;
  final String runType;
  final String status;
  final DateTime? startedAt;
  final DateTime? finishedAt;
  final int totalSources;
  final int totalFound;
  final int totalSaved;
  final int totalAttachments;
  final int totalAiExtracted;
  final int totalReviewTasks;
  final String? notificationStatus;
  final String? errorMessage;
  final DateTime? createdAt;
  bool get hasDuplicateSkippedSignal =>
      status != 'failed' && errorMessage == null && totalFound > 0 && totalSaved == 0;
  factory CrawlRun.fromJson(Map<String, dynamic> json) => CrawlRun(
    id: _asInt(json['id']),
    runType: json['run_type']?.toString() ?? '',
    status: json['status']?.toString() ?? '',
    startedAt: _asDate(json['started_at']),
    finishedAt: _asDate(json['finished_at']),
    totalSources: _asInt(json['total_sources']),
    totalFound: _asInt(json['total_found']),
    totalSaved: _asInt(json['total_saved']),
    totalAttachments: _asInt(json['total_attachments']),
    totalAiExtracted: _asInt(json['total_ai_extracted']),
    totalReviewTasks: _asInt(json['total_review_tasks']),
    notificationStatus: _asString(json['notification_status']),
    errorMessage: _asString(json['error_message']),
    createdAt: _asDate(json['created_at']),
  );
}

class CrawlRunSource {
  const CrawlRunSource({
    required this.id,
    required this.sourceName,
    required this.province,
    required this.city,
    required this.status,
    required this.blockedReason,
    required this.totalFound,
    required this.totalSaved,
    required this.errorMessage,
    required this.durationMs,
  });
  final int id;
  final String sourceName;
  final String? province;
  final String? city;
  final String status;
  final String? blockedReason;
  final int totalFound;
  final int totalSaved;
  final String? errorMessage;
  final int? durationMs;
  factory CrawlRunSource.fromJson(Map<String, dynamic> json) =>
      CrawlRunSource(
        id: _asInt(json['id']),
        sourceName: json['source_name']?.toString() ?? '',
        province: _asString(json['province']),
        city: _asString(json['city']),
        status: json['status']?.toString() ?? '',
        blockedReason: _asString(json['blocked_reason']),
        totalFound: _asInt(json['total_found']),
        totalSaved: _asInt(json['total_saved']),
        errorMessage: _asString(json['error_message']),
        durationMs: _asNullableInt(json['duration_ms']),
      );
}

class CrawlRunDetail {
  const CrawlRunDetail({required this.run, required this.sources});
  final CrawlRun run;
  final List<CrawlRunSource> sources;
  factory CrawlRunDetail.fromJson(Map<String, dynamic> json) =>
      CrawlRunDetail(
        run: CrawlRun.fromJson(json['run'] as Map<String, dynamic>),
        sources: ((json['sources'] as List?) ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(CrawlRunSource.fromJson)
            .toList(),
      );
}


class SourceLibraryStats {
  const SourceLibraryStats({
    required this.totalSources,
    required this.enabledSources,
    required this.parserReadySources,
    required this.blockedSources,
    required this.nationalSources,
    required this.guangdongSources,
    required this.provinceSourceCount,
    required this.citySourceCount,
    required this.priceSourceCount,
    required this.attachmentSourceCount,
    required this.manualImportSources,
    required this.authorizedApiSources,
    required this.byAcquisitionMethod,
    required this.byParserStatus,
  });
  final int totalSources;
  final int enabledSources;
  final int parserReadySources;
  final int blockedSources;
  final int nationalSources;
  final int guangdongSources;
  final int provinceSourceCount;
  final int citySourceCount;
  final int priceSourceCount;
  final int attachmentSourceCount;
  final int manualImportSources;
  final int authorizedApiSources;
  final Map<String, int> byAcquisitionMethod;
  final Map<String, int> byParserStatus;
  factory SourceLibraryStats.fromJson(Map<String, dynamic> json) =>
      SourceLibraryStats(
        totalSources: _asInt(json['total_sources']),
        enabledSources: _asInt(json['enabled_sources']),
        parserReadySources: _asInt(json['parser_ready_sources']),
        blockedSources: _asInt(json['blocked_sources']),
        nationalSources: _asInt(json['national_sources']),
        guangdongSources: _asInt(json['guangdong_sources']),
        provinceSourceCount: _asInt(json['province_source_count']),
        citySourceCount: _asInt(json['city_source_count']),
        priceSourceCount: _asInt(json['price_source_count']),
        attachmentSourceCount: _asInt(json['attachment_source_count']),
        manualImportSources: _asInt(json['manual_import_sources']),
        authorizedApiSources: _asInt(json['authorized_api_sources']),
        byAcquisitionMethod: _asIntMap(json['by_acquisition_method']),
        byParserStatus: _asIntMap(json['by_parser_status']),
      );
}

class SourceLibraryItem {
  const SourceLibraryItem({
    required this.name,
    required this.url,
    required this.domain,
    required this.sourceLevel,
    required this.sourceType,
    required this.acquisitionMethod,
    required this.keywords,
    required this.parserName,
    required this.enabled,
    required this.parserStatus,
    required this.requiresBrowser,
    required this.requiresManualReview,
    required this.reliabilityScore,
    required this.province,
    required this.city,
    required this.publicApiFound,
    required this.publicPageReachable,
    required this.lastSuccessAt,
    required this.lastBlockedReason,
    required this.tags,
    required this.notes,
  });
  final String name;
  final String url;
  final String domain;
  final String sourceLevel;
  final String sourceType;
  final String acquisitionMethod;
  final List<String> keywords;
  final String? parserName;
  final bool enabled;
  final String parserStatus;
  final bool requiresBrowser;
  final bool requiresManualReview;
  final double reliabilityScore;
  final String? province;
  final String? city;
  final bool publicApiFound;
  final bool publicPageReachable;
  final DateTime? lastSuccessAt;
  final String? lastBlockedReason;
  final List<String> tags;
  final String notes;
  factory SourceLibraryItem.fromJson(Map<String, dynamic> json) =>
      SourceLibraryItem(
        name: json['name']?.toString() ?? '',
        url: json['url']?.toString() ?? '',
        domain: json['domain']?.toString() ?? '',
        sourceLevel: json['source_level']?.toString() ?? '',
        sourceType: json['source_type']?.toString() ?? '',
        acquisitionMethod: json['acquisition_method']?.toString() ?? '',
        keywords: _asStringList(json['keywords']),
        parserName: _asString(json['parser_name']),
        enabled: _asBool(json['enabled']),
        parserStatus: json['parser_status']?.toString() ?? '',
        requiresBrowser: _asBool(json['requires_browser']),
        requiresManualReview: _asBool(json['requires_manual_review']),
        reliabilityScore: _asDouble(json['reliability_score']),
        province: _asString(json['province']),
        city: _asString(json['city']),
        publicApiFound: _asBool(json['public_api_found']),
        publicPageReachable: _asBool(json['public_page_reachable']),
        lastSuccessAt: _asDate(json['last_success_at']),
        lastBlockedReason: _asString(json['last_blocked_reason']),
        tags: _asStringList(json['tags']),
        notes: json['notes']?.toString() ?? '',
      );
}

class CrawlDashboardSummary {
  const CrawlDashboardSummary({
    required this.blockedSourceCount,
    required this.blockedReasonDistribution,
    required this.availableSourceCount,
    required this.todaySuccessfulSourceCount,
    required this.guangdongSuccessRate,
    required this.nationalSuccessRate,
    required this.sourceLibraryStats,
  });
  final int blockedSourceCount;
  final Map<String, int> blockedReasonDistribution;
  final int availableSourceCount;
  final int todaySuccessfulSourceCount;
  final double guangdongSuccessRate;
  final double nationalSuccessRate;
  final SourceLibraryStats sourceLibraryStats;
  factory CrawlDashboardSummary.fromJson(Map<String, dynamic> json) =>
      CrawlDashboardSummary(
        blockedSourceCount: _asInt(json['blocked_source_count']),
        blockedReasonDistribution: _asIntMap(json['blocked_reason_distribution']),
        availableSourceCount: _asInt(json['available_source_count']),
        todaySuccessfulSourceCount: _asInt(json['today_successful_source_count']),
        guangdongSuccessRate: _asDouble(json['guangdong_success_rate']),
        nationalSuccessRate: _asDouble(json['national_success_rate']),
        sourceLibraryStats: SourceLibraryStats.fromJson(
          (json['source_library_stats'] as Map?)?.map((k, v) => MapEntry(k.toString(), v)) ?? const {},
        ),
      );
}

class Attachment {
  const Attachment({
    required this.id,
    required this.rawDocumentId,
    required this.sourceUrl,
    required this.fileUrl,
    required this.fileName,
    required this.fileType,
    required this.fileSize,
    required this.localPath,
    required this.parseStatus,
    required this.errorMessage,
    required this.createdAt,
    required this.updatedAt,
  });
  final int id;
  final int? rawDocumentId;
  final String sourceUrl;
  final String fileUrl;
  final String fileName;
  final String fileType;
  final int? fileSize;
  final String? localPath;
  final String parseStatus;
  final String? errorMessage;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  factory Attachment.fromJson(Map<String, dynamic> json) => Attachment(
    id: _asInt(json['id']),
    rawDocumentId: _asNullableInt(json['raw_document_id']),
    sourceUrl: json['source_url']?.toString() ?? '',
    fileUrl: json['file_url']?.toString() ?? '',
    fileName: json['file_name']?.toString() ?? '',
    fileType: json['file_type']?.toString() ?? '',
    fileSize: _asNullableInt(json['file_size']),
    localPath: _asString(json['local_path']),
    parseStatus: json['parse_status']?.toString() ?? '',
    errorMessage: _asString(json['error_message']),
    createdAt: _asDate(json['created_at']),
    updatedAt: _asDate(json['updated_at']),
  );
}

class NotificationLog {
  const NotificationLog({
    required this.id,
    required this.eventType,
    required this.channel,
    required this.target,
    required this.status,
    required this.message,
    required this.errorMessage,
    required this.retryCount,
    required this.createdAt,
  });
  final int id;
  final String eventType;
  final String channel;
  final String? target;
  final String status;
  final String? message;
  final String? errorMessage;
  final int retryCount;
  final DateTime? createdAt;
  factory NotificationLog.fromJson(Map<String, dynamic> json) => NotificationLog(
    id: _asInt(json['id']),
    eventType: json['event_type']?.toString() ?? '',
    channel: json['channel']?.toString() ?? '',
    target: _asString(json['target']),
    status: json['status']?.toString() ?? '',
    message: _asString(json['message']),
    errorMessage: _asString(json['error_message']),
    retryCount: _asInt(json['retry_count']),
    createdAt: _asDate(json['created_at']),
  );
}

class ManagedBrowserRun {
  const ManagedBrowserRun({
    required this.id,
    required this.sourceName,
    required this.keyword,
    required this.mode,
    required this.startedAt,
    required this.endedAt,
    required this.visitedUrls,
    required this.downloadedFiles,
    required this.recordsCreated,
    required this.attachmentsCreated,
    required this.blockedReason,
    required this.errorMessage,
    required this.createdAt,
  });
  final int id;
  final String sourceName;
  final String keyword;
  final String mode;
  final DateTime? startedAt;
  final DateTime? endedAt;
  final List<String> visitedUrls;
  final List<String> downloadedFiles;
  final int recordsCreated;
  final int attachmentsCreated;
  final String? blockedReason;
  final String? errorMessage;
  final DateTime? createdAt;
  factory ManagedBrowserRun.fromJson(Map<String, dynamic> json) => ManagedBrowserRun(
    id: _asInt(json['id']),
    sourceName: json['source_name']?.toString() ?? '',
    keyword: json['keyword']?.toString() ?? '',
    mode: json['mode']?.toString() ?? '',
    startedAt: _asDate(json['started_at']),
    endedAt: _asDate(json['ended_at']),
    visitedUrls: _asStringList(json['visited_urls']),
    downloadedFiles: _asStringList(json['downloaded_files']),
    recordsCreated: _asInt(json['records_created']),
    attachmentsCreated: _asInt(json['attachments_created']),
    blockedReason: _asString(json['blocked_reason']),
    errorMessage: _asString(json['error_message']),
    createdAt: _asDate(json['created_at']),
  );
}

class RegionalPriceItem {
  const RegionalPriceItem({
    required this.province,
    required this.city,
    required this.productName,
    required this.avgPrice,
    required this.sampleCount,
    required this.latestDate,
  });
  final String province;
  final String? city;
  final String productName;
  final double avgPrice;
  final int sampleCount;
  final DateTime? latestDate;
  factory RegionalPriceItem.fromJson(Map<String, dynamic> json) =>
      RegionalPriceItem(
        province: json['province']?.toString() ?? '',
        city: _asString(json['city']),
        productName: json['product_name']?.toString() ?? '',
        avgPrice: _asDouble(json['avg_price'] ?? json['price']),
        sampleCount: _asInt(json['sample_count'] ?? json['count']),
        latestDate: _asDate(json['latest_date'] ?? json['date']),
      );
}
