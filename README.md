# 灵控桌面大图标适配（LINGKONG-UI-icon）

让 Android TV App 在 **TCL / 雷鸟「灵控桌面」** 上显示大图标（横幅大卡片），而不是默认的方形小图标。

一套 **Agent 可直接读懂** 的知识 + 工具包：喂给 WorkBuddy / Codex / DeepSeek Harness / Claude 等常用 Agent，它们就能自动完成诊断、生成图片、改 Manifest、验证全流程。

> **核心结论**：灵控桌面不会自动"拉取"大图标。大图标是 **App 侧主动声明** 出来的。普通 App 只有 `android:icon`，所以只能显示小图标。

---

## 一、私有协议是什么

灵控桌面（包名 `com.tcl.cyberui`，内部代号 **BeidouUI / beidou**）读取 App 大图走两条**独立**通道：

| 通道 | 声明方式 | 图片 | 适用范围 |
|---|---|---|---|
| **A · 标准 Android TV** | `android:banner="@drawable/banner"` + `CATEGORY_LEANBACK_LAUNCHER` | `res/drawable-*/banner.png` | 所有 Leanback 桌面，Google 官方文档背书 |
| **B · 灵控私有协议** | 入口 `<meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>` | `assets/tv_launcher.png` | 仅 TCL / 雷鸟灵控桌面，未公开 |

**两条都要做**：只做 A，灵控大卡片可能仍不达标；只做 B，非 TCL 设备没有大图。

私有协议的三个关键点：

1. `android:name` 固定为 `beidouui_icon`
2. `android:value` 是 **`assets/` 下的裸文件名**（`tv_launcher.png`），**不是** `@drawable/...` 资源引用
3. 图片放在 **`assets/` 根目录**，文件名与 value 逐字一致（含大小写）

> `beidouui_icon` 属于未公开私有接口，来自 APK 逆向实证，非官方文档。字段解析规则、刷新时机、是否有白名单均未公开——**任何"适配成功"的结论都必须真机验证**。

详细原理与证据见 [`references/protocol.md`](references/protocol.md)。

---

## 二、需要的图片尺寸

| 用途 | 位置 | 尺寸 |
|---|---|---|
| 标准横幅（低密度） | `res/drawable-mdpi/banner.png` | 160×90 |
| 标准横幅（**官方基准，必需**） | `res/drawable-xhdpi/banner.png` | **320×180** |
| 标准横幅（高清） | `res/drawable-xxhdpi/banner.png` | 640×360 |
| 灵控私有大图 | `assets/tv_launcher.png` | 640×360 |

全部 16:9、PNG、保留 alpha。图片必须含 App 名称文字、居中、对比度高、距边缘 ≥5%。方形 mipmap 图标继续保留不要删。详见 [`references/size-spec.md`](references/size-spec.md)。

---

## 三、怎么加（最小 Manifest）

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.app">

    <uses-feature android:name="android.software.leanback" android:required="false"/>

    <application
        android:icon="@mipmap/ic_launcher"
        android:banner="@drawable/banner"
        android:label="@string/app_name">

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
            <!-- 灵控私有大图：value 是 assets 下的裸文件名 -->
            <meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>
        </activity-alias>

        <activity android:name=".MainActivity" android:exported="true"/>
    </application>
</manifest>
```

完整模板、多套可切换图标、极简兜底写法见 [`references/manifest-recipes.md`](references/manifest-recipes.md)，可直接参考 [`examples/AndroidManifest.xml`](examples/AndroidManifest.xml)。

---

## 四、快速开始

```bash
# 0. 依赖
pip install pyaxmlparser Pillow

# 1. 诊断现状（有 APK 时）
python scripts/inspect_apk.py target.apk

# 2. 生成四类图片
python scripts/gen_banner.py --app-name "我的TV" --color "#2E7D32" --out-dir ./output
#    把生成的 res/ 和 assets/ 合并进 Android 项目根目录

# 3. 生成 Manifest 片段（先看再贴）
python scripts/patch_manifest.py --package com.example.app --activity MainActivity --variant default --print
#    或自动注入（自动备份 .bak）
python scripts/patch_manifest.py --manifest app/src/main/AndroidManifest.xml \
  --package com.example.app --activity MainActivity --variant default --apply

