import 'package:flutter/material.dart';

class DateRangeFilterField extends StatelessWidget {
  const DateRangeFilterField({super.key, required this.label, this.value, required this.onChanged});
  final String label;
  final DateTimeRange? value;
  final ValueChanged<DateTimeRange?> onChanged;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(label),
      subtitle: Text(value == null ? '不限' : '${value!.start.toIso8601String().substring(0,10)} ~ ${value!.end.toIso8601String().substring(0,10)}'),
      trailing: IconButton(
        icon: const Icon(Icons.date_range),
        onPressed: () async {
          final now = DateTime.now();
          final picked = await showDateRangePicker(
            context: context,
            firstDate: DateTime(now.year - 2),
            lastDate: DateTime(now.year + 1),
            initialDateRange: value,
          );
          onChanged(picked);
        },
      ),
    );
  }
}

class RegionFilterField extends StatelessWidget {
  const RegionFilterField({super.key, this.province, this.city, required this.onProvinceChanged, required this.onCityChanged});
  final String? province;
  final String? city;
  final ValueChanged<String?> onProvinceChanged;
  final ValueChanged<String?> onCityChanged;

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Expanded(child: TextFormField(initialValue: province, decoration: const InputDecoration(labelText: '省份'), onChanged: (v)=>onProvinceChanged(v.isEmpty?null:v))),
      const SizedBox(width: 12),
      Expanded(child: TextFormField(initialValue: city, decoration: const InputDecoration(labelText: '城市'), onChanged: (v)=>onCityChanged(v.isEmpty?null:v))),
    ]);
  }
}

class ScaffoldTypeFilterField extends StatelessWidget {
  const ScaffoldTypeFilterField({super.key, this.value, required this.onChanged});
  final String? value;
  final ValueChanged<String?> onChanged;
  static const options = ['盘扣', '扣件', '门式'];

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: value,
      decoration: const InputDecoration(labelText: '脚手架类型'),
      items: options.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
      onChanged: onChanged,
    );
  }
}
