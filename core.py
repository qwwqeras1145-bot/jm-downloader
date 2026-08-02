# -*- coding: utf-8 -*-
"""
jm-downloader 核心逻辑：查询 / 搜索 / 排行 / 下载 / ZIP 打包 / 批量下载
基于 jmcomic 开源库（https://github.com/hect0x7/jmcomic）
"""
import os
import re
import sys
import json
import zipfile
import shutil
import threading
import traceback

# 仅屏蔽 jmcomic 的 INFO 日志，保留 WARNING/ERROR 便于排查问题
import logging
logging.disable(logging.INFO)

APP_VERSION = "v1.0.4"
GITHUB_RELEASE_API = "https://api.github.com/repos/qwwqeras1145-bot/jm-downloader/releases/latest"

# ---------------- 路径 ----------------

def base_dir() -> str:
    """exe 所在目录（PyInstaller 单文件模式）或源码目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DOWNLOADS_DIR = os.path.join(base_dir(), "downloads")
ZIPS_DIR = os.path.join(DOWNLOADS_DIR, "_zips")


def ensure_dirs():
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(ZIPS_DIR, exist_ok=True)


def normalize_id(raw):
    """从输入提取漫画 ID：支持 纯数字 / JM123456 / https://.../album/123456/ 等"""
    s = str(raw).strip()
    m = re.search(r"(?:album|photos/index/|photo/)(\d{4,})", s, re.I)
    if m:
        return m.group(1)
    m = re.search(r"JM\s*(\d+)", s, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{4,})\b", s)
    if m:
        return m.group(1)
    raise ValueError(f"无法识别漫画 ID：{raw}")


# ---------------- jmcomic 配置 ----------------

def make_option():
    """构造 jmcomic 选项：下载目录 = exe 旁 downloads/{album_id}，支持代理"""
    from jmcomic import JmOption, DirRule

    opt = JmOption.default()
    # 每本漫画一个目录：downloads/{album_id}
    # 用 jmcomic 官方预定义规则 'Bd/Aid'（Bd=base_dir, Aid=专辑ID）
    try:
        opt.dir_rule = DirRule("Bd/Aid", base_dir=DOWNLOADS_DIR)
    except Exception:
        pass
    # 代理：优先取网页版设置保存的 config.json，其次环境变量
    proxy = (
        get_proxy()
        or os.environ.get("JM_PROXY")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
    )
    if proxy:
        try:
            client = opt.new_jm_client()
            client.proxies = {"http": proxy, "https": proxy}
        except Exception:
            pass
    return opt


def new_client():
    return make_option().new_jm_client()


# ---------------- 查询 / 搜索 / 排行 ----------------

def about(album_id):
    """查询漫画详情"""
    album_id = normalize_id(album_id)
    client = new_client()
    album = client.get_album_detail(album_id)
    tags = []
    try:
        for t in album.tags:
            tags.append(getattr(t, "tag", str(t)))
    except Exception:
        pass
    photos = []
    try:
        for p in album:
            photos.append({"id": p.id, "title": getattr(p, "title", ""), "pages": p.page_count})
    except Exception:
        pass
    return {
        "id": str(album.id),
        "title": getattr(album, "title", ""),
        "author": getattr(album, "author", ""),
        "description": getattr(album, "description", "") or "",
        "tags": tags,
        "pages": getattr(album, "page_count", 0),
        "likes": getattr(album, "likes", 0),
        "views": getattr(album, "views", 0),
        "series": getattr(album, "series", ""),
        "category": getattr(getattr(album, "category", None), "title", ""),
        "cover": getattr(album, "cover_url", "") or "",
        "photos": photos,
    }


def _parse_search_item(item):
    """兼容 jmcomic 搜索结果两种结构：
    - 迭代: (id, title_str)
    - 索引: (id, info_dict)
    """
    if isinstance(item, tuple) and len(item) >= 2:
        aid, payload = item[0], item[1]
        if isinstance(payload, dict):
            return {
                "id": str(aid),
                "title": payload.get("name", ""),
                "author": payload.get("author", ""),
                "category": (payload.get("category") or {}).get("title", ""),
            }
        return {"id": str(aid), "title": str(payload), "author": "", "category": ""}
    return {
        "id": str(getattr(item, "id", "")),
        "title": getattr(item, "title", ""),
        "author": getattr(item, "author", ""),
        "category": getattr(getattr(item, "category", None), "title", ""),
    }


