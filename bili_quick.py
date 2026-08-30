def show_banner():
    """启动横幅：顶部像素风彩条（ANSI 彩色，仅交互模式）"""
    try:
        tty = sys.stdin.isatty()
    except Exception:
        tty = False
    if not tty:
        print("=" * 52)
        print("  视频内容一键提取 -> 投喂文件 (免费总结)")
        print("  支持: B站 / YouTube | 内容语言检测 + 多引擎")
        print("=" * 52)
        return
    P = "\033[38;2;251;114;153m"   # B站粉
    B = "\033[38;2;137;180;250m"   # 蓝
    C = "\033[38;2;94;226;213m"    # 青
    Y = "\033[38;2;249;226;175m"   # 黄
    R = "\033[0m"
    strip = P + "█" * 13 + B + "█" * 13 + C + "█" * 13 + Y + "█" * 13 + R
    print(strip)
    print(P + "▓" + R + "  视频内容一键提取 → 投喂文件（免费总结）  " + P + "▓" + R)
    print(P + "▓" + R + "  B站 / YouTube | 内容语言检测 + 多引擎选择 " + P + "▓" + R)
    print(strip)


def main():
    args = sys.argv[1:]
    use_api = "--api" in args
    args = [a for a in args if a != "--api"]
    lang_manual = None
    for a in args:
        if a.startswith("--lang="):
            lang_manual = a.split("=", 1)[1]
    engine = "auto"
    for a in args:
        if a.startswith("--engine="):
            engine = a.split("=", 1)[1]
    args = [a for a in args if not a.startswith("--lang") and not a.startswith("--engine")]
    if args:
        run_any(args[0], use_api, lang_manual, engine)
        return
    show_banner()
    while True:
        url = input("\n粘贴 视频链接或BV号 (输入 q 退出): ").strip()
        if url.lower() in ("q", "quit", "exit"):
            break
        if not url:
            continue
        try:
            run_any(url, use_api, lang_manual, engine)
        except KeyboardInterrupt:
            break
        except SystemExit as e:
            print(f"[x] {e}")
        except Exception as e:
            print(f"[x] 出错: {type(e).__name__}: {e}")
    print("\n再见~")


if __name__ == "__main__":
    main()
