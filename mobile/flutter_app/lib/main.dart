
import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api_client.dart';
import 'models.dart';

void main() => runApp(const BuildingPriceApp());

class BuildingPriceApp extends StatelessWidget {
  const BuildingPriceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '建筑价格情报',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff1565c0)), useMaterial3: true),
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
      _Destination('钢材', Icons.stacked_line_chart, PriceListPage(api: api, title: '钢材价格', category: 'steel')),
      _Destination('废钢', Icons.recycling, PriceListPage(api: api, title: '废钢价格', category: 'scrap')),
      _Destination('脚手架', Icons.construction, PriceListPage(api: api, title: '脚手架价格', category: 'scaffold')),
      _Destination('中标案例', Icons.assignment_turned_in, BidCasesPage(api: api)),
      _Destination('参考价', Icons.price_change, ReferencesPage(api: api)),
      _Destination('趋势', Icons.show_chart, TrendsPage(api: api)),
      _Destination('报价', Icons.calculate, QuotePage(api: api)),
    ];
    return Scaffold(
      appBar: AppBar(title: Text(pages[selected].label), actions: [Padding(padding: const EdgeInsets.all(12), child: Center(child: Text(api.baseUrl, style: Theme.of(context).textTheme.labelSmall)))]),
      body: pages[selected].page,
      bottomNavigationBar: NavigationBar(
        selectedIndex: selected,
        onDestinationSelected: (i) => setState(() => selected = i),
        destinations: pages.map((p) => NavigationDestination(icon: Icon(p.icon), label: p.label)).toList(),
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
  const LoadState({super.key, required this.loader, required this.builder, this.empty, this.isEmpty, this.padding = const EdgeInsets.all(12)});
  final Future<T> Function() loader;
  final Widget Function(BuildContext context, T data, Future<void> Function() refresh) builder;
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
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError) {
          return RefreshIndicator(
            onRefresh: refresh,
            child: ListView(padding: widget.padding, children: [ErrorCard(message: snapshot.error.toString(), onRetry: refresh)]),
          );
        }
        final data = snapshot.data as T;
        if (widget.isEmpty?.call(data) == true) {
          return RefreshIndicator(onRefresh: refresh, child: ListView(padding: widget.padding, children: [EmptyCard(message: widget.empty ?? '暂无数据')]));
        }
        return widget.builder(context, data, refresh);
      },
    );
  }
}

class HomePage extends StatelessWidget {
  const HomePage({super.key, required this.api});
  final ApiClient api;
  @override
  Widget build(BuildContext context) {
    return LoadState<List<PriceDaily>>(
      loader: api.todayPrices,
      isEmpty: (items) => items.isEmpty,
      builder: (context, prices, refresh) => RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            FutureBuilder<HealthStatus>(
              future: api.health(),
              builder: (context, s) => InfoCard(title: '后端状态', subtitle: s.hasData ? '${s.data!.service}: ${s.data!.status}' : '检查中...', icon: Icons.cloud_done),
            ),
            const SizedBox(height: 8),
            Text('今日价格', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            ...prices.map((p) => PriceCard(price: p)),
          ],
        ),
      ),
    );
  }
}

class PriceListPage extends StatefulWidget {
  const PriceListPage({super.key, required this.api, required this.title, required this.category});
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
    return Column(children: [
      FilterBar(children: [
        FilterField(controller: region, label: '区域'),
        FilterField(controller: city, label: '城市'),
        FilterField(controller: product, label: '品名'),
        FilledButton(onPressed: () => setState(() => reload++), child: const Text('筛选')),
      ]),
      Expanded(
        child: LoadState<PageResult<PriceDaily>>(
          key: ValueKey('${widget.category}-$reload'),
          loader: () => widget.api.prices(category: widget.category, region: region.text, city: city.text, productName: product.text),
          isEmpty: (page) => page.items.isEmpty,
          builder: (context, page, refresh) => RefreshIndicator(onRefresh: refresh, child: ListView(padding: const EdgeInsets.all(12), children: [PageSummary(page: page), ...page.items.map((p) => PriceCard(price: p))])),
        ),
      ),
    ]);
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
  int reload = 0;
  @override
  Widget build(BuildContext context) => Column(children: [
        FilterBar(children: [FilterField(controller: keyword, label: '关键词'), FilterField(controller: province, label: '省份'), FilterField(controller: type, label: '类型'), FilledButton(onPressed: () => setState(() => reload++), child: const Text('筛选'))]),
        Expanded(
          child: LoadState<PageResult<ScaffoldBidCase>>(
            key: ValueKey(reload),
            loader: () => widget.api.scaffoldBids(keyword: keyword.text, province: province.text, scaffoldType: type.text),
            isEmpty: (p) => p.items.isEmpty,
            builder: (context, page, refresh) => RefreshIndicator(
              onRefresh: refresh,
              child: ListView(padding: const EdgeInsets.all(12), children: [PageSummary(page: page), ...page.items.map((b) => BidCard(bid: b))]),
            ),
          ),
        ),
      ]);
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
  Widget build(BuildContext context) => Column(children: [
        FilterBar(children: [FilterField(controller: region, label: '地区'), FilterField(controller: type, label: '类型'), FilterField(controller: unit, label: '单位'), FilledButton(onPressed: () => setState(() => reload++), child: const Text('筛选'))]),
        Expanded(
          child: LoadState<PageResult<ScaffoldPriceReference>>(
            key: ValueKey(reload),
            loader: () => widget.api.scaffoldReferences(region: region.text, scaffoldType: type.text, calculatedUnit: unit.text),
            isEmpty: (p) => p.items.isEmpty,
            builder: (context, page, refresh) => RefreshIndicator(
              onRefresh: refresh,
              child: ListView(padding: const EdgeInsets.all(12), children: [PageSummary(page: page), ...page.items.map((r) => ReferenceCard(ref: r))]),
            ),
          ),
        ),
      ]);
}

