import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import 'api_client.dart';
import 'models.dart';
import 'feature/dashboard/ingest_status_page.dart';

void main() => runApp(const BuildingPriceApp());

class BuildingPriceApp extends StatelessWidget {
  const BuildingPriceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '建筑价格情报',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff1565c0)),
        useMaterial3: true,
      ),
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  final api = ApiClient();
  int selected = 0;

  @override
  Widget build(BuildContext context) {
    final pages = <_Destination>[
      _Destination('首页', Icons.home, HomePage(api: api)),
      _Destination(
        '钢材',
        Icons.stacked_line_chart,
        PriceListPage(api: api, title: '钢材价格', category: 'steel'),
      ),
      _Destination(
        '废钢',
        Icons.recycling,
        PriceListPage(api: api, title: '废钢价格', category: 'scrap'),
      ),
      _Destination(
        '脚手架',
        Icons.construction,
        PriceListPage(api: api, title: '脚手架价格', category: 'scaffold'),
      ),
      _Destination('中标案例', Icons.assignment_turned_in, BidCasesPage(api: api)),
      _Destination('参考价', Icons.price_change, ReferencesPage(api: api)),
      _Destination('趋势', Icons.show_chart, TrendsPage(api: api)),
      _Destination('报价', Icons.calculate, QuotePage(api: api)),
      _Destination('复核', Icons.fact_check, ReviewPage(api: api)),
      _Destination('区域', Icons.map, RegionDistributionPage(api: api)),
      _Destination('抓取状态', Icons.smart_toy, AutoCrawlDashboardPage(api: api)),
      _Destination('接入状态', Icons.monitor_heart, IngestStatusPage(api: api)),
      _Destination('失败源', Icons.error_outline, CrawlFailuresPage(api: api)),
      _Destination('运行历史', Icons.history, CrawlRunHistoryPage(api: api)),
    ];
    return Scaffold(
      appBar: AppBar(
        title: Text(pages[selected].label),
        actions: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Center(
              child: Text(
                api.baseUrl,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ),
          ),
        ],
      ),
      body: pages[selected].page,
      bottomNavigationBar: NavigationBar(
        selectedIndex: selected,
        onDestinationSelected: (i) => setState(() => selected = i),
        destinations: pages
            .map(
              (p) => NavigationDestination(icon: Icon(p.icon), label: p.label),
            )
            .toList(),
      ),
    );
  }
}

class _Destination {
  _Destination(this.label, this.icon, this.page);
  final String label;
  final IconData icon;
  final Widget page;
}

class LoadState<T> extends StatefulWidget {
  const LoadState({
    super.key,
    required this.loader,
    required this.builder,
    this.empty,
    this.isEmpty,
    this.padding = const EdgeInsets.all(12),
  });
  final Future<T> Function() loader;
  final Widget Function(
    BuildContext context,
    T data,
    Future<void> Function() refresh,
  )
  builder;
  final String? empty;
  final bool Function(T data)? isEmpty;
  final EdgeInsets padding;
  @override
  State<LoadState<T>> createState() => _LoadStateState<T>();
}

class _LoadStateState<T> extends State<LoadState<T>> {
  late Future<T> future;
  @override
  void initState() {
    super.initState();
    future = widget.loader();
  }

  Future<void> refresh() async => setState(() => future = widget.loader());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return RefreshIndicator(
            onRefresh: refresh,
            child: ListView(
              padding: widget.padding,
              children: [
                ErrorCard(message: snapshot.error.toString(), onRetry: refresh),
              ],
            ),
          );
        }
        final data = snapshot.data as T;
        if (widget.isEmpty?.call(data) == true) {
          return RefreshIndicator(
            onRefresh: refresh,
            child: ListView(
              padding: widget.padding,
              children: [EmptyCard(message: widget.empty ?? '暂无数据')],
            ),
          );
        }
        return widget.builder(context, data, refresh);
      },
    );
  }
}

