import 'package:flutter/material.dart';

import '../../api_client.dart';
import '../../models.dart';

class IngestStatusPage extends StatelessWidget {
  const IngestStatusPage({super.key, required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<IngestStatusOverview>(
      future: api.ingestStatusOverview(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        final data = snapshot.data!;
        final rate = (data.successRate * 100).toStringAsFixed(1);
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(child: ListTile(title: const Text('近24小时接入健康度'), subtitle: Text('成功率 $rate%'))),
            Card(child: ListTile(title: const Text('成功数'), trailing: Text('${data.successCount}'))),
            Card(child: ListTile(title: const Text('失败数'), trailing: Text('${data.failureCount}'))),
            Card(child: ListTile(title: const Text('最近错误'), subtitle: Text(data.lastError ?? '无'))),
          ],
        );
      },
    );
  }
}