def search(keyword, page=1):
    """搜索漫画，返回结果列表"""
    client = new_client()
    page_data = client.search_site(keyword, page=page)
    return [_parse_search_item(item) for item in page_data]


def top(kind="week", page=1):
    """排行榜：week / month / day"""
    client = new_client()
    fn = {
        "week": client.week_ranking,
        "month": client.month_ranking,
        "day": client.day_ranking,
    }.get(kind)
    if fn is None:
        raise ValueError(f"未知榜单: {kind}")
    ranks = fn(page)
    return [_parse_search_item(item) for item in ranks]


def random_album():
    """随机推荐：从日榜随机取一本"""
    import random
    items = top("day", 1)
    if not items:
        items = top("week", 1)
    if not items:
        raise RuntimeError("获取随机推荐失败")
    return random.choice(items)


# ---------------- 下载进度 ----------------

STATE_LOCK = threading.Lock()
STATE = {
    "running": False,
    "album_id": None,
    "current": 0,
    "total": 0,
    "msg": "空闲",
    "done": False,
    "ok": False,
    "error": None,
    "zip_path": None,
    # 批量任务字段
    "batch": False,
    "queue_total": 0,
    "queue_done": 0,
    "results": [],
}


def _set_state(**kw):
    with STATE_LOCK:
        STATE.update(kw)


def get_state():
    with STATE_LOCK:
        return dict(STATE)


# ---------------- ZIP 打包 ----------------

def make_zip(album_dir, dst_zip):
    """把专辑目录打包成普通 zip"""
    os.makedirs(os.path.dirname(dst_zip), exist_ok=True)
    files = []
    for root, _, names in os.walk(album_dir):
        for n in names:
            fp = os.path.join(root, n)
            arc = os.path.relpath(fp, album_dir)
            files.append((fp, arc))
    if not files:
        raise RuntimeError("没有可打包的文件")
    with zipfile.ZipFile(dst_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for fp, arc in files:
            z.write(fp, arc)
    return dst_zip


# ---------------- 下载任务（后台线程） ----------------

def _count_images(album_dir):
    """统计目录内图片数量"""
    if not os.path.isdir(album_dir):
        return 0
    try:
        return len([f for f in os.listdir(album_dir)
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))])
    except Exception:
        return 0


def _download_one(album_id, clean=False):
    """同步下载一本漫画，返回 (zip_path, album_dir, 图片数)。失败抛异常

    clean=False（默认）：断点续传 —— 已下载的图片自动跳过，只补缺失部分
                      （jmcomic 内置多线程 30 并发 + 已存在图片跳过机制）
    clean=True：清空旧目录强制重新下载
    """
    album_id = str(album_id)
    ensure_dirs()
    album_dir = os.path.join(DOWNLOADS_DIR, album_id)
    if clean and os.path.isdir(album_dir):
        shutil.rmtree(album_dir, ignore_errors=True)
    # v1.0.4 断点续传增强：清理损坏的半截文件（<10KB 视为下载中断产物），其余已存在图片自动跳过
    if os.path.isdir(album_dir):
        removed = 0
        for fn in os.listdir(album_dir):
            p = os.path.join(album_dir, fn)
            if os.path.isfile(p) and os.path.getsize(p) < 10 * 1024:
                os.remove(p)
                removed += 1
        if removed:
            _set_state(msg=f"🩹 已清理 {removed} 个损坏的半截文件，继续补全剩余图片")
        exist_n = _count_images(album_dir)
        if exist_n:
            _set_state(msg=f"♻️ 断点续传：已有 {exist_n} 张图片，仅补全缺失部分")
    opt = make_option()
    import jmcomic
    jmcomic.download_album(int(album_id), option=opt)
    album_dir = os.path.join(DOWNLOADS_DIR, album_id)
    if not os.path.isdir(album_dir):
        raise RuntimeError(f"未找到下载目录 {album_dir}，下载可能失败")
    files = _count_images(album_dir)
    if not files:
        raise RuntimeError("未下载到任何图片")
    zip_path = make_zip(album_dir, os.path.join(ZIPS_DIR, f"JM{album_id}.zip"))
    return zip_path, album_dir, files