class _HomeDashboardData {
  const _HomeDashboardData({
    required this.health,
    required this.prices,
    required this.summary,
    required this.importantBids,
    required this.crawlHealth,
    required this.latestRunDetail,
  });
  final HealthStatus health;
  final List<PriceDaily> prices;
  final TodayPriceSummary summary;
  final List<ScaffoldBidCase> importantBids;
  final CrawlOrchestratorHealth? crawlHealth;
  final CrawlRunDetail? latestRunDetail;
}

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.api});
  final ApiClient api;

  Future<_HomeDashboardData> _load() async {
    final results = await Future.wait<Object>([
      api.health(),
      api.todayPrices(),
      api.todaySummary(),
      api.scaffoldBids(keyword: '脚手架', pageSize: 5),
      api.crawlOrchestratorHealth().then((v) => v as CrawlOrchestratorHealth?).catchError((_) => null) as Future<Object>,
      api.crawlOrchestratorLatest().then((v) => v as CrawlRunDetail?).catchError((_) => null) as Future<Object>,
    ]);
    return _HomeDashboardData(
      health: results[0] as HealthStatus,
      prices: results[1] as List<PriceDaily>,
      summary: results[2] as TodayPriceSummary,
      importantBids: (results[3] as PageResult<ScaffoldBidCase>).items,
      crawlHealth: results[4] as CrawlOrchestratorHealth?,
      latestRunDetail: results[5] as CrawlRunDetail?,
    );
  }

  @override
  Widget build(BuildContext context) {
    return LoadState<_HomeDashboardData>(
      loader: _load,
      builder: (context, data, refresh) => RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            InfoCard(
              title: '后端状态',
              subtitle: '${data.health.service}: ${data.health.status}',
              icon: Icons.cloud_done,
            ),
            if (data.latestRunDetail != null)
              _CrawlStatusCard(detail: data.latestRunDetail!, api: api,),
            if (data.crawlHealth != null && data.latestRunDetail == null)
              InfoCard(
                title: '自动抓取',
                subtitle: '${data.crawlHealth!.totalRuns} 次运行, 最新: ${data.crawlHealth!.latestStatus}',
                icon: Icons.smart_toy,
              ),
            InfoCard(
              title: '今日行情摘要',
              subtitle: data.summary.summaryText,
              icon: Icons.summarize,
            ),
            _FreshnessCard(summary: data.summary, prices: data.prices),
            if (data.latestRunDetail != null) ...[
              const SizedBox(height: 8),
              Text('自动抓取快捷入口', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              _CrawlQuickLinks(api: api),
            ],
            const SizedBox(height: 8),
            Text('今日 KPI', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            _KpiGrid(prices: data.prices, summary: data.summary),
            const SizedBox(height: 8),
            Text('今日价格样本', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            if (data.prices.isEmpty) const EmptyCard(message: '今日暂无价格数据'),
            ...data.prices.take(6).map((p) => PriceCard(price: p)),
            const SizedBox(height: 8),
            Text('最新重要脚手架中标案例', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            if (data.importantBids.isEmpty) const EmptyCard(message: '暂无中标案例'),
            ...data.importantBids.map(
              (b) => BidCard(
                bid: b,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => BidDetailPage(bid: b)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({required this.prices, required this.summary});
  final List<PriceDaily> prices;
  final TodayPriceSummary summary;

  @override
  Widget build(BuildContext context) {
    final byCategory = <String, List<PriceDaily>>{};
    for (final price in prices) {
      byCategory.putIfAbsent(price.category, () => []).add(price);
    }
    final avg = prices.isEmpty
        ? 0.0
        : prices.map((e) => e.price).reduce((a, b) => a + b) / prices.length;
    final rising = prices.where((p) => (p.changeValue ?? 0) > 0).length;
    final cards = [
      _KpiCard(
        label: '今日记录',
        value: '${summary.totalRecords}',
        sub: '${byCategory.length} 个分类',
      ),
      _KpiCard(
        label: '均价样本',
        value: avg == 0 ? '-' : avg.toStringAsFixed(0),
        sub: '基于今日价格',
      ),
      _KpiCard(label: '上涨品类', value: '$rising', sub: 'change_value > 0'),
      _KpiCard(
        label: '异常波动',
        value: '${summary.anomalies.length}',
        sub: '≥100 元波动',
      ),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = (constraints.maxWidth - 8) / 2;
        return Wrap(
          spacing: 8,
          runSpacing: 8,
          children: cards
              .map(
                (card) => SizedBox(
                  width: width.clamp(150, 280).toDouble(),
                  child: card,
                ),
              )
              .toList(),
        );
      },
    );
  }
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({required this.label, required this.value, required this.sub});
  final String label;
  final String value;
  final String sub;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          Text(sub, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    ),
  );
}

class _FreshnessCard extends StatelessWidget {
  const _FreshnessCard({required this.summary, required this.prices});
  final TodayPriceSummary summary;
  final List<PriceDaily> prices;
  @override
  Widget build(BuildContext context) {
    final latestPriceDate = prices
        .map((p) => p.date)
        .whereType<DateTime>()
        .fold<DateTime?>(
          null,
          (latest, date) =>
              latest == null || date.isAfter(latest) ? date : latest,
        );
    final subtitle = [
      '行情日期：${fmtDate(summary.date ?? latestPriceDate)}',
      if (summary.updatedAt != null) '摘要更新：${fmtDateTime(summary.updatedAt)}',
      if (prices.isNotEmpty)
        '最新样本：${fmtDate(latestPriceDate)} · ${prices.length} 条',
    ].join('\n');
    return InfoCard(title: '数据新鲜度', subtitle: subtitle, icon: Icons.update);
  }
}

class PriceListPage extends StatefulWidget {
  const PriceListPage({
    super.key,
    required this.api,
    required this.title,
    required this.category,
  });
  final ApiClient api;
  final String title;
  final String category;
  @override
  State<PriceListPage> createState() => _PriceListPageState();
}

class _PriceListPageState extends State<PriceListPage> {
  final region = TextEditingController();
  final city = TextEditingController();
  final product = TextEditingController();
  int reload = 0;
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        FilterBar(
          children: [
            FilterField(controller: region, label: '区域'),
            FilterField(controller: city, label: '城市'),
            FilterField(controller: product, label: '品名'),
            FilledButton(
              onPressed: () => setState(() => reload++),
              child: const Text('筛选'),
            ),
          ],
        ),
        Expanded(
          child: LoadState<PageResult<PriceDaily>>(
            key: ValueKey('${widget.category}-$reload'),
            loader: () => widget.api.prices(
              category: widget.category,
              region: region.text,
              city: city.text,
              productName: product.text,
            ),
            isEmpty: (page) => page.items.isEmpty,
            builder: (context, page, refresh) => RefreshIndicator(
              onRefresh: refresh,
              child: ListView(
                padding: const EdgeInsets.all(12),
                children: [
                  PageSummary(page: page),
                  ...page.items.map((p) => PriceCard(price: p)),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class BidCasesPage extends StatefulWidget {
  const BidCasesPage({super.key, required this.api});
  final ApiClient api;
  @override
  State<BidCasesPage> createState() => _BidCasesPageState();
}

class _BidCasesPageState extends State<BidCasesPage> {
  final keyword = TextEditingController(text: '脚手架');
  final province = TextEditingController();
  final type = TextEditingController(text: '盘扣');
  final items = <ScaffoldBidCase>[];
  int page = 1;
  int total = 0;
  bool loading = false;
  String? error;

  @override
  void initState() {
    super.initState();
    load(reset: true);
  }

  Future<void> load({bool reset = false}) async {
    if (loading) return;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final nextPage = reset ? 1 : page + 1;
      final result = await widget.api.scaffoldBids(
        keyword: keyword.text,
        province: province.text,
        scaffoldType: type.text,
        page: nextPage,
        pageSize: 10,
      );
      setState(() {
        if (reset) items.clear();
        items.addAll(result.items);
        page = result.page;
        total = result.total;
      });
    } catch (e) {
      setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> openFilters() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('筛选中标案例', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            FilterField(controller: keyword, label: '关键词'),
            FilterField(controller: province, label: '省份'),
            FilterField(controller: type, label: '类型'),
            const SizedBox(height: 12),
            Row(
              children: [
                TextButton(
                  onPressed: () {
                    keyword.text = '脚手架';
                    province.clear();
                    type.clear();
                  },
                  child: const Text('清空筛选'),
                ),
                const Spacer(),
                FilledButton(
                  onPressed: () {
                    Navigator.pop(context);
                    load(reset: true);
                  },
                  child: const Text('应用'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.all(8),
        child: Row(
          children: [
            Expanded(
              child: Text(
                '共 $total 条 · ${keyword.text}${province.text.isEmpty ? '' : ' · ${province.text}'}',
                overflow: TextOverflow.ellipsis,
              ),
            ),
            OutlinedButton.icon(
              onPressed: openFilters,
              icon: const Icon(Icons.tune),
              label: const Text('筛选'),
            ),
          ],
        ),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: () => load(reset: true),
          child: ListView(
            padding: const EdgeInsets.all(12),
            children: [
              if (error != null)
                ErrorCard(message: error!, onRetry: () => load(reset: true)),
              if (!loading && error == null && items.isEmpty)
                const EmptyCard(message: '暂无该地区脚手架中标案例，可调整筛选条件'),
              ...items.map(
                (b) => BidCard(
                  bid: b,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => BidDetailPage(bid: b)),
                  ),
                ),
              ),
              if (items.length < total)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: FilledButton(
                    onPressed: loading ? null : () => load(),
                    child: Text(loading ? '加载中...' : '加载更多'),
                  ),
                ),
            ],
          ),
        ),
      ),
    ],
  );
}

class ReferencesPage extends StatefulWidget {
  const ReferencesPage({super.key, required this.api});
  final ApiClient api;
  @override
  State<ReferencesPage> createState() => _ReferencesPageState();
}

class _ReferencesPageState extends State<ReferencesPage> {
  final region = TextEditingController();
  final type = TextEditingController(text: '盘扣');
  final unit = TextEditingController();
  int reload = 0;
  @override
  Widget build(BuildContext context) => Column(
    children: [
      FilterBar(
        children: [
          FilterField(controller: region, label: '地区'),
          FilterField(controller: type, label: '类型'),
          FilterField(controller: unit, label: '单位'),
          FilledButton(
            onPressed: () => setState(() => reload++),
            child: const Text('筛选'),
          ),
        ],
      ),
      Expanded(
        child: LoadState<PageResult<ScaffoldPriceReference>>(
          key: ValueKey(reload),
          loader: () => widget.api.scaffoldReferences(
            region: region.text,
            scaffoldType: type.text,
            calculatedUnit: unit.text,
          ),
          isEmpty: (p) => p.items.isEmpty,
          builder: (context, page, refresh) => RefreshIndicator(
            onRefresh: refresh,
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                PageSummary(page: page),
                ...page.items.map((r) => ReferenceCard(ref: r)),
              ],
            ),
          ),
        ),
      ),
    ],
  );
}

class TrendsPage extends StatefulWidget {
  const TrendsPage({super.key, required this.api});
  final ApiClient api;
  @override
  State<TrendsPage> createState() => _TrendsPageState();
}

class TrendSeries {
  const TrendSeries({
    required this.category,
    required this.productName,
    required this.points,
  });
  final String category;
  final String productName;
  final List<PriceTrendPoint> points;
  String get label =>
      '${categoryLabel(category)}${productName.isEmpty ? '' : ' · $productName'}';
}

class _TrendsPageState extends State<TrendsPage> {
  final selectedCategories = <String>{'steel'};
  final product = TextEditingController();
  int days = 30;
  int reload = 0;

  Future<List<TrendSeries>> _load() async {
    final products = product.text
        .split(RegExp(r'[,，\n]'))
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final productFilters = products.isEmpty ? [''] : products;
    final requests = <Future<TrendSeries>>[];
    for (final category in selectedCategories) {
      for (final productName in productFilters) {
        requests.add(
          widget.api
              .trends(category: category, productName: productName, days: days)
              .then(
                (points) => TrendSeries(
                  category: category,
                  productName: productName,
                  points: points,
                ),
              ),
        );
      }
    }
    return Future.wait(requests);
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
        child: Align(
          alignment: Alignment.centerLeft,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final category in const ['steel', 'scrap', 'scaffold'])
                FilterChip(
                  label: Text(categoryLabel(category)),
                  selected: selectedCategories.contains(category),
                  onSelected: (selected) => setState(() {
                    if (selected) {
                      selectedCategories.add(category);
                    } else if (selectedCategories.length > 1) {
                      selectedCategories.remove(category);
                    }
                    reload++;
                  }),
                ),
              const SizedBox(width: 8),
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 7, label: Text('7天')),
                  ButtonSegment(value: 30, label: Text('30天')),
                  ButtonSegment(value: 90, label: Text('90天')),
                ],
                selected: {days},
                onSelectionChanged: (value) => setState(() {
                  days = value.single;
                  reload++;
                }),
              ),
            ],
          ),
        ),
      ),
      FilterBar(
        children: [
          SizedBox(
            width: 220,
            child: TextField(
              controller: product,
              decoration: const InputDecoration(
                labelText: '品名对比（逗号分隔，可空）',
                border: OutlineInputBorder(),
              ),
            ),
          ),
          FilledButton.icon(
            onPressed: () => setState(() => reload++),
            icon: const Icon(Icons.refresh),
            label: const Text('刷新'),
          ),
        ],
      ),
      Expanded(
        child: LoadState<List<TrendSeries>>(
          key: ValueKey('${selectedCategories.join(',')}-$days-$reload'),
          loader: _load,
          isEmpty: (series) => series.every((s) => s.points.isEmpty),
          builder: (context, series, refresh) {
            final nonEmpty = series.where((s) => s.points.isNotEmpty).toList();
            return RefreshIndicator(
              onRefresh: refresh,
              child: ListView(
                padding: const EdgeInsets.all(12),
                children: [
                  TrendLineChart(series: nonEmpty),
                  const SizedBox(height: 8),
                  ...nonEmpty.map((s) => _TrendSeriesList(series: s)),
                ],
              ),
            );
          },
        ),
      ),
    ],
  );
}

