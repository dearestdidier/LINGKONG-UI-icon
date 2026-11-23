# 灵控私有协议：是什么、怎么加、边界在哪

本文是整套方案的知识底座。给非技术人员解释时，可直接引用这里的结论。

## 1. 现象与真相

**现象**：在 TCL/雷鸟电视的灵控桌面（Lingkong UI / CyberUI）上，绝大多数侧载安装的 App 只显示一个方形小图标；少数 App 却能显示带画面的大图标 / 大卡片。

**常见误解**：以为是桌面"智能拉取"应用图标，或者有白名单放行。

**真相**：这是 **App 侧主动适配** 的结果。灵控桌面开放了卡片/图标接入能力，App 按约定声明资源，桌面才显示大图。公开资料也印证——主流视频客户端是"在卡片设计上做了适配"才有大卡片；灵控官方宣称开放了桌面 API / 卡片开放平台，提供多尺寸卡片。

## 2. 灵控桌面的身份标识

| 项 | 值 | 说明 |
|---|---|---|
| 桌面包名 | `com.tcl.cyberui` | 系统桌面应用 |
| 内部代号 | **BeidouUI / beidou** | 灵控桌面版本串后缀即 `.beidou`；私有字段名 `beidouui_icon` 同源，这是判定其归属的最强线索 |
| 卡片形式 | 1x1 小卡、1x2 横卡、2x2 大卡 | 大卡可带内容展现 |

## 3. 私有协议定义

### 3.1 字段三要素

| 要素 | 规定值 | 说明 |
|---|---|---|
| 字段位置 | 启动入口的 `<meta-data>`（推荐 `activity-alias`，兼容 `activity`） | 必须挂在带 `LAUNCHER` category 的入口上 |
| `android:name` | 固定 `beidouui_icon` | 全小写，不可改 |
| `android:value` | **`assets/` 下的裸文件名**，如 `tv_launcher.png` | 不带 `@`、不带 `drawable/` 等路径前缀，就是文件名字符串 |

完整示例：

```xml
<activity-alias
    android:name=".LauncherBigIcon"
    android:enabled="true"
    android:exported="true"
    android:icon="@mipmap/ic_launcher"
    android:banner="@drawable/banner"
    android:targetActivity=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.MAIN"/>
        <category android:name="android.intent.category.LAUNCHER"/>
        <category android:name="android.intent.category.LEANBACK_LAUNCHER"/>
    </intent-filter>
    <!-- 灵控私有：value 是 assets 里的文件名，不是资源引用 -->
    <meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>
</activity-alias>
```

### 3.2 三条最容易写错的规定

1. **value 是文件名，不是资源引用**。`android:value="tv_launcher.png"` 正确；`android:value="@drawable/banner"` 错误。这是最常踩的坑。
2. **图片放 `assets/` 根目录，不是 `res/drawable/`**。assets 里的文件不进资源表，桌面只能靠文件名字符串去读。
3. **文件名必须与 value 逐字一致，含大小写**。改了文件名就要同步改 meta-data，否则桌面找不到图、静默降级为小图标。

### 3.3 与标准 banner 的分工

| | 标准 `android:banner` | 私有 `beidouui_icon` |
|---|---|---|
| 属性类型 | 资源引用 `@drawable/banner` | 裸字符串文件名 `tv_launcher.png` |
| 图片位置 | `res/drawable-*/banner.png` | `assets/tv_launcher.png` |
| 声明位置 | `<application>` 或入口 activity/alias | 入口 `<meta-data>` |
| 标准化 | Google 官方，有文档 | TCL 私有，无文档 |
| 作用范围 | 所有 Leanback 桌面 | 仅灵控桌面 |

两者读的是**不同文件**，互不替代。要跨设备稳定显示大图标，必须两条都做。

## 4. 为什么两条通道都要

- 只做标准 banner：多数 TV 桌面能显示横幅，但灵控的大卡片可能仍不达标，部分版本仍降级为小图标。
- 只做私有协议：非 TCL 设备完全读不到，等于没适配。
- 两条都做：标准通道兜底所有 Leanback 桌面，私有通道在灵控上拿到专属大图，互不冲突。

## 5. 证据与可信度

本方案的技术细节来自对一款**已适配该协议的第三方 TV 应用 APK** 的逆向分析（2026-11）：

- 用 `pyaxmlparser` 解析二进制 `AndroidManifest.xml`，得到 `activity-alias`、双通道声明；
- 用 `resources.arsc` 映射资源 ID 到 `mipmap/ic_launcher*` / `drawable/banner*`；
- 读 PNG 文件头得到 assets 大图为 640×360；
- dex 中出现 `launcher_icon_style` 与多套 Launcher 样式名，证实"图标可选"是 App 内设置驱动的 alias 切换。

结合 Google 官方 Android TV banner 规范，可确认：

- 双通道结构的真实存在与字段拼写是可信的一手证据；
- 尺寸档位（160×90 / 320×180 / 640×360）符合 Android 密度体系与实测结果。

## 6. 未公开的部分（必须如实告知）

`beidouui_icon` 属于**未公开私有接口**，以下内容无公开文档、无法从 App 侧确认：

- 桌面何时扫描/刷新这个字段（首次安装？桌面重启？开机？）
- 私有图有无大小/格式/尺寸上限，超出如何降级
- 是否存在设备型号、系统版本、签名或包名白名单限制
- 系统大版本更新后字段是否保留

因此：**任何声称"已适配成功"的结论，都必须经过 TCL/雷鸟真机验证**。脚本只能证明声明与资源正确，不能证明桌面渲染结果。

## 7. 普通 App 为什么只有小图标

普通 App 的 Manifest 通常只有 `android:icon`（方形 mipmap），没有 `android:banner`，没有 `LEANBACK_LAUNCHER` 入口，更没有 `beidouui_icon`。灵控桌面扫不到任何横幅资源，只能把方形 icon 缩放显示成小图标。

所以"别的 App 能显示大图标"不是桌面偏心，而是那些 App 多写了几行声明、多放了几张图。这是任何第三方 App 都能复制的做法。

## 8. 可迁移的最小改动集

任何第三方 TV App 想获得同样效果：

1. 加 16:9 banner 图片：至少 xhdpi 320×180，建议补齐 160×90 与 640×360。
2. 给入口加 `MAIN` + `LAUNCHER` + `LEANBACK_LAUNCHER`，并声明 `android:banner`。
3. 在入口上加 `<meta-data android:name="beidouui_icon" android:value="<assets 文件名>"/>`，同名 PNG 放进 `assets/` 根目录。
4. 声明 `android.software.leanback` 且 `required="false"`，保证普通设备可安装。
5. 需要多套样式时用多个 `activity-alias`，运行时切换 enabled，且始终只启用一个。
6. 回编译/编译后用 `inspect_apk.py` 回读验证，再上真机确认。