# 4. 编译后回读成品 APK 验证
python scripts/inspect_apk.py app/build/outputs/apk/release/app-release.apk
```

`--suffix light` 可派生浅色主题图片（`banner_light.png` / `tv_launcher_light.png`），对应 `--variant light`。

---

## 五、怎样才算真正适配

脚本通过 ≠ 适配成功。必须四层全过：

| 层 | 内容 | 验证方 |
|---|---|---|
| 1 · 声明层 | banner / alias / category / meta-data / uses-feature 齐全正确 | `inspect_apk.py` |
| 2 · 资源层 | 三档 banner 尺寸正确；`assets/<value>` 存在且 16:9 640×360；文件名逐字一致 | `inspect_apk.py` |
| 3 · 运行层 | TCL / 雷鸟真机显示大卡片，重启桌面仍显示，只出现一个入口 | **必须真机** |
| 4 · 兼容层 | 手机 / 平板 / 其他 TV 桌面安装正常、能搜到 App | 真机或测试机 |

完整清单见 [`references/workflows.md`](references/workflows.md) 与 [`references/pitfalls.md`](references/pitfalls.md)。

---

## 六、Agent 兼容性

本仓库为多种 Agent 提供了等价入口，内容一致，任选其一读取即可：

| Agent | 读取入口 | 说明 |
|---|---|---|
| **WorkBuddy** | `SKILL.md` | 带 YAML frontmatter，放到 `~/.workbuddy/skills/lingkong-tv-big-icon/` 即自动加载 |
| **OpenAI Codex / DeepSeek Harness** / 其他 | `AGENTS.md` | 通用 Agent 指令文件，自包含完整流程 |
| **Claude Code** | `CLAUDE.md` → `AGENTS.md` | `CLAUDE.md` 为指针，细节在 `AGENTS.md` |
| **人类 / 任意 Agent** | `README.md`（本文件） | 协议速查 + 快速开始 |

作为 WorkBuddy Skill 安装：

```bash
git clone <本仓库> ~/.workbuddy/skills/lingkong-tv-big-icon
```

然后对 Agent 说：**"用 lingkong-tv-big-icon 帮我的 App 适配灵控桌面大图标"** 即可。

---

## 七、仓库结构

```
lingkong-tv-big-icon/
├── README.md                       # 本文件
├── AGENTS.md                       # 通用 Agent 入口
├── CLAUDE.md                       # Claude 入口指针
├── SKILL.md                        # WorkBuddy Skill 入口（含 frontmatter）
├── LICENSE                         # MIT
├── requirements.txt                # Python 依赖
├── .gitignore
├── agents/
│   └── openai.yaml                 # WorkBuddy Skill 展示元数据
├── examples/
│   └── AndroidManifest.xml         # 完整可编译示例
├── references/
│   ├── protocol.md                 # 私有协议：是什么、证据、边界
│   ├── size-spec.md                # 图片尺寸与内容规范
│   ├── manifest-recipes.md         # Manifest 模板与多图标切换
│   ├── workflows.md                # 源码 / APK 双路线 + 四层验收
│   └── pitfalls.md                 # 高频错误与验证清单
└── scripts/
    ├── inspect_apk.py              # 诊断 APK 现状
    ├── gen_banner.py               # 生成四类图片
    └── patch_manifest.py           # 生成/注入 Manifest 片段
```

---

## 八、边界与免责声明

- `beidouui_icon` 是**未公开私有协议**，来自 APK 逆向实证；字段解析规则无官方文档，不同灵控版本可能改动。使用本工具包即表示你理解并接受这一不确定性。
- 本工具包只修改 **App 侧声明**，不修改桌面系统，不提供任何绕过系统限制的能力。
- 脚本只能证明声明与资源正确，**不能保证桌面实际渲染**；请以真机结果为准。
- 请仅在自有设备与合规前提下使用；对第三方 App 的反编译改造需遵守其许可与当地法律。

## License

MIT — 详见 [`LICENSE`](LICENSE)。
