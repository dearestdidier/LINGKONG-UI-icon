#!/usr/bin/env python3
"""生成（或注入）适配灵控大图标的 AndroidManifest 片段。

两种用法:
  1) 只打印片段，人工粘贴（推荐先看一眼）:
     python patch_manifest.py --package com.example.app --activity MainActivity --variant default --print
  2) 自动注入到现有 Manifest（会先备份 .bak）:
     python patch_manifest.py --manifest /path/AndroidManifest.xml \
         --package com.example.app --activity MainActivity --variant default --apply

variant: default / light / classic —— 对应横幅与 beidouui_icon 组合。
"""
import argparse
import os
import re
import shutil
import sys

VARIANTS = {
    "default": {
        "alias": "LauncherBigIcon",
        "icon": "@mipmap/ic_launcher",
        "banner": "@drawable/banner",
        "beidou": "tv_launcher.png",
    },
    "light": {
        "alias": "LauncherLight",
        "icon": "@mipmap/ic_launcher_light",
        "banner": "@drawable/banner_light",
        "beidou": "tv_launcher_light.png",
    },
    "classic": {
        "alias": "LauncherClassic",
        "icon": "@mipmap/ic_launcher",
        "banner": "@drawable/banner",
        "beidou": None,
    },
}


def build_alias(package, activity, cfg, enabled=True):
    # 支持传入全类名或相对包名的短名
    target = activity if "." in activity.lstrip(".") else package + "." + activity.lstrip(".")
    alias = cfg["alias"]
    lines = [
        "        <activity-alias",
        '            android:name="%s"' % alias,
        '            android:enabled="%s"' % ("true" if enabled else "false"),
        '            android:exported="true"',
        '            android:icon="%s"' % cfg["icon"],
        '            android:banner="%s"' % cfg["banner"],
        '            android:targetActivity="%s">' % target,
        "            <intent-filter>",
        '                <action android:name="android.intent.action.MAIN"/>',
        '                <category android:name="android.intent.category.LAUNCHER"/>',
        '                <category android:name="android.intent.category.LEANBACK_LAUNCHER"/>',
        "            </intent-filter>",
    ]
    if cfg["beidou"]:
        lines += [
            "            <meta-data",
            '                android:name="beidouui_icon"',
            '                android:value="%s"/>' % cfg["beidou"],
        ]
    lines.append("        </activity-alias>")
    return "\n".join(lines)


def ensure_feature_and_application_attrs(manifest):
    """注入 uses-feature 与 application android:banner；返回改动后的文本。"""
    if "android.software.leanback" not in manifest:
        idx = manifest.find("<manifest ")
        end = manifest.find(">", idx)
        if idx == -1 or end == -1:
            sys.exit("找不到 <manifest> 开始标签")
        feature = ('\n    <uses-feature android:name="android.software.leanback" '
                   'android:required="false"/>')
        manifest = manifest[:end + 1] + feature + manifest[end + 1:]

    m = re.search(r"<application\b[^>]*>", manifest)
    if m:
        tag = m.group(0)
        if "android:banner=" not in tag:
            new_tag = tag[:-1].rstrip() + ' android:banner="@drawable/banner">'
            manifest = manifest.replace(tag, new_tag, 1)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", help="目标 AndroidManifest.xml 路径")
    ap.add_argument("--package", required=True, help="应用包名")
    ap.add_argument("--activity", required=True, help="主 Activity（全名或相对包名）")
    ap.add_argument("--variant", choices=VARIANTS.keys(), default="default")
    ap.add_argument("--print", action="store_true", help="仅打印片段")
    ap.add_argument("--apply", action="store_true", help="注入到 --manifest 指定文件")
    args = ap.parse_args()

    cfg = VARIANTS[args.variant]
    snippet = build_alias(args.package, args.activity, cfg, enabled=True)

    if args.print or not args.apply:
        print("=== 1) uses-feature（放在 <manifest> 内）===")
        print('    <uses-feature android:name="android.software.leanback" android:required="false"/>')
        print("\n=== 2) application 节点加属性 ===")
        print('    <application ... android:banner="@drawable/banner" ...>')
        print("\n=== 3) activity-alias（放在 <application> 内）===")
        print(snippet)
        print("\n说明: 多套图标时复制多份 alias，仅一个 enabled=true，其余 false。")
        print("      variant=light 时横幅为 @drawable/banner_light，私有图为 tv_launcher_light.png。")
        if not args.apply:
            return

    if args.apply:
        if not args.manifest or not os.path.exists(args.manifest):
            sys.exit("--apply 需要有效的 --manifest 路径")
        shutil.copy(args.manifest, args.manifest + ".bak")
        with open(args.manifest, "r", encoding="utf-8") as f:
            content = f.read()
        content = ensure_feature_and_application_attrs(content)
        if "</application>" not in content:
            sys.exit("Manifest 中找不到 </application>，无法自动注入")
        if cfg["alias"] in content:
            sys.exit("alias %s 已存在，避免重复注入" % cfg["alias"])
        content = content.replace(
            "</application>", "    " + snippet + "\n    </application>", 1
        )
        with open(args.manifest, "w", encoding="utf-8") as f:
            f.write(content)
        print("已注入:", args.manifest, "(备份在 .bak)")


if __name__ == "__main__":
    main()
