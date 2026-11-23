# 工作流：源码 / APK 双路线

根据目标项目形态选择路线。先诊断，再动手，最后验证。

## 1. 路线判定

| 输入 | 特征 | 路线 |
|---|---|---|
| 完整 Android 源码 | 有 `app/src/main/AndroidManifest.xml`、gradle 工程 | A：改源码 |
| 仓库无源码 | 只有 README / build 脚本 / 配置；APK 在 Release | B：改 APK 或出方案 |
| 只有 APK 文件 | 单个 `.apk` | B：改 APK 或出方案 |
| 仅提问原理 | 无文件 | 直接讲解，不改文件 |

判断是否开源：看仓库 git tree 是否有 `app/src`。**不要因为 README 写得详细就以为有源码**——很多项目只发 APK，构建脚本 `include(":app")` 但源码目录被 `.gitignore` 排除。

## 2. 路线 A：有源码

1. 备份 `AndroidManifest.xml`。
2. 若有旧 APK，先跑 `scripts/inspect_apk.py <旧.apk>` 看现状，确认缺哪条通道。
3. 跑 `scripts/gen_banner.py` 生成图片，合并进项目：
   - `res/drawable-{mdpi,xhdpi,xxhdpi}/banner.png`
   - `assets/tv_launcher.png`
4. 用 `scripts/patch_manifest.py --print` 生成片段，人工或用 `--apply` 注入目标文件。
5. 若做多套图标，按 [manifest-recipes.md](manifest-recipes.md) 的多 alias 写法，并接入设置页切换逻辑。
6. Gradle 编译，装机验证；回读成品 APK 再跑一次 `inspect_apk.py`。

`--apply` 会先备份 `.bak` 再写入。注入前确认 alias 名不冲突、enabled 唯一。

## 3. 路线 B：只有 APK / 不开源仓库

先明确告知用户：无源码时无法"改代码"，只能反编译改造再签名，或输出改造方案让其自行编译。征得同意再继续。

1. **拿到 APK**：从 Release 或设备中提取，核对版本。
2. **诊断**：`python scripts/inspect_apk.py <apk>`，输出 banner / alias / beidouui_icon / assets 大图现状。
3. **判断可行性**：
   - 双通道已齐全且 assets 图匹配 → 已适配，无需改，如实告知。
   - 缺任一 → 需要改造。
4. **改造路径**（需用户确认）：
   - **反编译回编译**：apktool 解包 → 改明文 `AndroidManifest.xml` → 放入 `assets/tv_launcher.png` 与 `res/drawable-*/banner.png` → 回编译 → 签名（apksigner / jarsigner）。风险：目标 App 若有签名校验/完整性校验会启动失败，需实测。
   - **仅出方案**：整理 Manifest 片段 + 图片 + 步骤，交给有源码方。安全、可交付。
5. **验证**：对改造后的 APK 再跑 `inspect_apk.py`，然后真机安装观察。

apktool 回编译注意：Manifest 反编译后是明文 XML，`meta-data` 直接照模板加；资源文件名保持原名，按 `res/drawable/banner.png` 等路径放置即可。

## 4. 真正适配的四层验收

"脚本没报错"不等于适配成功。必须四层都过：

### 第 1 层 · 声明层（脚本可验证）

- `uses-feature android.software.leanback` 且 `required="false"`
- 入口同时有 `MAIN` action + `LAUNCHER` + `LEANBACK_LAUNCHER` category
- `android:banner` 指向 `@drawable/banner`
- 入口上有 `beidouui_icon` meta-data

### 第 2 层 · 资源层（脚本可验证）

- `res/drawable-xhdpi/banner.png` 存在且为 320×180（基准，必需）
- mdpi 160×90、xxhdpi 640×360 齐备
- `assets/<beidouui_icon 的 value>` 文件真实存在，为 16:9 且不小于 320×180（建议 640×360）
- 文件名与 value 逐字一致，含大小写

### 第 3 层 · 运行层（必须真机）

- 在 TCL/雷鸟灵控桌面安装后，App 显示为大图标 / 大卡片
- 重启桌面或电视后仍显示（排除缓存偶然命中）
- 多套图标时只出现一个入口，切换样式后大图跟着变
- 若仍显示小图标：先确认桌面已刷新；再核对第 1、2 层；仍失败则考虑私有字段在该桌面版本被改动的可能

### 第 4 层 · 兼容层

- 普通手机 / 平板安装正常，功能不受影响
- 其他 TV 桌面（原生 Android TV、当贝等）能看到 App 并显示横幅
- 桌面搜索仍能找到 App（leanback 入口没写坏普通入口）

## 5. 诚实边界

- 私有协议 `beidouui_icon` 无官方文档，改造后必须在目标电视真机验证；脚本只能证明"声明与资源正确"，不能证明"桌面已渲染大图"。
- 若 apktool 回编译失败或签名校验导致 App 无法启动，如实报告，退回"仅出方案"，不要声称适配完成。
- 第三方 TV App 多为学习/自用性质，提醒用户在合规与自有设备前提下操作。