class TrendsPage extends StatefulWidget {
  const TrendsPage({super.key, required this.api});
  final ApiClient api;
  @override
  State<TrendsPage> createState() => _TrendsPageState();
}

class _TrendsPageState extends State<TrendsPage> {
  String category = 'steel';
  final product = TextEditingController();
  int days = 30;
  int reload = 0;
  @override
  Widget build(BuildContext context) => Column(children: [
        FilterBar(children: [
          DropdownButton<String>(value: category, items: const [DropdownMenuItem(value: 'steel', child: Text('钢材')), DropdownMenuItem(value: 'scrap', child: Text('废钢')), DropdownMenuItem(value: 'scaffold', child: Text('脚手架'))], onChanged: (v) => setState(() => category = v ?? 'steel')),
          FilterField(controller: product, label: '品名'),
          SizedBox(width: 90, child: TextField(decoration: const InputDecoration(labelText: '天数'), keyboardType: TextInputType.number, onChanged: (v) => days = int.tryParse(v) ?? 30)),
          FilledButton(onPressed: () => setState(() => reload++), child: const Text('刷新')),
        ]),
        Expanded(
          child: LoadState<List<PriceTrendPoint>>(
            key: ValueKey('$category-$reload'),
            loader: () => widget.api.trends(category: category, productName: product.text, days: days),
            isEmpty: (items) => items.isEmpty,
            builder: (context, items, refresh) => RefreshIndicator(
              onRefresh: refresh,
              child: ListView(
                padding: const EdgeInsets.all(12),
                children: [
                  TrendLineChart(points: items),
                  const SizedBox(height: 8),
                  ...items.map((p) => ListTile(leading: const Icon(Icons.timeline), title: Text('${fmtDate(p.date)}  ${p.productName}'), subtitle: Text('${p.region}${p.city ?? ''}'), trailing: Text('${p.price.toStringAsFixed(2)} ${p.unit}'))),
                ],
              ),
            ),
          ),
        ),
      ]);
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
  final tons = TextEditingController();
  ScaffoldQuoteResult? result;
  String? error;
  bool loading = false;

  Future<void> submit() async {
    setState(() { loading = true; error = null; });
    try {
      result = await widget.api.calculateQuote(scaffoldType: type.text, region: region.text, areaM2: double.tryParse(area.text), rentalDays: double.tryParse(days.text), tonnage: double.tryParse(tons.text));
    } catch (e) {
      error = e.toString();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(12), children: [
        FilterField(controller: type, label: '脚手架类型'),
        FilterField(controller: region, label: '地区'),
        FilterField(controller: area, label: '面积㎡', keyboardType: TextInputType.number),
        FilterField(controller: days, label: '租赁天数', keyboardType: TextInputType.number),
        FilterField(controller: tons, label: '吨数（元/吨/天时使用）', keyboardType: TextInputType.number),
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: loading ? null : submit, icon: const Icon(Icons.calculate), label: Text(loading ? '计算中...' : '计算报价')),
        if (error != null) ErrorCard(message: error!, onRetry: submit),
        if (result == null && error == null) const EmptyCard(message: '输入条件后点击计算'),
        if (result != null) Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('估算结果', style: Theme.of(context).textTheme.titleLarge), Text('参考价：${result!.referencePrice.toStringAsFixed(2)} ${result!.calculatedUnit}'), Text('估算金额：${result!.estimatedAmount?.toStringAsFixed(2) ?? '参数不足'}'), Text('置信度：${result!.confidence} / 样本：${result!.referenceCount}'), Text('公式：${result!.formula}')]))),
      ]);
}

class TrendLineChart extends StatelessWidget {
  const TrendLineChart({super.key, required this.points});
  final List<PriceTrendPoint> points;