class _TrendSeriesList extends StatelessWidget {
  const _TrendSeriesList({required this.series});
  final TrendSeries series;
  @override
  Widget build(BuildContext context) {
    final sorted = [...series.points]
      ..sort(
        (a, b) =>
            (b.date ?? DateTime(1970)).compareTo(a.date ?? DateTime(1970)),
      );
    return Card(
      child: ExpansionTile(
        initiallyExpanded: true,
        title: Text(series.label),
        subtitle: Text(
          '${sorted.length} 个点 · 最新 ${sorted.isEmpty ? '-' : sorted.first.price.toStringAsFixed(2)} ${sorted.isEmpty ? '' : sorted.first.unit}',
        ),
        children: sorted
            .take(12)
            .map(
              (p) => ListTile(
                dense: true,
                leading: const Icon(Icons.timeline),
                title: Text('${fmtDate(p.date)}  ${p.productName}'),
                subtitle: Text('${p.region}${p.city ?? ''}'),
                trailing: Text('${p.price.toStringAsFixed(2)} ${p.unit}'),
              ),
            )
            .toList(),
      ),
    );
  }
}

class QuotePage extends StatefulWidget {
  const QuotePage({super.key, required this.api});
  final ApiClient api;
  @override
  State<QuotePage> createState() => _QuotePageState();
}

class _QuotePageState extends State<QuotePage> {
  final type = TextEditingController(text: '盘扣');
  final region = TextEditingController(text: '呼和浩特');
  final area = TextEditingController(text: '1000');
  final days = TextEditingController(text: '90');
  final months = TextEditingController();
  final tons = TextEditingController();
  final setupFee = TextEditingController();
  final transportFee = TextEditingController();
  final lossRate = TextEditingController(text: '0.02');
  final taxRate = TextEditingController(text: '0.09');
  final profitRate = TextEditingController(text: '0.12');
  final fixedTotal = TextEditingController();
  String pricingMethod = '元/㎡';
  ScaffoldQuoteResult? result;
  String? error;
  bool loading = false;

