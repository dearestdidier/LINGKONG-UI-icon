# Manifest 模板与配方

所有模板中 `com.example.app` / `MainActivity` 需替换为目标 App 的实际值。可用 `scripts/patch_manifest.py --print` 生成。

## 1. 最小可用配置（单个大图标）

覆盖两条通道的精简版，适合快速接入：

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.app">

    <!-- 1. 声明 leanback 但非必需，保证平板/手机可安装 -->
    <uses-feature android:name="android.software.leanback" android:required="false"/>

    <application
        android:icon="@mipmap/ic_launcher"
        android:banner="@drawable/banner"
        android:label="@string/app_name"
        android:exported="true">

        <!-- 2. 入口 alias：三个 category 齐全 -->
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
            <!-- 3. 灵控私有钩子：value 是 assets 下的裸文件名 -->
            <meta-data
                android:name="beidouui_icon"
                android:value="tv_launcher.png"/>
        </activity-alias>

        <activity android:name=".MainActivity" android:exported="true"/>
    </application>
</manifest>
```

### 字段核对表

| 字段 | 为什么必须 |
|---|---|
| `uses-feature leanback required="false"` | 声明 TV 能力但不强制，否则普通手机/平板在应用市场被过滤、无法安装 |
| `application android:banner` | 部分桌面只读 application 级；写在 application + alias 两处最稳 |
| `alias android:banner` | 入口自带横幅，避免被 application 级设置覆盖 |
| `MAIN` action | 启动器识别为可启动入口 |
| `LAUNCHER` category | 普通 Android 桌面显示图标 |
| `LEANBACK_LAUNCHER` category | TV 桌面（含灵控）搜到 App；缺了它 TV 上根本找不到 |
| `meta-data beidouui_icon` | 灵控私有大图钩子 |
| `targetActivity` | 必须指向真实存在、允许被启动的 Activity |
| `exported="true"` | Android 12+ 带 intent-filter 的组件必须显式声明 |

`beidouui_icon` 的 value **不带** `@drawable/`，就是 `assets/` 里的文件名。

## 2. 只改 application 的极简兜底版

若项目结构受限（单 Activity、无法加 alias），可在 `<application>` 上放 banner 与私有 meta-data，并给主 Activity 补 `LEANBACK_LAUNCHER`：

```xml
<application
    android:banner="@drawable/banner"
    ...>
    <meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>
    <activity android:name=".MainActivity" android:exported="true">
        <intent-filter>
            <action android:name="android.intent.action.MAIN"/>
            <category android:name="android.intent.category.LAUNCHER"/>
            <category android:name="android.intent.category.LEANBACK_LAUNCHER"/>
        </intent-filter>
    </activity>
</application>
```

注意：application 级的 `beidouui_icon` 写法**未经实证**。优先用 alias 级写法；此版仅作受限项目兜底，交付时必须说明"需真机验证"。

## 3. 多套可切换图标

当 App 提供"可选图标"时，用多个 alias 指向同一个 `targetActivity`，每套配自己的 icon / banner / `beidouui_icon`，运行时切换 enabled。

```xml
<application android:banner="@drawable/banner" ...>

    <!-- 默认启用：深色款，走灵控私有大图 -->
    <activity-alias
        android:name=".LauncherBigIcon"
        android:enabled="true"
        android:exported="true"
        android:icon="@mipmap/ic_launcher"
        android:banner="@drawable/banner"
        android:targetActivity=".MainActivity">
        <meta-data android:name="beidouui_icon" android:value="tv_launcher.png"/>
        <intent-filter>
            <action android:name="android.intent.action.MAIN"/>
            <category android:name="android.intent.category.LAUNCHER"/>
            <category android:name="android.intent.category.LEANBACK_LAUNCHER"/>
        </intent-filter>
    </activity-alias>

    <!-- 浅色款，走灵控私有大图 -->
    <activity-alias
        android:name=".LauncherLight"
        android:enabled="false"
        android:exported="true"
        android:icon="@mipmap/ic_launcher_light"
        android:banner="@drawable/banner_light"
        android:targetActivity=".MainActivity">
        <meta-data android:name="beidouui_icon" android:value="tv_launcher_light.png"/>
        <intent-filter>...同上三个 category...</intent-filter>
    </activity-alias>

    <!-- 经典款：只有标准 banner，不带私有字段 -->
    <activity-alias
        android:name=".LauncherClassic"
        android:enabled="false"
        android:exported="true"
        android:icon="@mipmap/ic_launcher"
        android:banner="@drawable/banner"
        android:targetActivity=".MainActivity">
        <intent-filter>...同上三个 category...</intent-filter>
    </activity-alias>
</application>
```

### 运行时切换（Kotlin）

```kotlin
fun switchLauncherIcon(context: Context, aliasName: String) {
    val pm = context.packageManager
    val aliases = arrayOf(
        "com.example.app.LauncherBigIcon",
        "com.example.app.LauncherLight",
        "com.example.app.LauncherClassic"
    )
    aliases.forEach { name ->
        val state = if (name == aliasName)
            PackageManager.COMPONENT_ENABLED_STATE_ENABLED
        else
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED
        pm.setComponentEnabledSetting(
            ComponentName(context, name), state,
            PackageManager.DONT_KILL_APP
        )
    }
}
```

### 铁律

- 任何时刻**只能有一个 alias 处于 enabled**，否则桌面出现多个入口图标，部分桌面会错乱。
- 切换用 `DONT_KILL_APP`；切换后桌面可能需要重启或刷新才更新图标，属正常现象。
- alias 名一旦发布不要改——改了等于新入口，用户桌面旧图标会失效。
- 每套 alias 的 `beidouui_icon` 都要指向各自存在的 assets 文件；只给启用项配也行，但切换后未配置的款式会退化为小图标。

## 4. 用脚本生成

```bash
# 深色款（默认）
python scripts/patch_manifest.py --package com.example.app --activity MainActivity \
  --variant default --print

# 浅色款
python scripts/patch_manifest.py --package com.example.app --activity MainActivity \
  --variant light --print

# 自动注入并备份 .bak
python scripts/patch_manifest.py \
  --manifest app/src/main/AndroidManifest.xml \
  --package com.example.app --activity MainActivity \
  --variant default --apply
```

三个 variant 的对应关系：

| variant | alias 名 | banner | beidouui_icon |
|---|---|---|---|
| `default` | `LauncherBigIcon` | `@drawable/banner` | `tv_launcher.png` |
| `light` | `LauncherLight` | `@drawable/banner_light` | `tv_launcher_light.png` |
| `classic` | `LauncherClassic` | `@drawable/banner` | 无（仅标准通道） |

注入前务必确认目标 alias 名不冲突、enabled 状态唯一。
