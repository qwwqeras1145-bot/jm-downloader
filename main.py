# -*- coding: utf-8 -*-
"""
JM Downloader 入口
- 双击运行 / 无参数：控制台启动菜单（1=网页版图形界面 2=命令行 3=退出）
- 命令行：
    jm-downloader.exe web                    直接启动网页版（浏览器打开，图形界面）
    jm-downloader.exe about <漫画ID>           查询详情
    jm-downloader.exe search <关键词>          搜索
    jm-downloader.exe top <week|month|day>     排行榜
    jm-downloader.exe dl <漫画ID>              下载并打包 zip
    jm-downloader.exe batch <ID1 ID2 ...>      批量下载多本
    jm-downloader.exe random                   随机推荐
    jm-downloader.exe history                  本地下载记录
"""
import argparse
import json
import os
import sys
import threading
import webbrowser

# 确保可以导入同目录模块（某些 Python 环境未把脚本目录加入 sys.path）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core


def _fix_stdout_encoding():
    """Windows 控制台默认 GBK，强制 UTF-8 输出，避免特殊字符报错"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_fix_stdout_encoding()


def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def wait_download(title="下载"):
    """等待当前下载任务结束，显示实时进度条（含百分比）"""
    import time
    while True:
        s = core.get_state()
        if s["done"]:
            print()
            return s
        cur = int(s.get("current", 0) or 0)
        total = int(s.get("total", 0) or 0)
        msg = (s.get("msg") or "").strip()
        if total > 0:
            pct = min(100, int(cur * 100 / total))
            bar_len = 22
            filled = min(bar_len, int(bar_len * cur / total))
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r📥 {title}: [{bar}] {pct:3d}% ({cur}/{total}) {msg[:28]}", end="", flush=True)
        else:
            print(f"\r⏳ {title}: {msg} (已获取 {cur} 张)", end="", flush=True)
        time.sleep(0.5)


# ---------------- 启动菜单（无参数双击） ----------------

def start_launcher():
    """控制台启动菜单：网页版 / 命令行 / 退出"""
    print()
    print("=" * 46)
    print("   📚  JM Downloader")
    print("-" * 46)
    print("   1. 🌐  网页版图形界面（浏览器打开）【推荐】")
    print("   2. 💻  命令行模式")
    print("   3. 🚪  退出")
    print("-" * 46)
    try:
        sel = input("   请选择 [1/2/3]，回车默认网页版: ").strip() or "1"
    except Exception:
        sel = "1"
    print()
    if sel == "2":
        cli_menu()
    elif sel == "3":
        print("👋 再见")
    else:
        start_web_mode()


def _print_history():
    """打印本地下载记录"""
    items = core.history()
    if not items:
        print("📭 暂无下载记录")
        return
    print(f"📚 本地已下载 {len(items)} 本：")
    for it in items:
        size = it["size"]
        sz = f"{size/1048576:.1f} MB" if size >= 1048576 else f"{size/1024:.0f} KB"
        print(f"  JM{it['id']}   {it['files']} 张   {sz}")


def cli_menu():
    """简单的命令行交互模式"""
    print("💻 命令行模式（输入 help 查看命令，exit 退出）")
    while True:
        try:
            line = input("\njm> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见")
            return
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        if cmd in ("exit", "quit", "q"):
            print("👋 再见")
            return
        if cmd == "help" or cmd == "h":
            print("  search <关键词>    搜索漫画")
            print("  top [week|month|day]  排行榜")
            print("  about <ID>         查询详情")
            print("  dl <ID>            下载并打包 zip")
            print("  batch <ID ID ...>  批量下载")
            print("  random             随机推荐")
            print("  history            本地下载记录")
            print("  exit               退出")
            continue
        try:
            if cmd == "search":
                print_json(core.search(parts[1], 1))
            elif cmd == "top":
                kind = parts[1] if len(parts) > 1 else "week"
                print_json(core.top(kind, 1))
            elif cmd == "about":
                print_json(core.about(parts[1]))
            elif cmd == "random":
                print_json(core.random_album())
            elif cmd == "dl":
                core.start_download(parts[1])
                s = wait_download(f"JM{parts[1]}")
                if s["ok"]:
                    print(f"\n✅ 下载完成！ZIP: {s['zip_path']}")
                else:
                    print(f"\n❌ 失败: {s['error']}")
            elif cmd == "batch":
                n = core.start_batch(parts[1:])
                s = wait_download(f"批量任务 {n} 本")
                print()
                for r in s["results"]:
                    mark = "✅" if r["ok"] else "❌"
                    print(f"  {mark} JM{r['id']}：{r.get('files', '') and (str(r['files']) + ' 张') or r.get('error', '失败')}")
            elif cmd == "history":
                _print_history()
            else:
                print(f"❓ 未知命令: {cmd}（输入 help 查看帮助）")
        except Exception as e:
            print(f"❌ 错误: {e}")


# ---------------- CLI ----------------

def cli_main(args):
    p = argparse.ArgumentParser(prog="jm-downloader", description="JM Downloader - jmcomic 本地下载工具")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("web", help="启动网页版（浏览器打开）")
    sub.add_parser("random", help="随机推荐")

    pa = sub.add_parser("about", help="查询漫画详情")
    pa.add_argument("id", help="漫画 ID")

    ps = sub.add_parser("search", help="搜索漫画")
    ps.add_argument("keyword", help="关键词")
    ps.add_argument("-p", "--page", type=int, default=1)

    pt = sub.add_parser("top", help="排行榜")
    pt.add_argument("kind", nargs="?", default="week", choices=["week", "month", "day"])
    pt.add_argument("-p", "--page", type=int, default=1)

    pd = sub.add_parser("dl", help="下载漫画并打包 zip")
    pd.add_argument("id", help="漫画 ID")

    pb = sub.add_parser("batch", help="批量下载多本（空格分隔 ID）")
    pb.add_argument("ids", nargs="+", help="漫画 ID 列表，例如: batch 1114751 123456 789012")

    opts = p.parse_args(args)

    if not opts.cmd:
        start_launcher()
        return
    if opts.cmd == "web":
        start_web_mode()
        return

    try:
        if opts.cmd == "random":
            print_json(core.random_album())
        elif opts.cmd == "about":
            print_json(core.about(opts.id))
        elif opts.cmd == "search":
            print_json(core.search(opts.keyword, opts.page))
        elif opts.cmd == "top":
            print_json(core.top(opts.kind, opts.page))
        elif opts.cmd == "dl":
            core.start_download(opts.id)
            print(f"⏳ 开始下载 JM{opts.id} ...（Ctrl+C 可取消）")
            s = wait_download(f"JM{opts.id}")
            if s["ok"]:
                print(f"\n✅ 下载完成！")
                print(f"📂 目录: {os.path.join(core.DOWNLOADS_DIR, str(opts.id))}")
                print(f"📦 ZIP: {s['zip_path']}")
            else:
                print(f"\n❌ 失败: {s['error']}")
                sys.exit(1)
        elif opts.cmd == "batch":
            n = core.start_batch(opts.ids)
            print(f"⏳ 批量下载 {n} 本漫画 ...（Ctrl+C 可取消）")
            s = wait_download(f"批量任务 {n} 本")
            print()
            for r in s["results"]:
                mark = "✅" if r["ok"] else "❌"
                print(f"  {mark} JM{r['id']}：{r.get('files', '') and (str(r['files']) + ' 张') or r.get('error', '失败')}")
            if not s["ok"]:
                sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


def start_web_mode():
    import webui
    srv, port = webui.start_web()
    url = f"http://127.0.0.1:{port}"
    print(f"🚀 JM Downloader Web 控制台已启动: {url}")
    print("   关闭本窗口即退出程序。")
    # 延迟打开浏览器，确保服务就绪
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 已退出")


if __name__ == "__main__":
    cli_main(sys.argv[1:])
