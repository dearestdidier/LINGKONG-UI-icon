#!/usr/bin/env python3
"""生成灵控桌面大图标所需的横幅图片（三档密度 + assets 私有大图）。

用法:
    python gen_banner.py --app-name "我的TV" --color "#222222" --out-dir ./out
    python gen_banner.py --app-name "我的TV" --logo ./logo.png --out-dir ./out
    python gen_banner.py --app-name "我的TV" --suffix light --color "#F5F5F5" --out-dir ./out

产物:
    <out>/res/drawable-mdpi/banner.png       160x90
    <out>/res/drawable-xhdpi/banner.png      320x180  (官方基准)
    <out>/res/drawable-xxhdpi/banner.png     640x360
    <out>/assets/tv_launcher.png             640x360  (beidouui_icon 引用)

    带 --suffix light 时文件名变为 banner_light.png / tv_launcher_light.png

依赖: pip install Pillow
"""
import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("缺少依赖，请先运行: pip install Pillow")

SIZES = {
    "mdpi": (160, 90),
    "xhdpi": (320, 180),
    "xxhdpi": (640, 360),
}


def pick_font(px):
    """跨平台挑一个可用的无衬线粗体字体。"""
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, px)
        except Exception:
            continue
    return ImageFont.load_default()


def hex_color(s):
    s = s.lstrip("#")
    if len(s) == 6:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    return (0x22, 0x22, 0x22)


def draw_banner(size, app_name, color, logo_path=None):
    w, h = size
    img = Image.new("RGBA", (w, h), color + (255,))
    d = ImageDraw.Draw(img)

    safe_x = int(w * 0.08)  # 5%+ 安全区，防 overscan 裁切
    has_logo = False
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            max_h = int(h * 0.62)
            ratio = min((w * 0.30) / logo.width, max_h / logo.height)
            logo = logo.resize((int(logo.width * ratio), int(logo.height * ratio)))
            lx = safe_x
            ly = (h - logo.height) // 2
            img.alpha_composite(logo, (lx, ly))
            text_x = lx + logo.width + int(w * 0.04)
            has_logo = True
        except Exception as e:
            print("  logo 读取失败，忽略:", e)

    if not has_logo:
        text_x = safe_x

    # 字号按高度定，再按可用宽度自适应缩小，确保不裁切
    font_px = max(12, int(h * 0.34))
    font = pick_font(font_px)
    text = app_name
    avail = w - text_x - safe_x
    while font_px > 10:
        if d.textbbox((0, 0), text, font=font)[2] <= avail:
            break
        font_px -= 2
        font = pick_font(font_px)

    bbox = d.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]
    tx = text_x
    ty = (h - th) // 2 - bbox[1]
    outline = max(1, int(h * 0.012))
    d.text((tx, ty), text, font=font, fill=(255, 255, 255, 255),
           stroke_width=outline, stroke_fill=(0, 0, 0, 180))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-name", required=True, help="App 名称，会画在横幅上")
    ap.add_argument("--color", default="#222222", help="背景色 HEX，默认深灰")
    ap.add_argument("--logo", default=None, help="可选 logo 图片路径")
    ap.add_argument("--suffix", default="",
                    help="文件名后缀，如 light -> banner_light.png / tv_launcher_light.png")
    ap.add_argument("--out-dir", default="./out", help="输出根目录")
    args = ap.parse_args()

    try:
        color = hex_color(args.color)
    except Exception:
        sys.exit("color 格式错误，应为 #RRGGBB")

    suffix = "_" + args.suffix if args.suffix else ""
    banner_name = "banner%s.png" % suffix
    asset_name = "tv_launcher%s.png" % suffix
    out = args.out_dir

    for density, size in SIZES.items():
        dest_dir = os.path.join(out, "res", "drawable-" + density)
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, banner_name)
        draw_banner(size, args.app_name, color, args.logo).save(path)
        print("生成", path, size)

    assets_dir = os.path.join(out, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    assets_path = os.path.join(assets_dir, asset_name)
    draw_banner(SIZES["xxhdpi"], args.app_name, color, args.logo).save(assets_path)
    print("生成", assets_path, SIZES["xxhdpi"])

    print("\n完成。把 res/ 和 assets/ 合并进 Android 项目根目录。")
    print("Manifest 对应声明:")
    print('  android:banner="@drawable/%s"' % ("banner" + suffix))
    print('  <meta-data android:name="beidouui_icon" android:value="%s"/>' % asset_name)


if __name__ == "__main__":
    main()