  @override
  Widget build(BuildContext context) {
    final sorted = [...points]..sort((a, b) => (a.date ?? DateTime(1970)).compareTo(b.date ?? DateTime(1970)));
    final prices = sorted.map((p) => p.price).toList();
    final minY = prices.reduce(math.min);
    final maxY = prices.reduce(math.max);
    final span = math.max(1.0, maxY - minY);
    final spots = <FlSpot>[
      for (var i = 0; i < sorted.length; i++) FlSpot(i.toDouble(), sorted[i].price),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 16, 18, 12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('价格趋势折线图', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          SizedBox(
            height: 220,
            child: LineChart(
              LineChartData(
                minY: minY - span * 0.08,
                maxY: maxY + span * 0.08,
                gridData: const FlGridData(show: true),
                borderData: FlBorderData(show: true),
                titlesData: FlTitlesData(
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: math.max(1, (sorted.length / 4).floor()).toDouble(),
                      getTitlesWidget: (value, meta) {
                        final i = value.round();
                        if (i < 0 || i >= sorted.length) return const SizedBox.shrink();
                        return Padding(padding: const EdgeInsets.only(top: 4), child: Text(DateFormat('MM-dd').format(sorted[i].date ?? DateTime.now()), style: const TextStyle(fontSize: 10)));
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 46, getTitlesWidget: (value, meta) => Text(value.toStringAsFixed(0), style: const TextStyle(fontSize: 10)))),
                ),
                lineBarsData: [
                  LineChartBarData(spots: spots, isCurved: true, color: Theme.of(context).colorScheme.primary, barWidth: 3, dotData: const FlDotData(show: true), belowBarData: BarAreaData(show: true, color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.12))),
                ],
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

class FilterBar extends StatelessWidget {
  const FilterBar({super.key, required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => SingleChildScrollView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), child: Row(children: children.map((w) => Padding(padding: const EdgeInsets.only(right: 8), child: w)).toList()));
}

class FilterField extends StatelessWidget {
  const FilterField({super.key, required this.controller, required this.label, this.keyboardType});
  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  @override
  Widget build(BuildContext context) => SizedBox(width: 130, child: TextField(controller: controller, keyboardType: keyboardType, decoration: InputDecoration(labelText: label, border: const OutlineInputBorder())));
}

class PageSummary extends StatelessWidget {
  const PageSummary({super.key, required this.page});
  final PageResult page;
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(bottom: 8), child: Text('共 ${page.total} 条，第 ${page.page} 页，每页 ${page.pageSize} 条', style: Theme.of(context).textTheme.labelMedium));
}

class PriceCard extends StatelessWidget {
  const PriceCard({super.key, required this.price});
  final PriceDaily price;
  @override
  Widget build(BuildContext context) => Card(child: ListTile(title: Text('${price.productName} ${price.spec ?? ''}'), subtitle: Text('${price.region}${price.city ?? ''} · ${fmtDate(price.date)} · ${price.sourceName}'), trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [Text(price.price.toStringAsFixed(2), style: Theme.of(context).textTheme.titleMedium), Text(price.unit)])));
}

class BidCard extends StatelessWidget {
  const BidCard({super.key, required this.bid});
  final ScaffoldBidCase bid;
  @override
  Widget build(BuildContext context) => Card(child: ListTile(title: Text(bid.projectName), subtitle: Text('${bid.province ?? ''}${bid.city ?? ''} · ${bid.scaffoldType ?? ''} · ${bid.procurementType ?? ''}\n中标：${bid.winner ?? '-'} · 面积：${bid.areaM2?.toStringAsFixed(0) ?? '-'}㎡ · ${fmtDate(bid.publishDate)}'), isThreeLine: true, trailing: Text(bid.bidAmount == null ? '-' : '${(bid.bidAmount! / 10000).toStringAsFixed(1)}万')));
}

class ReferenceCard extends StatelessWidget {
  const ReferenceCard({super.key, required this.ref});
  final ScaffoldPriceReference ref;
  @override
  Widget build(BuildContext context) => Card(child: ListTile(title: Text('${ref.scaffoldType ?? ''} ${ref.calculatedPrice.toStringAsFixed(2)} ${ref.calculatedUnit}'), subtitle: Text('${ref.region ?? ''} · ${ref.confidence}\n${ref.formula}'), isThreeLine: true));
}

class InfoCard extends StatelessWidget {
  const InfoCard({super.key, required this.title, required this.subtitle, required this.icon});
  final String title;
  final String subtitle;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Card(child: ListTile(leading: Icon(icon), title: Text(title), subtitle: Text(subtitle)));
}

class EmptyCard extends StatelessWidget {
  const EmptyCard({super.key, required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(24), child: Center(child: Text(message))));
}

class ErrorCard extends StatelessWidget {
  const ErrorCard({super.key, required this.message, required this.onRetry});
  final String message;
  final Future<void> Function() onRetry;
  @override
  Widget build(BuildContext context) => Card(color: Theme.of(context).colorScheme.errorContainer, child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('加载失败', style: Theme.of(context).textTheme.titleMedium), Text(message), const SizedBox(height: 8), FilledButton(onPressed: onRetry, child: const Text('重试'))])));
}

String fmtDate(DateTime? d) => d == null ? '-' : DateFormat('yyyy-MM-dd').format(d);