  double? _num(TextEditingController c) => double.tryParse(c.text);

  Future<void> submit() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      result = await widget.api.calculateQuote(
        scaffoldType: type.text,
        region: region.text,
        pricingMethod: pricingMethod,
        areaM2: _num(area),
        rentalDays: _num(days),
        rentalMonths: _num(months),
        tonnage: _num(tons),
        setupDismantleFee: _num(setupFee),
        transportFee: _num(transportFee),
        lossRate: _num(lossRate),
        taxRate: _num(taxRate),
        profitRate: _num(profitRate),
        fixedTotalPrice: _num(fixedTotal),
      );
    } catch (e) {
      error = e.toString();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(12),
    children: [
      FilterField(controller: type, label: '脚手架类型'),
      FilterField(controller: region, label: '地区'),
      DropdownButtonFormField<String>(
        initialValue: pricingMethod,
        decoration: const InputDecoration(
          labelText: '计价方式',
          border: OutlineInputBorder(),
        ),
        items: const [
          '元/㎡',
          '元/吨/天',
          '元/月',
          '总价折算',
        ].map((v) => DropdownMenuItem(value: v, child: Text(v))).toList(),
        onChanged: (v) => setState(() => pricingMethod = v ?? '元/㎡'),
      ),
      const SizedBox(height: 8),
      FilterField(
        controller: area,
        label: '面积㎡',
        keyboardType: TextInputType.number,
      ),
      FilterField(
        controller: days,
        label: '租赁天数',
        keyboardType: TextInputType.number,
      ),
      FilterField(
        controller: months,
        label: '租赁月数',
        keyboardType: TextInputType.number,
      ),
      FilterField(
        controller: tons,
        label: '吨数',
        keyboardType: TextInputType.number,
      ),
      const SizedBox(height: 8),
      ExpansionTile(
        title: const Text('高级成本项'),
        children: [
          FilterField(
            controller: setupFee,
            label: '搭拆费',
            keyboardType: TextInputType.number,
          ),
          FilterField(
            controller: transportFee,
            label: '运输费',
            keyboardType: TextInputType.number,
          ),
          FilterField(
            controller: lossRate,
            label: '损耗率(0.02)',
            keyboardType: TextInputType.number,
          ),
          FilterField(
            controller: taxRate,
            label: '税率(0.09)',
            keyboardType: TextInputType.number,
          ),
          FilterField(
            controller: profitRate,
            label: '利润率(0.12)',
            keyboardType: TextInputType.number,
          ),
          FilterField(
            controller: fixedTotal,
            label: '总价折算',
            keyboardType: TextInputType.number,
          ),
        ],
      ),
      const SizedBox(height: 12),
      FilledButton.icon(
        onPressed: loading ? null : submit,
        icon: const Icon(Icons.calculate),
        label: Text(loading ? '计算中...' : '计算报价'),
      ),
      if (error != null) ErrorCard(message: error!, onRetry: submit),
      if (result == null && error == null)
        const EmptyCard(message: '输入条件后点击计算'),
      if (result != null) QuoteResultCard(result: result!),
    ],
  );
}

class QuoteResultCard extends StatelessWidget {
  const QuoteResultCard({super.key, required this.result});
  final ScaffoldQuoteResult result;

  String get quoteText => [
    '脚手架报价测算',
    '类型：${result.scaffoldType}  地区：${result.region ?? '-'}',
    '计价方式：${result.pricingMethod}',
    '参考价：${result.referencePrice.toStringAsFixed(2)} ${result.calculatedUnit}',
    '估算金额：${result.estimatedAmount?.toStringAsFixed(2) ?? '参数不足'}',
    if (result.unitAreaPrice != null)
      '单方价：${result.unitAreaPrice!.toStringAsFixed(2)} 元/㎡',
    if (result.unitTonDayPrice != null)
      '吨日综合价：${result.unitTonDayPrice!.toStringAsFixed(2)} 元/吨/天',
    '置信度：${result.confidence} / 样本：${result.referenceCount}',
    '材料租赁费：${result.costBreakdown.baseRentalFee.toStringAsFixed(2)}',
    '搭拆费：${result.costBreakdown.setupDismantleFee.toStringAsFixed(2)}，运输费：${result.costBreakdown.transportFee.toStringAsFixed(2)}',
    '损耗：${result.costBreakdown.lossFee.toStringAsFixed(2)}，税费：${result.costBreakdown.taxFee.toStringAsFixed(2)}，利润：${result.costBreakdown.profitFee.toStringAsFixed(2)}',
    '公式：${result.formula}',
  ].join('\n');

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: quoteText));
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('报价文本已复制到剪贴板')));
    }
  }

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '估算结果',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              IconButton(
                tooltip: '复制报价文本',
                onPressed: () => _copy(context),
                icon: const Icon(Icons.copy),
              ),
            ],
          ),
          Text('计价方式：${result.pricingMethod}'),
          Text(
            '参考价：${result.referencePrice.toStringAsFixed(2)} ${result.calculatedUnit}',
          ),
          Text('估算金额：${result.estimatedAmount?.toStringAsFixed(2) ?? '参数不足'}'),
          if (result.unitAreaPrice != null)
            Text('单方价：${result.unitAreaPrice!.toStringAsFixed(2)} 元/㎡'),
          if (result.unitTonDayPrice != null)
            Text('吨日综合价：${result.unitTonDayPrice!.toStringAsFixed(2)} 元/吨/天'),
          Text('置信度：${result.confidence} / 样本：${result.referenceCount}'),
          const Divider(),
          Text('费用拆分', style: Theme.of(context).textTheme.titleMedium),
          Text(
            '材料租赁费：${result.costBreakdown.baseRentalFee.toStringAsFixed(2)}',
          ),
          Text(
            '搭拆费：${result.costBreakdown.setupDismantleFee.toStringAsFixed(2)} / 运输费：${result.costBreakdown.transportFee.toStringAsFixed(2)}',
          ),
          Text(
            '损耗：${result.costBreakdown.lossFee.toStringAsFixed(2)} / 税费：${result.costBreakdown.taxFee.toStringAsFixed(2)} / 利润：${result.costBreakdown.profitFee.toStringAsFixed(2)}',
          ),
          Text('公式：${result.formula}'),
          const Divider(),
          Row(
            children: [
              Expanded(
                child: Text(
                  '可复制报价文本',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              OutlinedButton.icon(
                onPressed: () => _copy(context),
                icon: const Icon(Icons.copy_all),
                label: const Text('复制'),
              ),
            ],
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: SelectableText(quoteText),
          ),
        ],
      ),
    ),
  );
}

