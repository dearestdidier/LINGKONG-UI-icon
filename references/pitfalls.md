# 坑位与验证

## 1. 高频错误

| 现象 | 原因 | 修复 |
|---|---|---|
| 灵控仍显示小图标 | 只加了 `android:banner`，没加 `beidouui_icon` | 两条通道都加；value 填 assets 裸文件名 |
| `beidouui_icon` 不生效 | value 写成了 `@drawable/banner` 或带路径 | 改成 `tv_launcher.png` 这种纯文件名 |
| meta-data 读不到 | 放在了 application/activity 里，但桌面读的是带 LAUNCHER 的 alias | 放到启动 alias 上，见 [Manifest 模板](manifest-recipes.md) |
| assets 图读不到 | 文件名大小写不符 / 放进了 `res/` | 文件放 `assets/` 根目录，名字与 value 完全一致（含大小写） |
| 桌面出现多个 App 图标 | 多个 alias 同时 `enabled="true"` | 只保留一个 enabled=true，其余 false |
| App 在普通安卓设备装不上 | 声明了 `leanback` 且 `required="true"` | 改为 `android:required="false"` |
| TV 桌面搜不到 App | 入口缺 `CATEGORY_LEANBACK_LAUNCHER` | MAIN / LAUNCHER / LEANBACK_LAUNCHER 补齐 |
| Android 12+ 安装失败 | 带 intent-filter 的组件没声明 `exported` | alias 与 activity 都加 `android:exported="true"` |
| 横幅在部分电视看不见 | 纯白底 + 浅色主题 | 提供深色/浅色两套，或用有对比度的背景 |
| banner 被裁切 | 重要元素贴边，TV overscan | 文字/logo 距边缘 ≥5% |
| 切换图标后旧图标残留 | 桌面缓存未刷新 | 重启桌面或电视；确认只有一个 alias enabled |

## 2. 验证清单

编译/回编译后逐条确认：

- [ ] `python scripts/inspect_apk.py <成品.apk>` 输出含 `android:banner` 非 null
- [ ] 输出含至少一个入口带 `beidouui_icon`
- [ ] `beidouui_icon` 的 value 对应文件确实存在于 APK 的 `assets/` 中（脚本会报"私有大图文件匹配: OK"）
- [ ] 入口同时有 LAUNCHER 与 LEANBACK_LAUNCHER category（输出 `cats=[LAUNCHER,LEANBACK]`）
- [ ] `leanback` feature 为 `required=false`
- [ ] 若有多个 alias，仅一个 `enabled=true`
- [ ] 三档 banner 尺寸为 160×90 / 320×180 / 640×360，私有 assets 图为 640×360
- [ ] **真机**（TCL/雷鸟灵控桌面）安装后显示大图标，重启桌面后仍显示
- [ ] 平板/手机安装正常，功能不受影响

## 3. 诊断脚本能证明什么

`inspect_apk.py` 解析 APK 的二进制 Manifest 与 assets 清单，能证明：

- 声明层面：banner / alias / category / meta-data / uses-feature 是否正确
- 资源层面：assets 里的 16:9 大图是否存在、私有字段 value 能否对应到真实文件

它**不能**证明灵控桌面实际渲染了大图标——那取决于桌面版本、机型、是否重启桌面等运行时因素。必须把这一点如实告知用户。

## 4. 典型诊断输出

适配完整的 App 应得到类似输出：

```
================================================================
package: com.example.app
version: 1.0.4 (code 40)
uses-feature leanback: required=false
application banner: @drawable/banner
----------------------------------------------------------------
alias: LauncherBigIcon         enabled=true   banner=@drawable/banner       beidouui_icon=tv_launcher.png       cats=[LAUNCHER,LEANBACK]
alias: LauncherLight           enabled=false  banner=@drawable/banner_light beidouui_icon=tv_launcher_light.png cats=[LAUNCHER,LEANBACK]
----------------------------------------------------------------
assets 大图:
  assets/tv_launcher.png (640x360)
  assets/tv_launcher_light.png (640x360)
私有大图文件匹配: OK
================================================================
VERDICT: 已适配灵控大图标（标准 banner + 私有 beidouui_icon 双通道齐全）
```

若输出 `VERDICT: 未完全适配`，按上面列出的 problems 逐条修。
