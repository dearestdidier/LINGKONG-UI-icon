# AGENTS.md — 灵控桌面大图标适配

本文件是给 Codex、DeepSeek Harness 及任何读取 `AGENTS.md` 的编码 Agent 的通用入口。WorkBuddy / Claude 类工具请同时参考 `SKILL.md`。两者内容一致，`SKILL.md` 带 frontmatter 以便作为 Skill 加载。

## 你的任务

让用户指定的 Android TV App 在 TCL/雷鸟「灵控桌面」上显示大图标（横幅大卡片）而不是默认小图标。

## 核心事实（必须先理解）

灵控桌面显示大图**不是桌面自动拉取，而是 App 侧主动声明**。只有方形 `android:icon` 的 App 必然只显示小图标。必须同时打通两条独立通道：

| 通道 | 声明 | 图片 |
|---|---|---|
| A · 标准 Android TV | `android:banner="@drawable/banner"` + `CATEGORY_LEANBACK_LAUNCHER` | `res/drawable-{mdpi,xhdpi,xxhdpi}/banner.png` = 160×90 / 320×180 / 640×360 |
| B · 灵控私有协议 | 入口 `<meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>` | `assets/tv_launcher.png`，640×360 |

**最容易写错的三点**：

1. `beidouui_icon` 的 `android:value` 是 **`assets/` 下的裸文件名**（如 `tv_launcher.png`），**不是** `@drawable/...` 资源引用，不带路径。
2. 私有图必须放在 **`assets/` 根目录**，不是 `res/drawable/`。
3. 文件名与 value 必须逐字一致（含大小写）；改一个就要同步改另一个。

## 必读文档

按顺序读取，不要跳：

1. `references/protocol.md` — 私有协议是什么、证据、未公开边界
2. `references/size-spec.md` — 四类图片的精确尺寸与内容规范
3. `references/manifest-recipes.md` — Manifest 模板与多套图标切换
4. `references/workflows.md` — 源码 / APK 双路线、四层验收标准
5. `references/pitfalls.md` — 高频错误与验证清单

`examples/AndroidManifest.xml` 是一份完整可编译示例，可直接参考。

## 执行流程

### 1. 判断输入

- 有 `app/src/main/AndroidManifest.xml` → 源码路线：直接改源码。
- 只有 APK 或仓库不开源 → APK 路线：先诊断，征得同意后再决定反编译改造或只出方案。
- 只有问题、无文件 → 直接讲原理，不改文件。

### 2. 诊断（有 APK 时必做）

```bash
python scripts/inspect_apk.py <目标.apk>
```

依赖 `pip install pyaxmlparser`。输出包含 banner、所有 alias 的 `beidouui_icon`、category、assets 大图，以及 value 与 assets 文件是否精确匹配的结论。

### 3. 生成图片

```bash
python scripts/gen_banner.py --app-name "App名" --color "#2E7D32" --out-dir ./output
# 第二套浅色样式
python scripts/gen_banner.py --app-name "App名" --color "#F5F5F5" --suffix light --out-dir ./output
```

依赖 `pip install Pillow`。合并 `res/` 和 `assets/` 到项目根目录。图片必须含 App 名称文字、居中、对比度高、距边缘 ≥5%。

### 4. 改 Manifest

四类声明缺一不可：

1. `<uses-feature android:name="android.software.leanback" android:required="false"/>`
2. `android:banner="@drawable/banner"`（application 与入口 alias 都写）
3. 入口带 `MAIN` + `LAUNCHER` + `LEANBACK_LAUNCHER`
4. 入口上 `beidouui_icon` meta-data

```bash
python scripts/patch_manifest.py --package com.example.app --activity MainActivity --variant default --print
python scripts/patch_manifest.py --manifest app/src/main/AndroidManifest.xml \
  --package com.example.app --activity MainActivity --variant default --apply
```

variant：`default` / `light` / `classic`。多套图标时多个 alias 指向同一 `targetActivity`，**任何时刻只能有一个 enabled=true**。

### 5. 验证——四层都过才算完成

| 层 | 判定 | 方式 |
|---|---|---|
| 声明层 | 双通道齐全、category 齐全、leanback required=false | `inspect_apk.py` |
| 资源层 | 三档 banner 尺寸正确；`assets/<value>` 存在且 16:9、640×360；文件名逐字一致 | `inspect_apk.py` |
| 运行层 | TCL/雷鸟真机显示大卡片，重启桌面仍显示，只有一个入口 | **必须真机** |
| 兼容层 | 手机/平板/其他 TV 桌面安装正常、能搜到 App | 真机或测试机 |

编译/回编译后回读成品 APK 再跑一次 `inspect_apk.py`。

## 边界与诚实要求

- `beidouui_icon` 是**未公开私有协议**，来自 APK 逆向实证；不同灵控版本可能改字段。交付时必须告知"需在真机验证"。
- 标准 banner 通道有 Google 官方文档背书；私有通道是增强项。
- 脚本只能证明"声明与资源正确"，**不能证明桌面已渲染大图标**。不得把脚本通过说成适配成功。
- 无源码且无法安全回编译的 App，只输出改造方案，不要谎称已完成。
- 不擅自决定品牌配色与图标视觉，由用户提供或确认。

## 检查清单（交付前自查）

- [ ] 没有把 `beidouui_icon` 的 value 写成资源引用
- [ ] 私有 PNG 在 `assets/` 根目录，文件名与 value 一致
- [ ] xhdpi 320×180 banner 存在
- [ ] 三个 category 齐全、`exported="true"`、leanback `required="false"`
- [ ] 多个 alias 时只有一个 enabled
- [ ] 已回读成品 APK 跑过 `inspect_apk.py`
- [ ] 已明确告知用户需要真机验证
