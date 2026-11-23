---
name: lingkong-tv-big-icon
description: 给 Android TV / 电视盒子 App 适配 TCL·雷鸟「灵控桌面」的大图标（横幅大卡片）。当用户希望 App 在灵控桌面显示大图标而非默认小图标、添加或修改 TV banner、设置 beidouui_icon 私有协议、配置多套可切换图标样式，或诊断"为什么别人的 App 有大图标而我的没有"时使用。输入为 Android 项目源码或 APK，产出为可直接编译/回编译的 Manifest 片段、横幅图片与验证结论。
trigger-words: [灵控桌面, 大图标, 大卡片, 横幅图标, beidouui_icon, TV banner, 电视桌面图标, 雷鸟桌面, TCL桌面, 适配大图标]
---

# 灵控桌面大图标适配

## 一句话结论

灵控桌面显示大图标**不是桌面自动拉取，而是 App 侧主动声明**。只有方形 `android:icon` 的普通 App 必然只显示小图标。要显示大图标，必须同时打通两条通道：

| 通道 | 声明方式 | 被谁读取 |
|---|---|---|
| **A · 标准 Android TV** | `android:banner="@drawable/banner"` + `CATEGORY_LEANBACK_LAUNCHER` | 所有 Leanback 桌面（原生 Android TV、灵控、当贝等） |
| **B · 灵控私有协议** | `<meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>`，同名 PNG 放 `assets/` 根目录 | TCL/雷鸟灵控桌面专属（内部代号 BeidouUI） |

只做 A，灵控大卡片可能仍不达标；只做 B，非 TCL 设备没有大图。**要真正适配，两条都要加。**

## 协议速查（是什么 / 怎么加 / 什么尺寸）

详见 [协议原理](references/protocol.md)、[尺寸规范](references/size-spec.md)、[Manifest 模板](references/manifest-recipes.md)。

| 问题 | 答案 |
|---|---|
| 私有字段叫什么 | `beidouui_icon`，固定在启动入口的 `<meta-data>` 上 |
| value 填什么 | **`assets/` 下的裸文件名**，如 `tv_launcher.png`。不是 `@drawable/...`，不带路径 |
| 图放哪里 | `assets/` **根目录**，不是 `res/drawable/` |
| 私有图尺寸 | 640×360（16:9） |
| 标准 banner 尺寸 | 160×90（mdpi）、**320×180（xhdpi，官方基准）**、640×360（xxhdpi） |
| 入口还要什么 | `MAIN` + `LAUNCHER` + `LEANBACK_LAUNCHER` 三个 category 齐全 |
| 平板上装不上怎么办 | `<uses-feature android:name="android.software.leanback" android:required="false"/>` |

最小 XML 骨架：

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
    <meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>
