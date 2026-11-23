#!/usr/bin/env python3
"""诊断 APK 是否适配灵控桌面大图标（标准 banner + 私有 beidouui_icon 双通道）。

用法:
    python inspect_apk.py <目标.apk>

依赖: pip install pyaxmlparser
"""
import re
import struct
import sys
import zipfile

try:
    from pyaxmlparser import APK
except ImportError:
    sys.exit("缺少依赖，请先运行: pip install pyaxmlparser")


def png_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    return None


def beidou_values(text):
    """提取所有 beidouui_icon 的 value（兼容属性顺序不同的情况）。"""
    results = []
    for m in re.finditer(r"<meta-data\b[^>]*/?>", text):
        tag = m.group(0)
        if 'android:name="beidouui_icon"' not in tag:
            continue
        v = re.search(r'android:value="([^"]+)"', tag)
        if v:
            results.append(v.group(1))
    return results


def resolve_ref(apk, value):
    """把二进制 Manifest 里的 @7F0C0000 映射成 @mipmap/ic_launcher。"""
    if not value or not re.fullmatch(r"@(?:0x)?[0-9A-Fa-f]{8}", value):
        return value
    try:
        import contextlib
        import io

        rid = int(value.lstrip("@")[2:] if value.lower().startswith("@0x")
                  else value.lstrip("@"), 16)
        # 某些 pyaxmlparser 版本会在解析资源名时打印调试噪音，屏蔽掉
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            name = apk.get_android_resources().get_resource_xml_name(rid)
        if not name:
            return value
        name = name.split(":", 1)[-1].lstrip("@")  # 去掉包名前缀
        return "@" + name
    except Exception:
        return value


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python inspect_apk.py <目标.apk>")
    apk_path = sys.argv[1]

    import contextlib
    import io

    # pyaxmlparser 内部会向 stdout/stderr 打印调试噪音，只在这些调用期间静音
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        apk = APK(apk_path)
        xml_bytes = apk.get_android_manifest_axml().get_xml()
    text = xml_bytes.decode("utf-8", errors="replace")

    print("=" * 72)
    print("package:", apk.get_package())
    try:
        print("version: %s (code %s)" % (
            str(apk.version_name).strip(), str(apk.version_code).strip()))
    except Exception:
        pass

    # application banner / leanback feature
    app_banner = "null"
    m = re.search(r"<application[^>]*>", text)
    if m:
        mb = re.search(r'android:banner="([^"]+)"', m.group(0))
        if mb:
            app_banner = mb.group(1)

    leanback = re.search(
        r'<uses-feature[^>]*android:name="android\.software\.leanback"[^>]*/>', text
    )
    leanback_req = "未声明"
    if leanback:
        mr = re.search(r'android:required="([^"]+)"', leanback.group(0))
        leanback_req = mr.group(1) if mr else "(默认 false)"

    print("uses-feature leanback: required=" + leanback_req)
    print("application banner:", resolve_ref(apk, app_banner))

    # activity-alias：自闭合或成对标签都要整体匹配，
    # 否则 meta-data 的 "/>" 会提前截断、丢掉 intent-filter 里的 category。
    aliases = re.findall(
        r"<activity-alias\b[^>]*/>|<activity-alias\b.*?</activity-alias>", text, re.S
    )
    print("-" * 72)
    if not aliases:
        print("activity-alias: 无")

    has_standard = app_banner not in ("null", "")
    has_leanback_entry = bool(re.search(r'category\.LEANBACK_LAUNCHER"', text))
    enabled_names = []
    private_values = beidou_values(text)

    for a in aliases:
        name = re.search(r'android:name="([^"]+)"', a)
        name = name.group(1).split(".")[-1] if name else "?"
        en = re.search(r'android:enabled="([^"]+)"', a)
        enabled = en.group(1) if en else "(未显式声明)"
        if enabled == "true":
            enabled_names.append(name)

        bn = re.search(r'android:banner="([^"]+)"', a)
        banner = bn.group(1) if bn else "null"
        vals = beidou_values(a)
        has_launcher = bool(re.search(r'category\.LAUNCHER"', a))
        has_leanback = bool(re.search(r'category\.LEANBACK_LAUNCHER"', a))
        cat_str = ("LAUNCHER," if has_launcher else "") + ("LEANBACK" if has_leanback else "")
        cat_str = cat_str.strip(",") or "-"
        if banner not in ("null", ""):
            has_standard = True
        print(
            "alias: %-24s enabled=%-12s banner=%-26s beidouui_icon=%-24s cats=[%s]"
            % (name, enabled, resolve_ref(apk, banner),
               ",".join(vals) if vals else "-", cat_str)
        )

    # assets 里的 16:9 大图
    print("-" * 72)
    big_icons = []
    assets_names = []
    with zipfile.ZipFile(apk_path) as z:
        assets_names = z.namelist()
        for n in assets_names:
            if n.startswith("assets/") and n.lower().endswith((".png", ".webp", ".jpg")):
                sz = png_size(z.read(n))
                if sz and sz[0] >= 320 and abs(sz[0] / sz[1] - 16 / 9) < 0.05:
                    big_icons.append((n, sz))

    if big_icons:
        print("assets 大图:")
        for n, (w, h) in big_icons:
            print("  %s (%dx%d)" % (n, w, h))
    else:
        print("assets 大图: 无")

    # 私有字段 value 与 assets 文件精确匹配
    if private_values:
        missing = []
        for v in dict.fromkeys(private_values):  # 去重，多个 alias 可能引用同一张图
            candidates = [n for n in assets_names if n.startswith("assets/")
                          and n.rsplit("/", 1)[-1] == v]
            if not candidates:
                missing.append(v)
            else:
                print("私有大图文件匹配: %s -> %s OK" % (v, candidates[0]))
        if missing:
            print("私有大图文件匹配: 缺失 -> " + ", ".join(missing))
    else:
        print("私有大图文件匹配: 无 beidouui_icon 声明")

    # 结论
    print("=" * 72)
    problems = []
    if not has_standard:
        problems.append("缺标准 android:banner 通道")
    if not private_values:
        problems.append("缺灵控私有 beidouui_icon 通道")
    if leanback_req in ("未声明", "true", "(默认 true)"):
        problems.append("leanback feature 缺失或 required=true（影响普通设备安装）")
    if not has_leanback_entry:
        problems.append("入口缺 CATEGORY_LEANBACK_LAUNCHER（TV 桌面搜不到 App）")
    if len(enabled_names) > 1:
        problems.append("多个 alias 同时 enabled=true，会出现多个入口图标")
    if private_values:
        for v in private_values:
            if not any(n.startswith("assets/") and n.rsplit("/", 1)[-1] == v
                       for n in assets_names):
                problems.append("beidouui_icon 指向的 assets/%s 不存在" % v)
                break

    if not problems:
        print("VERDICT: 已适配灵控大图标（标准 banner + 私有 beidouui_icon 双通道齐全）")
        print("注意: 脚本只能证明声明与资源正确，桌面实际渲染须在 TCL/雷鸟真机确认。")
    else:
        print("VERDICT: 未完全适配，问题如下:")
        for p in problems:
            print("  - " + p)


if __name__ == "__main__":
    main()