class TrendLineChart extends StatelessWidget {
  const TrendLineChart({super.key, required this.series});
  final List<TrendSeries> series;

  @override
  Widget build(BuildContext context) {
    final allPoints = series.expand((s) => s.points).toList();
    if (allPoints.isEmpty) return const EmptyCard(message: '暂无趋势数据');
    final prices = allPoints.map((p) => p.price).toList();
    final minY = prices.reduce(math.min);
    final maxY = prices.reduce(math.max);
    final span = math.max(1.0, maxY - minY);
    final allDates =
        allPoints.map((p) => p.date).whereType<DateTime>().toSet().toList()
          ..sort();
    final dateIndex = {
      for (var i = 0; i < allDates.length; i++)
        DateFormat('yyyy-MM-dd').format(allDates[i]): i.toDouble(),
    };
    final palette = [
      Theme.of(context).colorScheme.primary,
      Colors.orange,
      Colors.green,
      Colors.purple,
      Colors.teal,
      Colors.redAccent,
    ];
    final bars = <LineChartBarData>[];
    for (var s = 0; s < series.length; s++) {
      final sorted = [...series[s].points]
        ..sort(
          (a, b) =>
              (a.date ?? DateTime(1970)).compareTo(b.date ?? DateTime(1970)),
        );
      final spots = sorted.map((p) {
        final key = p.date == null
            ? null
            : DateFormat('yyyy-MM-dd').format(p.date!);
        return FlSpot(dateIndex[key] ?? 0, p.price);
      }).toList();
      bars.add(
        LineChartBarData(
          spots: spots,
          isCurved: true,
          color: palette[s % palette.length],
          barWidth: 3,
          dotData: const FlDotData(show: true),
          belowBarData: BarAreaData(show: false),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 16, 18, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('多品类价格趋势对比', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 10,
              runSpacing: 6,
              children: [
                for (var i = 0; i < series.length; i++)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 10,
                        height: 10,
                        color: palette[i % palette.length],
                      ),
                      const SizedBox(width: 4),
                      Text(
                        series[i].label,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ],
                  ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 240,
              child: LineChart(
                LineChartData(
                  minY: minY - span * 0.08,
                  maxY: maxY + span * 0.08,
                  gridData: const FlGridData(show: true),
                  borderData: FlBorderData(show: true),
                  titlesData: FlTitlesData(
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: math
                            .max(1, (allDates.length / 4).floor())
                            .toDouble(),
                        getTitlesWidget: (value, meta) {
                          final i = value.round();
                          if (i < 0 || i >= allDates.length) {
                            return const SizedBox.shrink();
                          }
                          return Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Text(
                              DateFormat('MM-dd').format(allDates[i]),
                              style: const TextStyle(fontSize: 10),
                            ),
                          );
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 46,
                        getTitlesWidget: (value, meta) => Text(
                          value.toStringAsFixed(0),
                          style: const TextStyle(fontSize: 10),
                        ),
                      ),
                    ),
                  ),
                  lineBarsData: bars,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ReviewPage extends StatefulWidget {
  const ReviewPage({super.key, required this.api});
  final ApiClient api;
  @override
  State<ReviewPage> createState() => _ReviewPageState();
}

class _ReviewPageState extends State<ReviewPage> {
  int reload = 0;

  Future<void> _mark(ScaffoldBidCase bid, String status, String note) async {
    await widget.api.reviewBidCase(bid.id, status: status, reviewerNote: note);
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('案例 #${bid.id} 已标记为 $status')));
      setState(() => reload++);
    }
  }

  Future<void> _openReviewSheet(ScaffoldBidCase bid, String status) async {
    final note = TextEditingController(
      text: status == 'approved' ? '人工复核通过' : '人工已复核',
    );
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '复核案例 #${bid.id}',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            Text(bid.projectName),
            const SizedBox(height: 12),
            TextField(
              controller: note,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: '复核备注',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('取消'),
                ),
                const Spacer(),
                FilledButton(
                  onPressed: () {
                    Navigator.pop(context);
                    _mark(bid, status, note.text);
                  },
                  child: Text('标记 $status'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => LoadState<PageResult<ScaffoldBidCase>>(
    key: ValueKey(reload),
    loader: () =>
        widget.api.scaffoldBids(reviewStatus: 'pending', pageSize: 50),
    isEmpty: (page) => page.items.isEmpty,
    empty: '暂无 pending 低置信度复核任务',
    builder: (context, page, refresh) => RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          PageSummary(page: page),
          ...page.items.map(
            (bid) => _ReviewCaseCard(
              bid: bid,
              onReviewed: () => _openReviewSheet(bid, 'reviewed'),
              onApproved: () => _openReviewSheet(bid, 'approved'),
            ),
          ),
        ],
      ),
    ),
  );
}

class _ReviewCaseCard extends StatelessWidget {
  const _ReviewCaseCard({
    required this.bid,
    required this.onReviewed,
    required this.onApproved,
  });
  final ScaffoldBidCase bid;
  final VoidCallback onReviewed;
  final VoidCallback onApproved;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  bid.projectName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              Chip(
                label: Text(
                  '置信度 ${bid.extractionConfidence.toStringAsFixed(2)}',
                ),
              ),
            ],
          ),
          Text(
            '${bid.province ?? '-'}${bid.city ?? ''} · ${fmtDate(bid.publishDate)} · 状态 ${bid.reviewStatus}',
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: bid.missingFields.isEmpty
                ? [const Chip(label: Text('无缺失字段'))]
                : bid.missingFields
                      .map(
                        (f) => Chip(
                          label: Text('缺失 $f'),
                          backgroundColor: Theme.of(
                            context,
                          ).colorScheme.errorContainer,
                        ),
                      )
                      .toList(),
          ),
          const SizedBox(height: 8),
          Text('关键信息', style: Theme.of(context).textTheme.labelLarge),
          Text(
            '采购人：${bid.buyer ?? '-'} / 中标人：${bid.winner ?? '-'} / 金额：${bid.bidAmount == null ? '-' : '${(bid.bidAmount! / 10000).toStringAsFixed(2)}万'}',
          ),
          Text(
            '面积：${bid.areaM2?.toStringAsFixed(0) ?? '-'}㎡ / 吨位：${bid.tonnage?.toStringAsFixed(0) ?? '-'} / 租期：${bid.rentalDays ?? '-'}天',
          ),
          if ((bid.aiSummary ?? '').isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('AI 摘要：${bid.aiSummary}'),
            ),
          if (bid.rawEvidenceSnippets.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Evidence snippets',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            ...bid.rawEvidenceSnippets
                .take(3)
                .map(
                  (e) => Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: SelectableText('• $e'),
                  ),
                ),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: onReviewed,
                icon: const Icon(Icons.rate_review),
                label: const Text('标记 reviewed'),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: onApproved,
                icon: const Icon(Icons.check),
                label: const Text('approved'),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}

class RegionDistributionPage extends StatelessWidget {
  const RegionDistributionPage({super.key, required this.api});
  final ApiClient api;
  @override
  Widget build(BuildContext context) => LoadState<PageResult<ScaffoldBidCase>>(
    loader: () => api.scaffoldBids(pageSize: 100),
    isEmpty: (page) => page.items.isEmpty,
    empty: '暂无区域分布数据',
    builder: (context, page, refresh) {
      final stats = _buildRegionStats(page.items);
      return RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            Text(
              '区域分布（最近 ${page.items.length} 条）',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _PriorityRegionCard(title: '广东', stat: stats.priority('广东')),
                _PriorityRegionCard(
                  title: '华北',
                  stat: stats.group('华北', const ['北京', '天津', '河北', '山西']),
                ),
                _PriorityRegionCard(title: '内蒙古', stat: stats.priority('内蒙古')),
              ],
            ),
            const SizedBox(height: 12),
            Text('省份分布', style: Theme.of(context).textTheme.titleMedium),
            ...stats.provinces
                .take(12)
                .map(
                  (s) => _RegionBar(stat: s, maxCount: stats.maxProvinceCount),
                ),
            const SizedBox(height: 12),
            Text('城市 Top10', style: Theme.of(context).textTheme.titleMedium),
            ...stats.cities
                .take(10)
                .map((s) => _RegionBar(stat: s, maxCount: stats.maxCityCount)),
          ],
        ),
      );
    },
  );
}

