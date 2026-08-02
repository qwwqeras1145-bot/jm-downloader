# -*- coding: utf-8 -*-
"""
JM Downloader Web 控制台（单文件版，无需额外依赖）
功能：搜索 / 排行榜 / 随机推荐 / 详情查询 / 单本下载 / 批量导入下载 / 历史记录
"""
import json
import os
import sys
import threading
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

PORT = 8123

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JM Downloader 控制台</title>
<style>
:root{--bg:#0f1117;--card:#171a23;--card2:#1d2130;--fg:#e8eaf0;--dim:#9aa0b0;
--accent:#ff6b9d;--accent2:#8b5cf6;--ok:#34d399;--err:#f87171;--line:#262b3a}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:"Segoe UI","Microsoft YaHei",sans-serif;padding:24px}
.wrap{max-width:1100px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}
h1 span{color:var(--accent)}
.sub{color:var(--dim);font-size:13px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input[type=text],textarea,select{background:var(--card2);border:1px solid var(--line);color:var(--fg);
border-radius:8px;padding:9px 12px;font-size:14px;outline:none}
input[type=text]{flex:1;min-width:200px}
textarea{width:100%;height:70px;resize:vertical;margin-top:8px;font-size:13px}
button{background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;color:#fff;
border-radius:8px;padding:9px 18px;font-size:14px;cursor:pointer;transition:.15s}
button:hover{filter:brightness(1.15)}
button.ghost{background:var(--card2);border:1px solid var(--line);color:var(--fg)}
button.small{padding:5px 12px;font-size:12px}
button:disabled{opacity:.5;cursor:not-allowed}
.tabs{display:flex;gap:8px;margin-bottom:14px}
.tabs button{border-radius:20px;padding:6px 16px;font-size:13px;background:var(--card2);border:1px solid var(--line)}
.tabs button.on{background:linear-gradient(135deg,var(--accent),var(--accent2));border-color:transparent}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
.item{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:10px;cursor:pointer;transition:.15s}
.item:hover{border-color:var(--accent)}
.item .id{color:var(--accent);font-size:12px;font-weight:700}
.item .t{font-size:13px;margin:6px 0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:36px}
.item .a{color:var(--dim);font-size:11px}
#status{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:16px;
display:none;font-size:14px;white-space:pre-line}
#status .bar{height:6px;background:var(--card2);border-radius:3px;margin-top:8px;overflow:hidden}
#status .bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .4s}
#resultsTitle{color:var(--dim);font-size:13px;margin:14px 0 8px}
.batch-list{margin-top:10px;font-size:13px}
.batch-list .ok{color:var(--ok)}
.batch-list .no{color:var(--err)}
.hint{color:var(--dim);font-size:12px;margin-top:6px}
a{color:var(--accent)}
.detail{font-size:13px;line-height:1.9;color:var(--dim)}
.detail b{color:var(--fg)}
</style>
</head>
<body>
<div class="wrap">
  <h1>JM <span>Downloader</span></h1>
  <div class="sub">禁漫本地下载工具 · exe 版 · 下载内容保存到程序旁的 downloads 文件夹</div>

  <div class="card">
    <div class="row">
      <input type="text" id="kw" placeholder="搜索关键词，例如：无职转生">
      <button onclick="doSearch()">搜索</button>
      <button class="ghost" onclick="doRandom()">🎲 随机</button>
    </div>
    <div class="tabs" id="tabs" style="margin-top:12px">
      <button onclick="doTop('week')">本周排行</button>
      <button onclick="doTop('month')">本月排行</button>
      <button onclick="doTop('day')">今日排行</button>
    </div>
  </div>

  <div class="card">
    <div class="row"><b style="font-size:14px">📥 批量导入下载</b></div>
    <textarea id="batchIds" placeholder="每行一个漫画 ID，例如：&#10;1114751&#10;123456&#10;789012"></textarea>
    <div class="row" style="margin-top:8px">
      <button onclick="doBatch()">🚀 批量下载</button>
      <button class="ghost" onclick="loadHistory()">📚 下载历史</button>
      <span class="hint">支持空格 / 逗号 / 换行分隔 ID</span>
    </div>
  </div>

  <div id="status"></div>
  <div id="resultsTitle"></div>
  <div class="grid" id="grid"></div>
</div>
<script>
let pollTimer=null;
async function api(url,opts){
  const r=await fetch(url,opts);const j=await r.json();
  if(!r.ok)throw new Error(j.error||'请求失败');
  return j;
}
function esc(s){return (s||'').toString().replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function showItems(list){
  const g=document.getElementById('grid');
  if(!list||!list.length){g.innerHTML='<div class="sub">没有结果</div>';return;}
  g.innerHTML=list.map(it=>`
    <div class="item" onclick="doAbout('${it.id}')">
      <div class="id">JM${esc(it.id)}</div>
      <div class="t">${esc(it.title)}</div>
      <div class="a">${esc(it.author)} ${esc(it.category)}</div>
    </div>`).join('');
}
function showStatus(s){
  const el=document.getElementById('status');
  if(!s.running&&!s.done){el.style.display='none';return;}
  el.style.display='block';
  let html=esc(s.msg||'');
  if(s.total>0){
    const pct=Math.min(100,Math.round(s.current/s.total*100));
    html+=`<div class="bar"><i style="width:${pct}%"></i></div>`;
  }
  if(s.done&&s.ok){
    if(s.zip_path) html+=`<br><a href="/api/file?p=${encodeURIComponent(s.zip_path)}" target="_blank">⬇️ 下载 ZIP 压缩包</a>`;
  }
  if(s.done&&!s.ok) html+=`<br><span style="color:var(--err)">${esc(s.error||'下载失败')}</span>`;
  if(s.batch&&s.results&&s.results.length){
    html+='<div class="batch-list">'+s.results.map(r=>`<div class="${r.ok?'ok':'no'}">JM${esc(r.id)}：${r.ok?('✅ '+r.files+' 张'):('❌ '+(r.error||'失败'))} ${r.zip?'<a href="/api/file?p='+encodeURIComponent(r.zip)+'" target="_blank">⬇️</a>':''}</div>`).join('')+'</div>';
  }
  el.innerHTML=html;
}
async function pollStatus(){
  try{
    const s=await api('/api/status');
    showStatus(s);
    if(s.running&&!s.done){pollTimer=setTimeout(pollStatus,1500);}
  }catch(e){console.error(e)}
}
async function doSearch(){
  const kw=document.getElementById('kw').value.trim();
  if(!kw)return;
  document.getElementById('resultsTitle').textContent=`搜索「${kw}」...`;
  try{
    const j=await api('/api/search?kw='+encodeURIComponent(kw));
    document.getElementById('resultsTitle').textContent=`搜索「${kw}」结果 ${j.list.length} 条`;
    showItems(j.list);
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
async function doTop(kind){
  document.getElementById('resultsTitle').textContent='加载排行中...';
  try{
    const j=await api('/api/top?kind='+kind);
    document.getElementById('resultsTitle').textContent='排行结果 '+j.list.length+' 条';
    showItems(j.list);
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
async function doRandom(){
  try{
    const j=await api('/api/random');
    document.getElementById('kw').value=j.id;
    document.getElementById('resultsTitle').textContent=`🎲 随机推荐：JM${j.id} ${j.title}`;
    showItems([j]);
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
async function doAbout(id){
  document.getElementById('resultsTitle').textContent='查询中...';
  try{
    const j=await api('/api/about?id='+id);
    const a=j.info;
    const g=document.getElementById('grid');
    g.innerHTML=`<div class="item" style="grid-column:1/-1;cursor:default">
      <div class="id">JM${esc(a.id)}</div>
      <div class="t" style="min-height:0;font-size:16px">${esc(a.title)}</div>
      <div class="detail">
        作者：<b>${esc(a.author)}</b>　分类：<b>${esc(a.category)}</b>　页数：<b>${a.pages}</b><br>
        点赞：<b>${a.likes}</b>　浏览：<b>${a.views}</b><br>
        标签：<b>${esc((a.tags||[]).slice(0,12).join(' / '))}</b><br>
        ${esc((a.description||'').slice(0,200))}
      </div>
      <button style="margin-top:10px" onclick="startDl('${a.id}')">⬇️ 下载这本</button>
    </div>`;
    document.getElementById('resultsTitle').textContent=`JM${a.id} 详情`;
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
async function startDl(id){
  try{
    await api('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
    pollStatus();
  }catch(e){showStatus({running:true,done:false,msg:'⚠️ '+e.message,total:0,current:0})}
}
async function doBatch(){
  const raw=document.getElementById('batchIds').value;
  const ids=[...new Set(raw.split(/[\\s,\\uff0c;\\n]+/).map(s=>s.trim()).filter(Boolean))];
  if(!ids.length){showStatus({running:true,done:false,msg:'⚠️ 请输入漫画 ID',total:0,current:0});return;}
  try{
    const j=await api('/api/batch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
    document.getElementById('resultsTitle').textContent=`已加入 ${j.total} 本批量下载任务`;
    pollStatus();
  }catch(e){showStatus({running:true,done:false,msg:'⚠️ '+e.message,total:0,current:0})}
}
async function loadHistory(){
  try{
    const j=await api('/api/history');
    const list=j.items||[];
    document.getElementById('resultsTitle').textContent=`本地已下载 ${list.length} 本`;
    showItems(list.map(it=>({id:it.id,title:it.id+' · '+it.files+' 张',author:'',category:''})));
    if(list.length){
      const g=document.getElementById('grid');
      g.innerHTML=list.map(it=>`
        <div class="item" style="cursor:default">
          <div class="id">JM${esc(it.id)}</div>
          <div class="t" style="min-height:0">本地 ${it.files} 张图片</div>
          <div class="a">${it.zip?`<a href="/api/file?p=${encodeURIComponent(it.zip)}">⬇️ ZIP</a>`:'未打包'}</div>
        </div>`).join('');
    }
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
</script>
</body>
</html>
"""


def build_handler() -> type:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        # noinspection PyPep8Naming
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                if path == "/" or path == "/index.html":
                    self._send_html(HTML)
                elif path == "/api/search":
                    self._send_json({"list": core.search(qs.get("kw", [""])[0], int(qs.get("page", ["1"])[0]))})
                elif path == "/api/top":
                    self._send_json({"list": core.top(qs.get("kind", ["week"])[0], int(qs.get("page", ["1"])[0]))})
                elif path == "/api/random":
                    self._send_json(core.random_album())
                elif path == "/api/about":
                    self._send_json({"info": core.about(qs.get("id", [""])[0])})
                elif path == "/api/status":
                    self._send_json(core.get_state())
                elif path == "/api/history":
                    self._send_json({"items": core.history()})
                elif path == "/api/file":
                    self._send_file(qs.get("p", [""])[0])
                else:
                    self._send_json({"error": "404"}, 404)
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)

        # noinspection PyPep8Naming
        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}") if length else {}
                if self.path == "/api/download":
                    aid = body.get("id", "")
                    if not aid:
                        self._send_json({"error": "缺少漫画 ID"}, 400)
                        return
                    core.start_download(aid)
                    self._send_json({"ok": True})
                elif self.path == "/api/batch":
                    ids = body.get("ids") or []
                    total = core.start_batch(ids)
                    self._send_json({"ok": True, "total": total})
                else:
                    self._send_json({"error": "404"}, 404)
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)

        def _send_html(self, html: str):
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, obj, code=200):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_file(self, path: str):
            if not path or not os.path.isfile(path):
                self._send_json({"error": "文件不存在"}, 404)
                return
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return Handler


def start_web(port=PORT):
    """启动 Web 服务，返回 (server, port)"""
    srv = ThreadingHTTPServer(("127.0.0.1", port), build_handler())
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port