def _download_one_retry(album_id, retries=3):
    """下载一本漫画，失败自动重试（网络波动时很有用）"""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return _download_one(album_id)
        except Exception as e:
            last_err = e
            if attempt < retries:
                _set_state(msg=f"⚠️ 第 {attempt} 次下载失败，正在重试 ({retries - attempt} 次剩余)...")
                import time
                time.sleep(2)
    raise last_err


def _poller_worker(album_id, stop, prefix=""):
    """后台轮询统计已下载图片数，更新 STATE"""
    album_dir = os.path.join(DOWNLOADS_DIR, str(album_id))
    while not stop.is_set():
        n = _count_images(album_dir)
        if n:
            _set_state(current=n, msg=f"{prefix}已获取 {n} 张图片")
        stop.wait(2)


def _download_worker(album_id):
    """单本下载后台任务"""
    try:
        _set_state(running=True, album_id=str(album_id), current=0, total=0,
                   done=False, ok=False, error=None, zip_path=None,
                   batch=False, queue_total=0, queue_done=0, results=[],
                   msg=f"正在下载 JM{album_id} ...")
        stop = threading.Event()
        threading.Thread(target=_poller_worker, args=(album_id, stop), daemon=True).start()
        zip_path, album_dir, files = _download_one_retry(album_id)
        stop.set()
        _set_state(current=files, total=files, msg="打包完成", zip_path=zip_path)
        _set_state(done=True, ok=True, running=False,
                   msg=f"✅ JM{album_id} 下载完成，共 {files} 张图片")
        notify("JM Downloader", f"✅ JM{album_id} 下载完成，共 {files} 张图片")
    except Exception as e:
        _set_state(done=True, ok=False, running=False, error=str(e),
                   msg=f"❌ 失败: {e}")
        notify("JM Downloader", f"❌ JM{album_id} 下载失败：{str(e)[:80]}")
        traceback.print_exc()


def start_download(album_id):
    """后台启动单本下载任务，返回是否已启动"""
    if get_state()["running"]:
        raise RuntimeError("已有任务正在进行，请稍候")
    album_id = normalize_id(album_id)
    ensure_dirs()
    threading.Thread(target=_download_worker, args=(album_id,), daemon=True).start()
    return True


# ---------------- 批量下载 ----------------

def start_batch(ids):
    """后台批量下载多本漫画（依次下载），返回任务数量"""
    if get_state()["running"]:
        raise RuntimeError("已有任务正在进行，请稍候")
    ids = [normalize_id(i) for i in ids if str(i).strip()]
    if not ids:
        raise ValueError("没有有效的漫画 ID")
    ensure_dirs()
    threading.Thread(target=_batch_worker, args=(ids,), daemon=True).start()
    return len(ids)


def _batch_worker(ids):
    """批量下载后台任务：依次下载，记录每本结果"""
    results = []
    try:
        _set_state(running=True, batch=True, queue_total=len(ids), queue_done=0,
                   results=[], done=False, ok=False, error=None)
        for idx, aid in enumerate(ids, 1):
            _set_state(album_id=aid, current=0, total=0, zip_path=None,
                       msg=f"正在下载第 {idx}/{len(ids)} 本：JM{aid} ...")
            stop = threading.Event()
            prefix = f"第 {idx}/{len(ids)} 本 JM{aid}："
            threading.Thread(target=_poller_worker, args=(aid, stop, prefix), daemon=True).start()
            try:
                zip_path, album_dir, files = _download_one_retry(aid)
                results.append({"id": aid, "ok": True, "zip": zip_path, "files": files})
            except Exception as e:
                results.append({"id": aid, "ok": False, "error": str(e)})
            finally:
                stop.set()
            _set_state(queue_done=idx, results=list(results))
        ok_n = sum(1 for r in results if r["ok"])
        msg = f"✅ 批量下载完成：成功 {ok_n}/{len(ids)}" if ok_n == len(ids) \
            else f"批量下载结束：成功 {ok_n}/{len(ids)}"
        _set_state(done=True, ok=ok_n == len(ids), running=False, msg=msg,
                   results=list(results))
        notify("JM Downloader", f"{msg}（成功 {ok_n}/{len(ids)} 本）")
    except Exception as e:
        _set_state(done=True, ok=False, running=False, error=str(e),
                   msg=f"❌ 批量任务异常: {e}", results=list(results))
        traceback.print_exc()