class _RegionStats {
  _RegionStats({required this.provinces, required this.cities});
  final List<_RegionStat> provinces;
  final List<_RegionStat> cities;
  int get maxProvinceCount =>
      provinces.isEmpty ? 1 : provinces.map((e) => e.count).reduce(math.max);
  int get maxCityCount =>
      cities.isEmpty ? 1 : cities.map((e) => e.count).reduce(math.max);
  _RegionStat priority(String name) => provinces.firstWhere(
    (s) => s.name == name,
    orElse: () => _RegionStat(name: name, count: 0, amount: 0),
  );
  _RegionStat group(String name, List<String> provinceNames) {
    final matched = provinces.where((s) => provinceNames.contains(s.name));
    return _RegionStat(
      name: name,
      count: matched.fold(0, (sum, s) => sum + s.count),
      amount: matched.fold(0, (sum, s) => sum + s.amount),
    );
  }
}

class _RegionStat {
  const _RegionStat({
    required this.name,
    required this.count,
    required this.amount,
  });
  final String name;
  final int count;
  final double amount;
}

_RegionStats _buildRegionStats(List<ScaffoldBidCase> bids) {
  final provinceMap = <String, _RegionStat>{};
  final cityMap = <String, _RegionStat>{};
  for (final bid in bids) {
    final province = (bid.province?.isNotEmpty ?? false)
        ? bid.province!
        : '未知省份';
    final city = (bid.city?.isNotEmpty ?? false)
        ? '$province${bid.city}'
        : '$province-未知城市';
    final amount = bid.bidAmount ?? 0;
    final p =
        provinceMap[province] ??
        _RegionStat(name: province, count: 0, amount: 0);
    provinceMap[province] = _RegionStat(
      name: province,
      count: p.count + 1,
      amount: p.amount + amount,
    );
    final c = cityMap[city] ?? _RegionStat(name: city, count: 0, amount: 0);
    cityMap[city] = _RegionStat(
      name: city,
      count: c.count + 1,
      amount: c.amount + amount,
    );
  }
  final provinces = provinceMap.values.toList()
    ..sort((a, b) => b.count.compareTo(a.count));
  final cities = cityMap.values.toList()
    ..sort((a, b) => b.count.compareTo(a.count));
  return _RegionStats(provinces: provinces, cities: cities);
}

class _PriorityRegionCard extends StatelessWidget {
  const _PriorityRegionCard({required this.title, required this.stat});
  final String title;
  final _RegionStat stat;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 160,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              '${stat.count} 条',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            Text('金额 ${amountWan(stat.amount)}'),
          ],
        ),
      ),
    ),
  );
}

class _RegionBar extends StatelessWidget {
  const _RegionBar({required this.stat, required this.maxCount});
  final _RegionStat stat;
  final int maxCount;
  @override
  Widget build(BuildContext context) {
    final ratio = maxCount <= 0 ? 0.0 : stat.count / maxCount;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(stat.name)),
                Text('${stat.count} 条 · ${amountWan(stat.amount)}'),
              ],
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: ratio.clamp(0.0, 1.0)),
          ],
        ),
      ),
    );
  }
}

class FilterBar extends StatelessWidget {
  const FilterBar({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    scrollDirection: Axis.horizontal,
    padding: const EdgeInsets.all(8),
    child: Row(
      children: children
          .map(
            (w) => Padding(padding: const EdgeInsets.only(right: 8), child: w),
          )
          .toList(),
    ),
  );
}

class FilterField extends StatelessWidget {
  const FilterField({
    super.key,
    required this.controller,
    required this.label,
    this.keyboardType,
  });
  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: 130,
    child: TextField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
    ),
  );
}

class PageSummary extends StatelessWidget {
  const PageSummary({super.key, required this.page});
  final PageResult page;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      '共 ${page.total} 条，第 ${page.page} 页，每页 ${page.pageSize} 条',
      style: Theme.of(context).textTheme.labelMedium,
    ),
  );
}

class PriceCard extends StatelessWidget {
  const PriceCard({super.key, required this.price});
  final PriceDaily price;
  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      title: Text('${price.productName} ${price.spec ?? ''}'),
      subtitle: Text(
        '${price.region}${price.city ?? ''} · ${fmtDate(price.date)} · ${price.sourceName}',
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            price.price.toStringAsFixed(2),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          Text(price.unit),
        ],
      ),
    ),
  );
}

class BidCard extends StatelessWidget {
  const BidCard({super.key, required this.bid, this.onTap});
  final ScaffoldBidCase bid;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      onTap: onTap,
      title: Text(bid.projectName),
      subtitle: Text(
        '${bid.province ?? ''}${bid.city ?? ''} · ${bid.scaffoldType ?? ''} · ${bid.procurementType ?? ''}\n中标：${bid.winner ?? '-'} · 面积：${bid.areaM2?.toStringAsFixed(0) ?? '-'}㎡ · ${fmtDate(bid.publishDate)}',
      ),
      isThreeLine: true,
      trailing: Text(
        bid.bidAmount == null
            ? '-'
            : '${(bid.bidAmount! / 10000).toStringAsFixed(1)}万',
      ),
    ),
  );
}

