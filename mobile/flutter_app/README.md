# building-price-intel Flutter APP

Flutter 安卓/桌面调试客户端，用于对接仓库根目录 FastAPI 后端。

## 目录

```text
mobile/flutter_app
  lib/
    main.dart        # 页面、导航、状态组件
    api_client.dart  # Dio API client
    models.dart      # Dart models + PageResult
```

## 后端准备

在仓库根目录启动 FastAPI 后端：

```bash
cd /home/huanghonsen/projects/construction-price-app/building-price-intel
source .venv/bin/activate
DATABASE_URL=sqlite+pysqlite:///./local_test.db uvicorn app.main:app --host 127.0.0.1 --port 9000
```

如果还没有 SQLite 测试库：

```bash
rm -f local_test.db
DATABASE_URL=sqlite+pysqlite:///./local_test.db alembic upgrade head
DATABASE_URL=sqlite+pysqlite:///./local_test.db python -m app.seed.seed_data
```

## 启动 Flutter APP

```bash
cd /home/huanghonsen/projects/construction-price-app/building-price-intel/mobile/flutter_app
export PATH="$HOME/.local/flutter/bin:$PATH"
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$HOME/Android/Sdk"
export JAVA_HOME="$HOME/.local/jdks/jdk-17.0.17+10"
flutter pub get
flutter run -d <device-id>
```

查看设备：

```bash
flutter devices
```

## baseUrl 切换

默认规则：

- Android 模拟器：`http://10.0.2.2:9000`
- 本机浏览器/Linux 桌面：`http://127.0.0.1:9000`

也可以用 `--dart-define` 强制覆盖：

```bash
flutter run -d linux --dart-define=API_BASE_URL=http://127.0.0.1:9000
flutter run -d <android-emulator-id> --dart-define=API_BASE_URL=http://10.0.2.2:9000
```

真机调试时把地址换成电脑局域网 IP：

```bash
flutter run -d <phone-id> --dart-define=API_BASE_URL=http://192.168.x.x:9000
```

## 已对接 API

- `GET /api/health`
- `GET /api/prices/today`
- `GET /api/prices?page=1&page_size=20`
- `GET /api/prices?category=steel`
- `GET /api/prices?category=scrap`
- `GET /api/prices?category=scaffold`
- `GET /api/prices/trends`
- `GET /api/scaffold/bids?page=1&page_size=20`
- `GET /api/scaffold/prices/reference?page=1&page_size=20`
- `POST /api/quote/scaffold/calculate`

列表接口统一解析：

```json
{"items": [], "total": 0, "page": 1, "page_size": 20}
```

## 页面

- 首页：后端健康状态 + 今日价格
- 钢材价格页：钢材列表 + 区域/城市/品名筛选
- 废钢价格页：废钢列表 + 区域/城市/品名筛选
- 脚手架价格页：脚手架价格列表 + 区域/城市/品名筛选
- 脚手架中标案例页：案例列表 + 关键词/省份/类型筛选
- 参考价页：脚手架参考价 + 地区/类型/单位筛选
- 价格趋势页：按类别/品名/天数查看趋势点
- 报价计算器页：面积、租赁天数、吨数输入，调用后端报价计算

页面均有 loading / error / empty 状态，列表支持下拉刷新。

## 测试与检查

```bash
flutter analyze
flutter test
flutter build apk --debug
```

## 当前限制

- 目前是 MVP UI，未做登录、收藏和本地缓存。
- 趋势页已用 `fl_chart` 做基础折线图，同时保留趋势点列表。
- 数据源仍依赖后端 mock/seed 数据，真实公开数据源接入后页面无需大改。