# ---------------- 历史记录 ----------------

def history():
    """本地已下载记录：downloads 下的专辑 + _zips 下的 zip 包"""
    ensure_dirs()
    items = []
    if os.path.isdir(DOWNLOADS_DIR):
        for name in sorted(os.listdir(DOWNLOADS_DIR)):
            d = os.path.join(DOWNLOADS_DIR, name)
            if os.path.isdir(d) and name != "_zips":
                size = 0
                for dp, _, fs in os.walk(d):
                    for f in fs:
                        try:
                            size += os.path.getsize(os.path.join(dp, f))
                        except Exception:
                            pass
                items.append({
                    "id": name,
                    "dir": d,
                    "files": _count_images(d),
                    "size": size,
                    "zip": os.path.join(ZIPS_DIR, f"JM{name}.zip")
                            if os.path.exists(os.path.join(ZIPS_DIR, f"JM{name}.zip")) else None,
                })
    return items

def delete_album(album_id):
    """删除本地已下载的漫画目录及其 ZIP"""
    album_id = normalize_id(album_id)
    album_dir = os.path.join(DOWNLOADS_DIR, album_id)
    zip_path = os.path.join(ZIPS_DIR, f"JM{album_id}.zip")
    removed = []
    if os.path.isdir(album_dir):
        shutil.rmtree(album_dir, ignore_errors=True)
        removed.append(album_dir)
    if os.path.exists(zip_path):
        os.remove(zip_path)
        removed.append(zip_path)
    if not removed:
        raise ValueError(f"本地没有 JM{album_id} 的下载记录")
    return album_id

def open_dir(album_id):
    """在资源管理器中打开下载目录（Windows）"""
    album_id = normalize_id(album_id)
    album_dir = os.path.join(DOWNLOADS_DIR, album_id)
    if not os.path.isdir(album_dir):
        raise ValueError(f"本地没有 JM{album_id} 的下载目录")
    os.startfile(album_dir)


# ---------------- v1.0.3 新增：看图 / 更新检查 / 通知 ----------------

def list_images(album_id):
    """返回某本已下载漫画的图片文件名列表（按文件名排序）"""
    album_id = normalize_id(album_id)
    album_dir = os.path.join(DOWNLOADS_DIR, album_id)
    if not os.path.isdir(album_dir):
        raise ValueError(f"本地没有 JM{album_id} 的下载目录")
    names = [f for f in os.listdir(album_dir)
             if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))]
    # 按页码自然排序：001.jpg < 002.jpg < ... < 010.jpg
    names.sort(key=lambda f: (len(f), f))
    return names