class BidDetailPage extends StatelessWidget {
  const BidDetailPage({super.key, required this.bid});
  final ScaffoldBidCase bid;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('中标案例详情')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(bid.projectName, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        DetailRow(label: '地区', value: '${bid.province ?? ''}${bid.city ?? ''}'),
        DetailRow(label: '采购人', value: bid.buyer),
        DetailRow(label: '中标人', value: bid.winner),
        DetailRow(
          label: '金额',
          value: bid.bidAmount == null
              ? null
              : '${(bid.bidAmount! / 10000).toStringAsFixed(2)} 万元',
        ),
        DetailRow(
          label: '面积',
          value: bid.areaM2 == null
              ? null
              : '${bid.areaM2!.toStringAsFixed(0)} ㎡',
        ),
        DetailRow(
          label: '吨位',
          value: bid.tonnage == null
              ? null
              : '${bid.tonnage!.toStringAsFixed(0)} 吨',
        ),
        DetailRow(
          label: '租期',
          value: bid.rentalDays == null ? null : '${bid.rentalDays} 天',
        ),
        DetailRow(
          label: '类型',
          value: '${bid.scaffoldType ?? '-'} / ${bid.procurementType ?? '-'}',
        ),
        DetailRow(label: '发布日期', value: fmtDate(bid.publishDate)),
        DetailRow(label: 'AI 摘要', value: bid.aiSummary ?? bid.serviceScope),
        SelectableText(
          '来源：${bid.sourceUrl}',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    ),
  );
}

class DetailRow extends StatelessWidget {
  const DetailRow({super.key, required this.label, required this.value});
  final String label;
  final String? value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 84,
          child: Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
        Expanded(
          child: SelectableText(
            (value == null || value!.isEmpty) ? '-' : value!,
          ),
        ),
      ],
    ),
  );
}

class ReferenceCard extends StatelessWidget {
  const ReferenceCard({super.key, required this.ref});
  final ScaffoldPriceReference ref;
  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      title: Text(
        '${ref.scaffoldType ?? ''} ${ref.calculatedPrice.toStringAsFixed(2)} ${ref.calculatedUnit}',
      ),
      subtitle: Text('${ref.region ?? ''} · ${ref.confidence}\n${ref.formula}'),
      isThreeLine: true,
    ),
  );
}

class InfoCard extends StatelessWidget {
  const InfoCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
  });
  final String title;
  final String subtitle;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      leading: Icon(icon),
      title: Text(title),
      subtitle: Text(subtitle),
    ),
  );
}

class EmptyCard extends StatelessWidget {
  const EmptyCard({super.key, required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Center(child: Text(message)),
    ),
  );
}

class ErrorCard extends StatelessWidget {
  const ErrorCard({super.key, required this.message, required this.onRetry});
  final String message;
  final Future<void> Function() onRetry;
  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.errorContainer,
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('加载失败', style: Theme.of(context).textTheme.titleMedium),
          Text(message),
          const SizedBox(height: 8),
          FilledButton(onPressed: onRetry, child: const Text('重试')),
        ],
      ),
    ),
  );
}

String fmtDate(DateTime? d) =>
    d == null ? '-' : DateFormat('yyyy-MM-dd').format(d);
String fmtDateTime(DateTime? d) =>
    d == null ? '-' : DateFormat('yyyy-MM-dd HH:mm').format(d);
String amountWan(double amount) =>
    amount == 0 ? '-' : '${(amount / 10000).toStringAsFixed(1)}万';
String categoryLabel(String category) => switch (category) {
  'steel' => '钢材',
  'scrap' => '废钢',
  'scaffold' => '脚手架',
  _ => category,
};

// ---------------------------------------------------------------------------
// Crawl Status Card (homepage)
// ---------------------------------------------------------------------------

class _CrawlStatusCard extends StatelessWidget {
  const _CrawlStatusCard({required this.detail, required this.api});
  final CrawlRunDetail detail;
  final ApiClient api;

  Color _statusColor(String status) => switch (status) {
    'success' => Colors.green,
    'partial_success' => Colors.orange,
    'failed' => Colors.red,
    'running' => Colors.blue,
    _ => Colors.grey,
  };

  @override
  Widget build(BuildContext context) {
    final run = detail.run;
    final color = _statusColor(run.status);
    final sources = detail.sources;
    final blocked = sources.where((s) => s.status == 'blocked').length;
    final failed = sources.where((s) => s.status == 'failed').length;
    return Card(
      color: color.withValues(alpha: 0.1),
      child: InkWell(
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => CrawlRunDetailPage(detail: detail),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.smart_toy, color: color),
                  const SizedBox(width: 8),
                  Text('最新自动抓取', style: Theme.of(context).textTheme.titleMedium),
                  const Spacer(),
                  _StatusChip(status: run.status),
                ],
              ),
              const SizedBox(height: 8),
              Text('计划: ${run.runType}  ·  ${run.totalSources} 源  ·  新增 ${run.totalSaved} 条'),
              if (blocked > 0 || failed > 0)
                Text(
                  '⚠ blocked $blocked  ·  failed $failed',
                  style: TextStyle(color: Colors.red.shade700),
                ),
              Text(
                '${fmtDateTime(run.startedAt)}  →  ${fmtDateTime(run.finishedAt)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CrawlQuickLinks extends StatelessWidget {
  const _CrawlQuickLinks({required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 8,
    runSpacing: 8,
    children: [
      ActionChip(
        avatar: const Icon(Icons.smart_toy, size: 18),
        label: const Text('抓取状态'),
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => AutoCrawlDashboardPage(api: api)),
        ),
      ),
      ActionChip(
        avatar: const Icon(Icons.error_outline, size: 18),
        label: const Text('失败源'),
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => CrawlFailuresPage(api: api)),
        ),
      ),
      ActionChip(
        avatar: const Icon(Icons.history, size: 18),
        label: const Text('运行历史'),
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => CrawlRunHistoryPage(api: api)),
        ),
      ),
    ],
  );
}

// ---------------------------------------------------------------------------
// Auto Crawl Dashboard Page
// ---------------------------------------------------------------------------

class AutoCrawlDashboardPage extends StatelessWidget {
  const AutoCrawlDashboardPage({super.key, required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) => LoadState<CrawlRunDetail>(
    loader: () => api.crawlOrchestratorLatest(),
    builder: (context, detail, refresh) => CrawlRunDetailPage(
      detail: detail,
      onRefresh: refresh,
    ),
  );
}

// ---------------------------------------------------------------------------
// Crawl Run Detail Page
// ---------------------------------------------------------------------------

class CrawlRunDetailPage extends StatelessWidget {
  const CrawlRunDetailPage({super.key, required this.detail, this.onRefresh});
  final CrawlRunDetail detail;
  final Future<void> Function()? onRefresh;