</activity-alias>
```

## 工作流

按顺序执行，细节按需读 references。

### 步骤 1：判断输入类型

- **有源码**（找得到 `app/src/main/AndroidManifest.xml`）→ 路线 A：直接改源码，用 `patch_manifest.py` 生成补丁。
- **只有 APK / 仓库不开源** → 路线 B：先 `inspect_apk.py` 诊断，再决定反编译改造还是只出方案。见 [双路线工作流](references/workflows.md)。
- **只问原理、无文件** → 直接读 [协议原理](references/protocol.md) 用文字回答，不改文件。

先诊断，不要凭空改：

```bash
python scripts/inspect_apk.py <目标.apk>
```

它输出包名、当前 `android:banner`、所有 `activity-alias` 及其 `beidouui_icon`、assets 大图，并给出"已适配/未完全适配"结论，还会检查 `beidouui_icon` 的 value 是否真能在 `assets/` 里找到对应文件。

### 步骤 2：准备大图素材

```bash
python scripts/gen_banner.py --app-name "你的App" --color "#2E7D32" --out-dir ./output
```

生成物：

- `res/drawable-mdpi/banner.png` 160×90
- `res/drawable-xhdpi/banner.png` 320×180（官方基准，必需）
- `res/drawable-xxhdpi/banner.png` 640×360
- `assets/tv_launcher.png` 640×360（供 `beidouui_icon` 引用）

做浅色/白色样式时加 `--suffix light`，产出 `banner_light.png` / `tv_launcher_light.png`，与 `patch_manifest.py --variant light` 配套。图片必须含 App 名称文字、居中、对比度高、远处可读；用户提供 logo 时用 `--logo` 合成，不拉伸变形。详见 [尺寸规范](references/size-spec.md)。

### 步骤 3：改 AndroidManifest

四类声明缺一不可：

1. `<uses-feature android:name="android.software.leanback" android:required="false"/>`
2. `android:banner` 指向 `@drawable/banner`（写在 application 与入口 alias 上最稳）
3. 入口带 `MAIN` + `LAUNCHER` + `LEANBACK_LAUNCHER`
4. 入口上 `<meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>`

生成可直接粘贴的片段：

```bash
python scripts/patch_manifest.py --package com.example.app --activity MainActivity --variant default --print
```

自动注入（会先备份 `.bak`）：

```bash
python scripts/patch_manifest.py --manifest app/src/main/AndroidManifest.xml \
  --package com.example.app --activity MainActivity --variant default --apply
```

多套可切换图标、极简兜底写法见 [Manifest 模板与配方](references/manifest-recipes.md)。

### 步骤 4：验证——什么叫"真正适配"

必须四层都过，缺任何一层都不算完成：

| 层 | 内容 | 谁来验 |
|---|---|---|
| 1 · 声明层 | 双通道字段齐全、category 齐全、leanback required=false | `inspect_apk.py` |
| 2 · 资源层 | 三档 banner 尺寸正确；`assets/<value>` 真实存在且 640×360；文件名逐字一致 | `inspect_apk.py` |
| 3 · 运行层 | TCL/雷鸟真机安装后显示大卡片，重启桌面仍显示，只出现一个入口 | **必须真机** |
| 4 · 兼容层 | 普通手机/平板/其他 TV 桌面安装正常、桌面能搜到 App | 真机或测试机 |

编译或回编译后回读成品 APK：

```bash
python scripts/inspect_apk.py <新.apk>
```

常见失败与逐项清单见 [坑位与验证](references/pitfalls.md)。

## 多套可切换图标（可选）

用多个 `activity-alias` 指向同一个 `targetActivity`，每套配自己的 icon / banner / `beidouui_icon`，运行时用 `PackageManager.setComponentEnabledSetting()` 切换。**同一时刻只能有一个 alias 处于 enabled**，否则桌面出现多个入口。写法见 [Manifest 模板与配方](references/manifest-recipes.md)。

## 能力边界与诚实声明

- `beidouui_icon` 是**未公开私有协议**，来自 APK 逆向实证而非官方文档；不同灵控版本可能改字段或规则。交付时必须告知"需在真机验证"。
- 标准 Android TV banner 通道有 Google 官方文档背书，确定性最高；私有通道是增强项。
- 脚本只能证明"声明与资源正确"，**不能证明桌面已渲染大图标**。运行时结果取决于桌面版本、机型、桌面缓存，必须真机确认。
- 本 Skill 只改 App 侧声明，不改桌面系统。无源码且无法安全回编译的 App，只输出改造方案，不要谎称已完成。
- 图标配色与品牌视觉由用户提供或明确确认，不擅自决定。

## 文档索引

- [references/protocol.md](references/protocol.md) — 私有协议是什么、证据来源、未公开部分
- [references/size-spec.md](references/size-spec.md) — 图片尺寸与内容规范
- [references/manifest-recipes.md](references/manifest-recipes.md) — Manifest 模板与多图标切换
- [references/workflows.md](references/workflows.md) — 源码 / APK 双路线
- [references/pitfalls.md](references/pitfalls.md) — 高频错误与验收清单