def notify(title, msg):
    """Windows 桌面通知（右下角气泡），失败时静默忽略"""
    try:
        import subprocess
        ps = (
            "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
            "$n=New-Object System.Windows.Forms.NotifyIcon;"
            "$n.Icon=[System.Drawing.SystemIcons]::Information;"
            f"$n.BalloonTipTitle='{title}';"
            f"$n.BalloonTipText='{msg}';"
            "$n.Visible=$true;$n.ShowBalloonTip(3000);"
            "Start-Sleep -Seconds 4;$n.Dispose()"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def check_update():
    """检查 GitHub 最新版本，返回 {'current','latest','url','has_update'}"""
    import urllib.request
    info = {"current": APP_VERSION, "latest": APP_VERSION, "url": "", "has_update": False}
    try:
        req = urllib.request.Request(GITHUB_RELEASE_API, headers={
            "User-Agent": "jm-downloader", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        latest = (data.get("tag_name") or "").lstrip("v")
        info["latest"] = "v" + latest
        info["url"] = data.get("html_url", "")
        def _ver(v):
            return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
        info["has_update"] = _ver(latest) > _ver(APP_VERSION)
    except Exception:
        pass
    return info


# ---------------- v1.0.3：配置 / 书签 / 代理 ----------------

CONFIG_PATH = os.path.join(base_dir(), "config.json")
BOOKMARKS_PATH = os.path.join(base_dir(), "bookmarks.json")


def _load_json(path, default):
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _save_json(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_config():
    """读取本地配置文件（代理、主题等）"""
    cfg = _load_json(CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def save_config(**kw):
    """保存配置项，返回更新后的完整配置"""
    cfg = get_config()
    cfg.update(kw)
    _save_json(CONFIG_PATH, cfg)
    return cfg


def get_proxy():
    """读取已保存的代理地址（网页设置界面写入）"""
    return str(get_config().get("proxy", "") or "").strip()


def set_proxy(proxy):
    """保存代理地址，空值表示清除"""
    proxy = str(proxy or "").strip()
    save_config(proxy=proxy)
    return proxy


def list_bookmarks():
    """书签列表：[{id, title, time}]，最新在前"""
    items = _load_json(BOOKMARKS_PATH, [])
    return items if isinstance(items, list) else []


def add_bookmark(album_id, title=""):
    """添加书签，已存在返回 False"""
    album_id = normalize_id(album_id)
    items = list_bookmarks()
    for it in items:
        if it.get("id") == album_id:
            return False
    import time
    items.insert(0, {"id": album_id, "title": str(title or ""), "time": int(time.time())})
    _save_json(BOOKMARKS_PATH, items)
    return True


def remove_bookmark(album_id):
    """删除书签，返回是否删除了某项"""
    album_id = normalize_id(album_id)
    items = list_bookmarks()
    new = [it for it in items if it.get("id") != album_id]
    _save_json(BOOKMARKS_PATH, new)
    return len(items) != len(new)


def is_bookmarked(album_id):
    """判断某本是否已在书签中"""
    try:
        album_id = normalize_id(album_id)
    except Exception:
        return False
    return any(it.get("id") == album_id for it in list_bookmarks())


# ================= v1.0.4 =================
# 定时下载 / 追更订阅 / 封面墙 / 局域网 IP

TIMERS_PATH = os.path.join(base_dir(), "timers.json")
SUB_STATE_PATH = os.path.join(base_dir(), "subscribe_state.json")
COVERS_DIR = os.path.join(base_dir(), "covers")


def _now_str(fmt="%Y-%m-%d %H:%M"):
    import time
    return time.strftime(fmt)


# ---------- 定时下载 ----------

def list_timers():
    items = _load_json(TIMERS_PATH, [])
    return items if isinstance(items, list) else []


def add_timer(album_id, hhmm="00:00", tag=""):
    """新增定时任务：每天 hhmm（HH:MM）自动下载 album_id"""
    album_id = normalize_id(album_id)
    if not re.fullmatch(r"\d{2}:\d{2}", str(hhmm or "")):
        raise ValueError("时间格式应为 HH:MM，例如 22:30")
    items = list_timers()
    t = {"id": album_id, "time": hhmm, "tag": str(tag or ""), "last_run": "", "enabled": True}
    items = [it for it in items if it["id"] != album_id]  # 同一本只保留一个定时
    items.append(t)
    _save_json(TIMERS_PATH, items)
    return t


def remove_timer(album_id):
    album_id = normalize_id(album_id)
    items = list_timers()
    new = [it for it in items if it["id"] != album_id]
    _save_json(TIMERS_PATH, new)
    return len(items) != len(new)


def run_due_timers():
    """检查并触发所有到点且今天未执行的定时任务，返回触发的列表"""
    import time
    now_hm = time.strftime("%H:%M")
    today = time.strftime("%Y-%m-%d")
    fired = []
    items = list_timers()
    for it in items:
        if not it.get("enabled", True):
            continue
        if it.get("time") == now_hm and it.get("last_run") != today:
            it["last_run"] = today
            fired.append(it)
            _set_state(msg=f"⏰ 定时任务触发：自动下载 JM{it['id']}")
            try:
                if get_state()["running"]:
                    _set_state(msg=f"⏰ JM{it['id']} 定时任务等待队列...")
                    threading.Thread(target=_download_worker, args=(it["id"],), daemon=True).start()
                else:
                    start_download(it["id"])
            except Exception as e:
                traceback.print_exc()
    if fired:
        _save_json(TIMERS_PATH, items)
    return [{"id": t["id"], "time": t["time"]} for t in fired]


# ---------- 追更订阅 ----------

def set_subscribe(album_id, on=True):
    """把书签标记为追更/取消追更（自动下载新章节用）"""
    album_id = normalize_id(album_id)
    items = list_bookmarks()
    for it in items:
        if it.get("id") == album_id:
            it["sub"] = bool(on)
            _save_json(BOOKMARKS_PATH, items)
            return True
    # 不在书签里则自动加入书签并订阅
    add_bookmark(album_id)
    items = list_bookmarks()
    for it in items:
        if it.get("id") == album_id:
            it["sub"] = bool(on)
            _save_json(BOOKMARKS_PATH, items)
            return True
    return False


def check_subscriptions():
    """检查所有追更书签是否有更新（对比本地记录的最近更新时间）

    返回 [{'id','title','old_time','new_time'}]，并同步订阅状态文件
    """
    import time
    st = _load_json(SUB_STATE_PATH, {}) or {}
    updates = []
    for bm in list_bookmarks():
        if not bm.get("sub"):
            continue
        aid = bm["id"]
        try:
            a = about(aid)
            new_time = str(a.get("update_time") or a.get("time") or "")
            if not new_time:
                continue
            old = st.get(aid, "")
            if old and old != new_time:
                updates.append({"id": aid, "title": a.get("title", bm.get("title", "")),
                                "old_time": old, "new_time": new_time})
            st[aid] = new_time
        except Exception:
            pass
    _save_json(SUB_STATE_PATH, st)
    return updates


# ---------- 封面墙 ----------

def export_covers():
    """把已下载漫画的封面复制到 covers/ 并生成封面墙 HTML，返回 (html_path, count)"""
    ensure_dirs()
    os.makedirs(COVERS_DIR, exist_ok=True)
    html_path = os.path.join(COVERS_DIR, "covers_wall.html")
    cards = []
    n = 0
    if os.path.isdir(DOWNLOADS_DIR):
        for aid in sorted(os.listdir(DOWNLOADS_DIR), key=lambda x: int(x) if x.isdigit() else 0, reverse=True):
            adir = os.path.join(DOWNLOADS_DIR, aid)
            if not os.path.isdir(adir) or not aid.isdigit():
                continue
            imgs = sorted(f for f in os.listdir(adir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")))
            if not imgs:
                continue
            src = os.path.join(adir, imgs[0])
            dst = os.path.join(COVERS_DIR, f"{aid}.jpg")
            try:
                shutil.copyfile(src, dst)
                total = _count_images(adir)
                cards.append(f'<a class="c" href="../downloads/{aid}/" target="_blank">'
                             f'<img loading="lazy" src="{aid}.jpg"><span>JM{aid} · {total}P</span></a>')
                n += 1
            except Exception:
                pass
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>📚 我的封面墙（{n} 本）</title><style>
body{{margin:0;background:#0f1117;color:#e8eaf0;font-family:system-ui}}
h1{{text-align:center;padding:18px;font-size:20px;color:#9aa0b0}}
.wall{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;padding:0 18px 30px}}
.c{{text-decoration:none;color:#e8eaf0;text-align:center}}
.c img{{width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:8px;background:#171a23}}
.c span{{display:block;font-size:12px;margin-top:6px;color:#9aa0b0}}</style></head>
<body><h1>📚 我的封面墙 · 共 {n} 本</h1><div class="wall">{"".join(cards)}</div></body></html>"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path, n


# ---------- 局域网 IP（远程控制提示） ----------

def get_lan_ip():
    """获取本机局域网 IP，方便手机远程访问"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