  Color _sourceColor(String status) => switch (status) {
    'success' => Colors.green,
    'no_match' => Colors.grey.shade400,
    'blocked' => Colors.grey,
    'failed' => Colors.red,
    'skipped' => Colors.grey.shade300,
    _ => Colors.blue,
  };

  @override
  Widget build(BuildContext context) {
    final run = detail.run;
    final body = RefreshIndicator(
      onRefresh: onRefresh ?? (() async {}),
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text('运行 #${run.id}', style: Theme.of(context).textTheme.titleLarge),
                      const Spacer(),
                      _StatusChip(status: run.status),
                    ],
                  ),
                  const SizedBox(height: 8),
                  _DetailRow('计划', run.runType),
                  _DetailRow('开始', fmtDateTime(run.startedAt)),
                  _DetailRow('结束', fmtDateTime(run.finishedAt)),
                  _DetailRow('数据源', '${run.totalSources}'),
                  _DetailRow('新增', '${run.totalSaved}'),
                  _DetailRow('附件', '${run.totalAttachments}'),
                  _DetailRow('AI抽取', '${run.totalAiExtracted}'),
                  _DetailRow('待复核', '${run.totalReviewTasks}'),
                  if (run.notificationStatus != null) _DetailRow('通知', run.notificationStatus!),
                  if (run.errorMessage != null && run.errorMessage!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        '错误: ${run.errorMessage}',
                        style: TextStyle(color: Colors.red.shade700, fontSize: 12),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text('数据源详情', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...detail.sources.map(
            (s) => Card(
              color: _sourceColor(s.status).withValues(alpha: 0.08),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(child: Text(s.sourceName, style: const TextStyle(fontWeight: FontWeight.w600))),
                        _StatusChip(status: s.status, mini: true),
                      ],
                    ),
                    if (s.province != null || s.city != null)
                      Text('${s.province ?? ''} ${s.city ?? ''}'.trim(), style: Theme.of(context).textTheme.bodySmall),
                    Text('找到 ${s.totalFound} · 保存 ${s.totalSaved}'),
                    if (s.blockedReason != null)
                      Text('原因: ${s.blockedReason}', style: TextStyle(color: Colors.red.shade700, fontSize: 12)),
                    if (s.errorMessage != null && s.errorMessage!.isNotEmpty)
                      Text(s.errorMessage!, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
    if (onRefresh != null) return body;
    return Scaffold(appBar: AppBar(title: Text('抓取 #${run.id}')), body: body);
  }
}

// ---------------------------------------------------------------------------
// Crawl Failures Page
// ---------------------------------------------------------------------------

class CrawlFailuresPage extends StatelessWidget {
  const CrawlFailuresPage({super.key, required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) => LoadState<List<CrawlRunSource>>(
    loader: () => api.crawlOrchestratorFailures(),
    isEmpty: (data) => data.isEmpty,
    empty: '暂无失败源',
    builder: (context, sources, refresh) => RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: sources.map(
          (s) => Card(
            color: Colors.grey.shade100,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text(s.sourceName, style: const TextStyle(fontWeight: FontWeight.w600))),
                      _StatusChip(status: s.status, mini: true),
                    ],
                  ),
                  if (s.province != null || s.city != null)
                    Text('${s.province ?? ''} ${s.city ?? ''}'.trim()),
                  if (s.blockedReason != null)
                    Text('屏蔽原因: ${s.blockedReason}', style: TextStyle(color: Colors.red.shade700)),
                  if (s.errorMessage != null && s.errorMessage!.isNotEmpty)
                    Text(s.errorMessage!, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
                ],
              ),
            ),
          ),
        ).toList(),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Crawl Run History Page
// ---------------------------------------------------------------------------

class CrawlRunHistoryPage extends StatelessWidget {
  const CrawlRunHistoryPage({super.key, required this.api});
  final ApiClient api;

  Color _statusColor(String status) => switch (status) {
    'success' => Colors.green,
    'partial_success' => Colors.orange,
    'failed' => Colors.red,
    _ => Colors.grey,
  };

  @override
  Widget build(BuildContext context) => LoadState<PageResult<CrawlRun>>(
    loader: () => api.crawlOrchestratorRuns(),
    isEmpty: (data) => data.items.isEmpty,
    empty: '暂无运行历史',
    builder: (context, page, refresh) => RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          PageSummary(page: page),
          ...page.items.map(
            (run) => Card(
              color: _statusColor(run.status).withValues(alpha: 0.06),
              child: InkWell(
                onTap: () async {
                  try {
                    final detail = await api.crawlOrchestratorRunDetail(run.id);
                    if (context.mounted) {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => CrawlRunDetailPage(detail: detail)),
                      );
                    }
                  } catch (_) {}
                },
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('#${run.id} ${run.runType}', style: const TextStyle(fontWeight: FontWeight.w600)),
                          const Spacer(),
                          _StatusChip(status: run.status, mini: true),
                        ],
                      ),
                      Text('${run.totalSaved} 条  ·  ${run.totalSources} 源  ·  ${fmtDateTime(run.startedAt)}'),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Shared widgets
// ---------------------------------------------------------------------------

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status, this.mini = false});
  final String status;
  final bool mini;

  Color _bgColor() => switch (status) {
    'success' => Colors.green,
    'partial_success' => Colors.orange,
    'failed' => Colors.red,
    'running' => Colors.blue,
    'blocked' => Colors.grey,
    'no_match' => Colors.grey.shade300,
    _ => Colors.grey.shade300,
  };

  String _label() => switch (status) {
    'success' => '成功',
    'partial_success' => '部分成功',
    'failed' => '失败',
    'running' => '运行中',
    'blocked' => '已屏蔽',
    'no_match' => '无匹配',
    'skipped' => '已跳过',
    _ => status,
  };

  @override
  Widget build(BuildContext context) => Container(
    padding: EdgeInsets.symmetric(horizontal: mini ? 6 : 8, vertical: mini ? 2 : 4),
    decoration: BoxDecoration(color: _bgColor(), borderRadius: BorderRadius.circular(8)),
    child: Text(_label(), style: TextStyle(color: Colors.white, fontSize: mini ? 10 : 12, fontWeight: FontWeight.w600)),
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow(this.label, this.value);
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(
      children: [
        SizedBox(width: 80, child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
        Expanded(child: Text(value)),
      ],
    ),
  );
}
