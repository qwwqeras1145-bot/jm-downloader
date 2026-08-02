# -*- coding: utf-8 -*-
"""
JM Downloader 图形界面（tkinter 版，Python 自带，无额外依赖）
功能：搜索 / 排行 / 随机 / 详情 / 下载 / 批量导入 / 历史
"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

ACCENT = "#ff6b9d"
BG = "#0f1117"
CARD = "#171a23"
FG = "#e8eaf0"
DIM = "#9aa0b0"


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("JM Downloader")
        root.geometry("980x700")
        root.configure(bg=BG)
        root.minsize(860, 600)

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=FG,
                        rowheight=26, borderwidth=0, font=("Microsoft YaHei", 10))
        style.configure("Treeview.Heading", background="#1d2130", foreground=FG,
                        font=("Microsoft YaHei", 10, "bold"))
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#fff")])
        style.configure("TProgressbar", troughcolor=CARD, background=ACCENT, borderwidth=0)

        self.current_items = []
        self._build_ui()
        self._poll_status()

    # ---------- UI ----------
    def _build_ui(self):
        root = self.root

        # 顶部：标题
        title = tk.Label(root, text="JM Downloader", bg=BG, fg=ACCENT,
                         font=("Microsoft YaHei", 20, "bold"))
        title.pack(pady=(14, 0))
        sub = tk.Label(root, text="禁漫本地下载工具 · 图形版 · 文件保存在程序旁 downloads 文件夹",
                       bg=BG, fg=DIM, font=("Microsoft YaHei", 9))
        sub.pack(pady=(2, 8))

        # 搜索行
        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=14)
        self.kw_var = tk.StringVar()
        kw = tk.Entry(top, textvariable=self.kw_var, bg=CARD, fg=FG, insertbackground=FG,
                      relief="flat", font=("Microsoft YaHei", 11))
        kw.pack(side="left", fill="x", expand=True, ipady=7)
        kw.bind("<Return>", lambda e: self.do_search())
        self._btn(top, "🔍 搜索", self.do_search).pack(side="left", padx=(8, 0))
        self._btn(top, "🎲 随机", self.do_random).pack(side="left", padx=(6, 0))

        # 排行 + 批量
        row2 = tk.Frame(root, bg=BG)
        row2.pack(fill="x", padx=14, pady=8)
        self.rank_var = tk.StringVar(value="本周排行")
        rank = ttk.Combobox(row2, textvariable=self.rank_var, state="readonly", width=12,
                            values=["本周排行", "本月排行", "今日排行"])
        rank.pack(side="left")
        self._btn(row2, "加载排行", self.do_rank).pack(side="left", padx=6)
        self._btn(row2, "📚 历史", self.do_history).pack(side="left", padx=6)
        self._btn(row2, "⬇️ 下载选中", self.do_download).pack(side="left", padx=6)
        self._btn(row2, "🚀 批量导入", self.open_batch_dialog).pack(side="left", padx=6)

        # 结果列表
        cols = ("id", "title", "author", "category")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", height=14)
        for c, w, anchor in (("id", 90, "center"), ("title", 420, "w"),
                             ("author", 180, "w"), ("category", 160, "w")):
            self.tree.heading(c, text={"id": "ID", "title": "标题", "author": "作者", "category": "分类"}[c])
            self.tree.column(c, width=w, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda e: self.do_download())

        # 状态区
        status = tk.Frame(root, bg=BG)
        status.pack(fill="x", padx=14, pady=(0, 6))
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(status, textvariable=self.status_var, bg=BG, fg=FG,
                 font=("Microsoft YaHei", 10), anchor="w").pack(fill="x")
        self.progress = ttk.Progressbar(status, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 0))

        # 详情文本
        self.detail_var = tk.StringVar(value="双击结果可下载；右键结果查看详情。")
        tk.Label(root, textvariable=self.detail_var, bg=CARD, fg=DIM, anchor="w", justify="left",
                 font=("Microsoft YaHei", 9), padx=12, pady=8).pack(fill="x", padx=14, pady=(0, 14))

        self.tree.bind("<Button-3>", self.show_detail)

    def _btn(self, parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd, bg=CARD, fg=FG, relief="flat",
                      activebackground=ACCENT, activeforeground="#fff", cursor="hand2",
                      font=("Microsoft YaHei", 10), padx=12, pady=4)
        return b

    # ---------- 数据 ----------
    def _run(self, fn, on_ok, on_err=None):
        """后台执行任务，避免卡界面"""
        def worker():
            try:
                data = fn()
                self.root.after(0, lambda: on_ok(data))
            except Exception as e:
                if on_err:
                    self.root.after(0, lambda: on_err(e))
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def do_search(self):
        kw = self.kw_var.get().strip()
        if not kw:
            return
        self.status_var.set(f"正在搜索「{kw}」...")
        self._run(lambda: core.search(kw),
                  lambda d: self._fill(d, f"搜索「{kw}」结果 {len(d)} 条"))

    def do_rank(self):
        kind = {"本周排行": "week", "本月排行": "month", "今日排行": "day"}.get(self.rank_var.get(), "week")
        self.status_var.set("正在加载排行...")
        self._run(lambda: core.top(kind),
                  lambda d: self._fill(d, f"{self.rank_var.get()}：{len(d)} 条"))

    def do_random(self):
        self.status_var.set("随机推荐中...")
        self._run(lambda: core.random_album(),
                  lambda d: (self.kw_var.set(d["id"]), self._fill([d], f"🎲 随机推荐 JM{d['id']}")))

    def do_history(self):
        self.status_var.set("读取本地历史...")
        self._run(lambda: core.history(),
                  lambda d: self._fill([{"id": i["id"], "title": f"本地 {i['files']} 张图片",
                                         "author": "已下载", "category": i["zip"] and "含 ZIP" or "未打包"}
                                        for i in d], f"本地已下载 {len(d)} 本"))

    def _fill(self, items, title):
        self.current_items = items or []
        self.tree.delete(*self.tree.get_children())
        for it in self.current_items:
            self.tree.insert("", "end", values=(it.get("id", ""), it.get("title", ""),
                                                it.get("author", ""), it.get("category", "")))
        self.status_var.set(title)

    # ---------- 详情 / 下载 ----------
    def show_detail(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        it = self.current_items[idx]
        aid = str(it.get("id", ""))
        self.status_var.set(f"查询 JM{aid} 详情...")
        self._run(lambda: core.about(aid),
                  lambda a: self.detail_var.set(
                      f"JM{a['id']}《{a['title']}》  作者: {a['author']}  页数: {a['pages']}  "
                      f"赞: {a['likes']}  浏览: {a['views']}\n标签: {', '.join((a.get('tags') or [])[:12])}"),
                  on_err=lambda e: self.detail_var.set(f"⚠️ {e}"))

    def do_download(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        aid = str(self.current_items[idx].get("id", ""))
        self._start_download(aid)

    def _start_download(self, aid):
        try:
            core.start_download(aid)
            self.status_var.set(f"⏳ 开始下载 JM{aid} ...")
        except Exception as e:
            messagebox.showwarning("提示", str(e))

    def open_batch_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("批量导入下载")
        win.configure(bg=BG)
        win.geometry("460x320")
        win.transient(self.root)
        tk.Label(win, text="每行一个漫画 ID（支持逗号/空格分隔）：", bg=BG, fg=FG,
                 font=("Microsoft YaHei", 10)).pack(anchor="w", padx=14, pady=(12, 4))
        txt = scrolledtext.ScrolledText(win, bg=CARD, fg=FG, insertbackground=FG,
                                        relief="flat", font=("Microsoft YaHei", 10), height=8)
        txt.pack(fill="both", expand=True, padx=14)
        hint = tk.Label(win, text="例如：\n1114751\n123456", bg=BG, fg=DIM, font=("Microsoft YaHei", 9))
        hint.pack(anchor="w", padx=14)

        def do_batch():
            raw = txt.get("1.0", "end")
            ids = list(dict.fromkeys([s.strip() for s in raw.replace(",", " ").replace("，", " ")
                                      .replace(";", " ").split() if s.strip()]))
            if not ids:
                messagebox.showwarning("提示", "请输入漫画 ID")
                return
            try:
                n = core.start_batch(ids)
                win.destroy()
                self.status_var.set(f"🚀 已启动批量下载 {n} 本")
            except Exception as e:
                messagebox.showwarning("提示", str(e))

        tk.Button(win, text="🚀 开始批量下载", command=do_batch, bg=ACCENT, fg="#fff",
                  relief="flat", padx=16, pady=6, font=("Microsoft YaHei", 10)).pack(pady=10)

    # ---------- 状态轮询 ----------
    def _poll_status(self):
        try:
            s = core.get_state()
            if s["running"] or s["done"]:
                if s["batch"] and s["queue_total"]:
                    self.progress["maximum"] = s["queue_total"]
                    self.progress["value"] = s["queue_done"]
                    self.status_var.set(f"{s['msg']}  {s['queue_done']}/{s['queue_total']}")
                elif s["total"] > 0:
                    self.progress["maximum"] = s["total"]
                    self.progress["value"] = s["current"]
                    self.status_var.set(f"{s['msg']}  {s['current']}/{s['total']}")
                else:
                    self.progress["maximum"] = 1
                    self.progress["value"] = 0
                    self.status_var.set(s["msg"])
                if s["done"]:
                    if s["batch"] and s["results"]:
                        ok_n = sum(1 for r in s["results"] if r["ok"])
                        self.detail_var.set(
                            "\n".join(f"{'✅' if r['ok'] else '❌'} JM{r['id']}："
                                      f"{str(r.get('files', '')) + ' 张' if r['ok'] else r.get('error', '失败')}"
                                      for r in s["results"]) or s["msg"])
                    elif s["zip_path"]:
                        self.detail_var.set(f"✅ 下载完成！\n📦 ZIP: {s['zip_path']}")
                    elif not s["ok"]:
                        self.detail_var.set(f"❌ 失败: {s['error']}")
                    self.progress["value"] = self.progress["maximum"]
        except Exception:
            pass
        self.root.after(1200, self._poll_status)


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
