# 图片尺寸与内容规范

## 1. 需要的图片清单

一共四类图，缺一不可。全部由 `scripts/gen_banner.py` 生成，用 `--suffix` 可派生第二套样式。

| 用途 | 位置 | 像素尺寸 | 被谁读取 |
|---|---|---|---|
| 标准 TV 横幅（低密度） | `res/drawable-mdpi/banner.png` | **160×90** | Leanback / 灵控（低密度降级） |
| 标准 TV 横幅（基准） | `res/drawable-xhdpi/banner.png` | **320×180** | Leanback 官方基准，**必需** |
| 标准 TV 横幅（高清） | `res/drawable-xxhdpi/banner.png` | **640×360** | 4K / 高密度电视 |
| 灵控私有大图 | `assets/tv_launcher.png` | **640×360** | `beidouui_icon` meta-data |

全部 **16:9**，PNG 格式，保留 alpha 通道。

### 为什么是这几档

- `android:banner` 引用的 `@drawable/banner` 由 Android 按设备密度自动选三档之一。**xhdpi 320×180 是 Google 官方基准，不可省略**——缺了它，部分 TV 桌面的横幅会异常缩放。
- 640×360 放在 xxhdpi 档，在高密度/4K 电视上更清晰；Android 会按需缩放。
- `assets/tv_launcher.png` **不受资源系统管理**，必须靠 `beidouui_icon` 的 value 精确匹配文件名。改文件名就要同步改 meta-data。
- 方形小图标 mipmap 继续保留，不要删除——手机、平板、部分桌面仍用它。按 Android Studio 默认 mipmap 目录即可（48/72/96/144/192 等密度档）。

### 第二套样式（如浅色主题）

用 `--suffix light` 生成：

- `res/drawable-*/banner_light.png`
- `assets/tv_launcher_light.png`

Manifest 里对应写 `android:banner="@drawable/banner_light"` 与 `android:value="tv_launcher_light.png"`，并用 `--variant light` 生成 alias。

## 2. 图片内容规范

- **必须含 App 名称文字**，居中、无衬线粗体、对比度高，远距离（约 10 英尺 / 3 米）可读。Google TV 规范强制要求 banner 带本地化文字，只放 logo 不合规。
- 多语言 App 理论上每种语言一张带对应文字的 banner。实际第三方 TV App 多为中文/英文单张即可，向用户说明这一点。
- **安全区**：重要元素距边缘 ≥5%，防止 TV overscan 裁切。
- **背景避免大面积纯白**：部分 TV 桌面是浅色主题，纯白图会"消失"。提供深色/浅色两套是更稳的做法。
- 用 PNG 不用 JPEG：桌面常需要透明圆角或 alpha 通道。
- 三档图用**同一版式等比缩放**，不要各画各的，避免切换密度时画面跳变。

## 3. 合成建议

用户提供 logo 时：

- logo 放左侧 1/3 或居中，App 名在 logo 右侧或下方，互不压盖。
- 主色取自用户或 App 品牌色；文字用白色或深灰，加描边保证在任意背景上可读。
- 三档图从同一批参数生成，`gen_banner.py` 已按高度自动计算字号并做宽度自适应缩放，无需手工调整。

## 4. 生成命令速查

```bash
# 默认深色款
python scripts/gen_banner.py --app-name "我的TV" --color "#222222" --out-dir ./output

# 带 logo
python scripts/gen_banner.py --app-name "我的TV" --logo ./logo.png --out-dir ./output

# 浅色主题第二套
python scripts/gen_banner.py --app-name "我的TV" --color "#F5F5F5" --suffix light --out-dir ./output
```

生成后把 `res/` 和 `assets/` 两个目录整体合并进 Android 项目根目录。
