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
.bar{height:8px;background:var(--card2);border-radius:4px;overflow:hidden}
.bar .fill{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .5s}
a{color:var(--accent)}
.detail{font-size:13px;line-height:1.9;color:var(--dim)}
.detail b{color:var(--fg)}
#banner{background:linear-gradient(135deg,rgba(255,107,157,.15),rgba(139,92,246,.15));
border:1px solid var(--accent);border-radius:10px;padding:10px 14px;margin-bottom:14px;
font-size:13px;display:none}
#banner a{margin-left:8px}
#viewer{position:fixed;inset:0;background:rgba(5,6,10,.94);z-index:99;display:none;
flex-direction:column;align-items:center;justify-content:center;padding:20px}
#viewer.on{display:flex}
#viewer img{max-width:92vw;max-height:78vh;object-fit:contain;border-radius:6px;
box-shadow:0 8px 40px rgba(0,0,0,.6)}
#viewer .vtop{position:absolute;top:16px;left:0;right:0;display:flex;justify-content:center;
gap:10px;align-items:center;font-size:13px;color:var(--dim)}
#viewer .vbtn{background:var(--card2);border:1px solid var(--line);color:var(--fg);
border-radius:8px;padding:8px 16px;font-size:14px;cursor:pointer}
#viewer .vbtn:hover{border-color:var(--accent)}
#viewer .vclose{position:absolute;top:14px;right:18px;font-size:26px;cursor:pointer;
color:var(--dim);background:none;border:none}
#viewer .vclose:hover{color:var(--accent)}
#viewer .vcnt{color:var(--dim);font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <h1>JM <span>Downloader</span>
    <button id="themeBtn" class="ghost" style="float:right;padding:6px 14px" onclick="toggleTheme()">🌙 暗色</button>
  </h1>
  <div class="sub">禁漫本地下载工具 · exe 版 · 下载内容保存到程序旁的 downloads 文件夹</div>

  <div class="card">
    <div class="row">
      <input type="text" id="kw" placeholder="搜索关键词，例如：无职转生">
      <button onclick="doSearch()">搜索</button>
      <button class="ghost" onclick="doRandom()">🎲 随机</button>
    </div>
    <div class="hint" id="searchHis"></div>
    <div class="tabs" id="tabs" style="margin-top:12px">
      <button onclick="doTop('week')">本周排行</button>
      <button onclick="doTop('month')">本月排行</button>
      <button onclick="doTop('day')">今日排行</button>
    </div>
  </div>

  <div class="card">
    <div class="row"><b style="font-size:14px">📥 批量导入下载</b></div>
    <textarea id="batchIds" placeholder="每行一个漫画 ID，支持纯数字 / JM 前缀 / 完整链接：&#10;1114751&#10;JM123456&#10;https://18comic.vip/album/789012/"></textarea>
    <div class="row" style="margin-top:8px">
      <button onclick="doBatch()">🚀 批量下载</button>
      <button class="ghost" onclick="loadBookmarks()">⭐ 书签</button>
      <button class="ghost" onclick="loadHistory()">📚 下载历史</button>
      <button class="ghost" onclick="showCoversWall()">🖼️ 封面墙</button>
      <button class="ghost" onclick="loadTimers()">⏰ 定时</button>
      <button class="ghost" onclick="loadSubscriptions()">🔔 追更</button>
      <button class="ghost" onclick="toggleSettings()">⚙️ 设置</button>
      <span class="hint">支持空格 / 逗号 / 换行分隔，粘贴链接也能自动识别</span>
    </div>
  </div>

  <div class="card" id="queueCard" style="display:none">
    <div class="row"><b style="font-size:14px">📊 下载队列</b><span class="hint" id="queueHint" style="margin-left:auto"></span></div>
    <div class="bar" style="margin-top:10px"><div class="fill" id="queueFill" style="width:0%"></div></div>
    <div id="queueInfo" style="margin-top:8px;font-size:13px;color:var(--dim)"></div>
  </div>

  <div class="card" id="timerCard" style="display:none">
    <div class="row"><b style="font-size:14px">⏰ 定时下载</b></div>
    <div class="row" style="margin-top:10px">
      <input type="text" id="timerId" placeholder="JM 编号，例如 123456">
      <input type="time" id="timerTime" value="22:30" style="width:120px">
      <button onclick="addTimer()">➕ 添加定时</button>
    </div>
    <div id="timerList" style="margin-top:10px;font-size:13px;color:var(--dim)"></div>
    <div class="hint">到点自动下载该本，每天一次；可同时设置多本</div>
  </div>

  <div class="card" id="subCard" style="display:none">
    <div class="row"><b style="font-size:14px">🔔 追更订阅</b>
      <button class="ghost" style="margin-left:auto" onclick="checkSub()">🔄 检查更新</button></div>
    <div id="subList" style="margin-top:10px;font-size:13px;color:var(--dim)"></div>
    <div class="hint">已订阅的书签会自动记录更新时间，发现新章节会提示</div>
  </div>

  <div class="card" id="settingsCard" style="display:none">
    <div class="row"><b style="font-size:14px">⚙️ 设置</b></div>
    <div class="row" style="margin-top:10px">
      <input type="text" id="proxyInput" placeholder="代理地址，例如：http://127.0.0.1:7890（留空保存 = 清除）">
      <button onclick="saveProxy()">💾 保存代理</button>
      <button class="ghost" onclick="clearProxy()">🗑️ 清除</button>
    </div>
    <div class="hint" id="proxyHint">当前代理：未设置（下载失败或超时可尝试配置代理）</div>
    <div class="row" style="margin-top:12px">
      <span class="hint">🎨 主题色</span>
      <input type="color" id="accentColor" value="#8b5cf6" style="width:44px;height:30px;padding:2px;border:1px solid var(--line);border-radius:6px;background:transparent">
      <button class="ghost" onclick="resetTheme()">重置</button>
      <span class="hint" style="margin-left:14px">🌐 语言</span>
      <button class="ghost" onclick="setLang('zh')">中文</button>
      <button class="ghost" onclick="setLang('en')">EN</button>
    </div>
    <div class="hint" id="lanHint">📱 局域网访问：仅本机可访问</div>
  </div>

  <div id="banner"></div>
  <div id="status"></div>
  <div id="resultsTitle"></div>
  <div class="grid" id="grid"></div>
</div>

<div id="viewer">
  <button class="vclose" onclick="closeViewer()">✕</button>
  <div class="vtop">
    <button class="vbtn" onclick="vPrev()">◀ 上一张</button>
    <span class="vcnt" id="vcnt">0 / 0</span>
    <button class="vbtn" onclick="vNext()">下一张 ▶</button>
  </div>
  <img id="vimg" src="" alt="">
  <div style="margin-top:12px;color:var(--dim);font-size:12px" id="vhint">方向键 ← → 翻页，Esc 关闭</div>
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
  }else if(s.running){
    html+=`<div class="bar"><i style="width:58%"></i></div>`;
    if(s.current>0) html+=`<div style="color:var(--dim);font-size:12px;margin-top:4px">已获取 ${s.current} 张图片</div>`;
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
      <button class="ghost" style="margin-top:10px" onclick="addBm('${a.id}','${esc(a.title).replace(/'/g,'')}')">⭐ 收藏</button>
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
          <div class="t" style="min-height:0">${it.files} 张图片 · ${fmtSize(it.size||0)}</div>
          <div class="a">
            ${it.zip?`<a href="/api/file?p=${encodeURIComponent(it.zip)}">⬇️ ZIP</a>`:'未打包'}
            · <a href="#" onclick="viewAlbum('${esc(it.id)}');return false;">👁 查看</a>
            · <a href="#" onclick="openDir('${esc(it.id)}');return false;">📂 目录</a>
            · <a href="#" onclick="delItem('${esc(it.id)}');return false;" style="color:var(--err)">🗑️ 删除</a>
          </div>
        </div>`).join('');
    }
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
function fmtSize(n){
  if(n>=1048576) return (n/1048576).toFixed(1)+' MB';
  if(n>=1024) return (n/1024).toFixed(0)+' KB';
  return n+' B';
}
async function openDir(id){
  try{await api('/api/open?p='+encodeURIComponent(id));}
  catch(e){alert('⚠️ '+e.message)}
}
async function delItem(id){
  if(!confirm('确定删除 JM'+id+' 的本地文件吗？')) return;
  try{
    await api('/api/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
    loadHistory();
  }catch(e){alert('⚠️ '+e.message)}
}
// ---- v1.0.3 网页看图 ----
let vImgs=[],vIdx=0,vAid='';
async function viewAlbum(id){
  try{
    const j=await api('/api/images?p='+encodeURIComponent(id));
    vAid=id;vImgs=j.list||[];vIdx=0;
    if(!vImgs.length){alert('没有找到图片');return;}
    showV();
  }catch(e){alert('⚠️ '+e.message)}
}
function showV(){
  const el=document.getElementById('viewer');
  el.classList.add('on');
  document.getElementById('vimg').src='/api/img?p='+encodeURIComponent(vAid)+'&n='+encodeURIComponent(vImgs[vIdx]);
  document.getElementById('vcnt').textContent=(vIdx+1)+' / '+vImgs.length;
}
function vNext(){if(vIdx<vImgs.length-1){vIdx++;showV();}}
function vPrev(){if(vIdx>0){vIdx--;showV();}}
function closeViewer(){document.getElementById('viewer').classList.remove('on');}
document.addEventListener('keydown',e=>{
  if(!document.getElementById('viewer').classList.contains('on'))return;
  if(e.key==='ArrowRight')vNext();
  else if(e.key==='ArrowLeft')vPrev();
  else if(e.key==='Escape')closeViewer();
});
// ---- v1.0.3 自动检查更新 ----
(async function checkUpdate(){
  try{
    const j=await api('/api/check_update');
    const b=document.getElementById('banner');
    if(j.has_update){
      b.style.display='block';
      b.innerHTML=`🚀 发现新版本 <b>${esc(j.latest)}</b>（当前 ${esc(j.current)}）<a href="${esc(j.url)}" target="_blank">点击前往下载</a>`;
    }
  }catch(e){}
})();
// ---- v1.0.3 主题切换 ----
function applyTheme(t){
  const r=document.documentElement.style;
  if(t==='light'){
    r.setProperty('--bg','#f3f4f8');r.setProperty('--card','#ffffff');r.setProperty('--card2','#eef0f5');
    r.setProperty('--fg','#1c2030');r.setProperty('--dim','#6b7280');r.setProperty('--line','#d8dce6');
    document.getElementById('themeBtn').textContent='🌙 暗色';
  }else{
    r.setProperty('--bg','#0f1117');r.setProperty('--card','#171a23');r.setProperty('--card2','#1d2130');
    r.setProperty('--fg','#e8eaf0');r.setProperty('--dim','#9aa0b0');r.setProperty('--line','#262b3a');
    document.getElementById('themeBtn').textContent='☀️ 亮色';
  }
}
function toggleTheme(){
  const t=(localStorage.getItem('jm_theme')||'dark')==='dark'?'light':'dark';
  localStorage.setItem('jm_theme',t);applyTheme(t);
}
applyTheme(localStorage.getItem('jm_theme')||'dark');
// ---- v1.0.3 设置（代理） ----
function toggleSettings(){
  const c=document.getElementById('settingsCard');
  const show=c.style.display!=='block';
  c.style.display=show?'block':'none';
  if(show)loadProxy();
}
async function loadProxy(){
  try{
    const j=await api('/api/proxy');
    document.getElementById('proxyInput').value=j.proxy||'';
    document.getElementById('proxyHint').textContent=j.proxy?('当前代理：'+j.proxy):'当前代理：未设置（下载失败或超时可尝试配置代理）';
  }catch(e){}
}
async function saveProxy(){
  try{
    const v=document.getElementById('proxyInput').value.trim();
    await api('/api/proxy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proxy:v})});
    loadProxy();
    alert(v?'✅ 代理已保存：'+v:'✅ 代理已清除');
  }catch(e){alert('⚠️ '+e.message)}
}
async function clearProxy(){
  document.getElementById('proxyInput').value='';
  saveProxy();
}
// ---- v1.0.3 书签 ----
async function loadBookmarks(){
  try{
    const j=await api('/api/bookmarks');
    const list=j.items||[];
    document.getElementById('resultsTitle').textContent=`⭐ 我的书签 ${list.length} 个`;
    const g=document.getElementById('grid');
    if(!list.length){g.innerHTML='<div class="sub">还没有书签，搜索点进详情后点「⭐ 收藏」即可添加</div>';return;}
    g.innerHTML=list.map(it=>`
      <div class="item" onclick="doAbout('${esc(it.id)}')">
        <div class="id">JM${esc(it.id)}</div>
        <div class="t" style="min-height:0">${esc(it.title||'(无标题)')}</div>
        <div class="a">
          ${it.sub?'<span style="color:var(--ok)">🔔 追更中</span>':'<a href="#" onclick="subIt(\''+esc(it.id)+'\');return false;">🔔 追更</a>'}
          <a href="#" onclick="unBook('${esc(it.id)}');return false;" style="color:var(--err)">✖ 取消收藏</a>
        </div>
      </div>`).join('');
  }catch(e){document.getElementById('resultsTitle').textContent='⚠️ '+e.message}
}
async function addBm(id,title){
  try{
    await api('/api/bookmarks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,title})});
    alert('⭐ 已加入书签 JM'+id);
  }catch(e){alert('⚠️ '+e.message)}
}
async function unBook(id){
  try{
    await api('/api/bookmarks',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
    loadBookmarks();
  }catch(e){alert('⚠️ '+e.message)}
}
// ================= v1.0.4 =================
// 多语言
const I18N={
  zh:{search:'🔍 搜索',random:'🎲 随机',batch:'🚀 批量下载',bookmark:'⭐ 书签',history:'📚 下载历史',covers:'🖼️ 封面墙',timer:'⏰ 定时',sub:'🔔 追更',settings:'⚙️ 设置',viewer:'👁 查看',download:'⬇️ 下载这本',favorite:'⭐ 收藏',clear:'🗑️ 清除',save:'💾 保存代理'},
  en:{search:'🔍 Search',random:'🎲 Random',batch:'🚀 Batch DL',bookmark:'⭐ Bmarks',history:'📚 History',covers:'🖼️ Covers',timer:'⏰ Timers',sub:'🔔 Subs',settings:'⚙️ Settings',viewer:'👁 View',download:'⬇️ Download',favorite:'⭐ Fav',clear:'🗑️ Clear',save:'💾 Save Proxy'}
};
function setLang(l){localStorage.setItem('jm_lang',l);location.reload();}
function t(key){const l=localStorage.getItem('jm_lang')||'zh';return (I18N[l]||I18N.zh)[key]||key;}
// 主题色自定义
function applyAccent(color){
  document.documentElement.style.setProperty('--accent',color);
  const el=document.getElementById('accentColor');if(el)el.value=color;
  localStorage.setItem('jm_accent',color);
}
function resetTheme(){localStorage.removeItem('jm_accent');applyAccent('#ff6b9d');}
applyAccent(localStorage.getItem('jm_accent')||'#ff6b9d');
(function(){const el=document.getElementById('accentColor');if(el)el.addEventListener('input',e=>applyAccent(e.target.value));})();
// 局域网访问提示
(async function(){try{
  const j=await api('/api/netinfo');
  document.getElementById('lanHint').textContent='📱 局域网访问：http://'+j.ip+':'+j.port+'（手机连同一 WiFi 即可远程操作）';
}catch(e){}})();
// 下载队列面板（轮询）
let qTimer=null;
function toggleQueue(){
  const c=document.getElementById('queueCard');
  const show=c.style.display!=='block';
  c.style.display=show?'block':'none';
  if(show){pollQueue();qTimer=setInterval(pollQueue,1500);}
  else{clearInterval(qTimer);}
}
async function pollQueue(){
  try{
    const s=await api('/api/status');
    const c=document.getElementById('queueCard');
    if(c.style.display!=='block')return;
    const f=document.getElementById('queueFill'),info=document.getElementById('queueInfo'),hint=document.getElementById('queueHint');
    if(!s.running){f.style.width='0%';hint.textContent='';info.textContent=s.msg||'🆓 空闲中';return;}
    if(s.batch){
      f.style.width=Math.round((s.queue_done/s.queue_total||0)*100)+'%';
      hint.textContent=`第 ${s.queue_done}/${s.queue_total} 本`;
    }else{
      f.style.width=s.total?Math.round((s.current/s.total)*100)+'%':'0%';
      hint.textContent='单本下载中';
    }
    info.innerHTML=(s.msg||'')+'<br>'+(s.results||[]).map(r=>'<span class="'+(r.ok?'ok':'no')+'">'+(r.ok?'✅':'❌')+' JM'+esc(r.id)+(r.ok?(' '+r.files+'P'):' '+esc(r.error||''))+'</span>').join(' ');
  }catch(e){}
}
// 定时下载
async function loadTimers(){
  try{
    const j=await api('/api/timers');
    document.getElementById('timerCard').style.display='block';
    document.getElementById('timerList').innerHTML=j.items.length
      ?j.items.map(x=>'⏰ JM'+esc(x.id)+' 每天 '+esc(x.time)+' <a href="#" onclick="delTimer(\''+esc(x.id)+'\');return false;">✖</a>').join('<br>')
      :'还没有定时任务，填编号和时间即可添加';
  }catch(e){}
}
async function addTimer(){
  const id=document.getElementById('timerId').value.trim();
  const time=document.getElementById('timerTime').value||'22:30';
  if(!id){alert('请输入 JM 编号');return;}
  try{
    await api('/api/timers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,time})});
    loadTimers();
  }catch(e){alert('⚠️ '+e.message)}
}
async function delTimer(id){
  await api('/api/timers',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  loadTimers();
}
// 追更订阅
async function loadSubscriptions(){
  try{
    const j=await api('/api/subscriptions');
    document.getElementById('subCard').style.display='block';
    const list=j.items||[];
    document.getElementById('subList').innerHTML=list.length
      ?list.map(b=>'🔔 JM'+esc(b.id)+' '+(b.title?esc(b.title):'')+' <a href="#" onclick="unSub(\''+esc(b.id)+'\');return false;">取消</a>').join('<br>')
      :'还没有追更订阅，书签页点「🔔 追更」即可';
  }catch(e){document.getElementById('subList').textContent='⚠️ '+e.message;}
}
async function subIt(id){
  await api('/api/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,on:true})});
  loadBookmarks();
}
async function unSub(id){
  await api('/api/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,on:false})});
  loadSubscriptions();loadBookmarks();
}
async function checkSub(){
  try{
    const j=await api('/api/sub_check');
    const u=j.updates||[];
    alert(u.length?('🔔 有 '+u.length+' 本更新了！\n'+u.map(x=>'JM'+x.id+' '+(x.title||'')).join('\n')):'✅ 追更的漫画都没有更新');
  }catch(e){alert('⚠️ '+e.message)}
}
// 封面墙
async function showCoversWall(){
  try{
    const j=await api('/api/covers_wall');
    window.open('/api/covers_wall','_blank');
  }catch(e){alert('⚠️ '+e.message)}
}
// 搜索历史（本地保存最近 10 条）
function saveHistory(kw){
  if(!kw)return;
  let h=JSON.parse(localStorage.getItem('jm_search_his')||'[]');
  h=[kw,...h.filter(x=>x!==kw)].slice(0,10);
  localStorage.setItem('jm_search_his',JSON.stringify(h));
  renderHistory();
}
function renderHistory(){
  const h=JSON.parse(localStorage.getItem('jm_search_his')||'[]');
  const el=document.getElementById('searchHis');
  if(!el)return;
  el.innerHTML=h.length?('🔍 最近搜索：'+h.map(k=>'<a href="#" onclick="doSearchBy(\''+k.replace(/'/g,'')+'\');return false;">'+esc(k)+'</a>').join(' · ')):'';
}
function doSearchBy(kw){document.getElementById('kw').value=kw;doSearch();}
(function(){
  const el=document.getElementById('kw');
  el.addEventListener('keydown',e=>{if(e.key==='Enter')doSearch();});
})();
const _doSearchOrig=doSearch;
doSearch=function(){saveHistory(document.getElementById('kw').value.trim());_doSearchOrig();};
renderHistory();
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
                elif path == "/api/open":
                    core.open_dir(qs.get("p", [""])[0])
                    self._send_json({"ok": True})
                elif path == "/api/images":
                    self._send_json({"list": core.list_images(qs.get("p", [""])[0])})
                elif path == "/api/img":
                    self._send_image(qs.get("p", [""])[0], qs.get("n", [""])[0])
                elif path == "/api/check_update":
                    self._send_json(core.check_update())
                elif path == "/api/bookmarks":
                    self._send_json({"items": core.list_bookmarks()})
                elif path == "/api/proxy":
                    self._send_json({"proxy": core.get_proxy()})
                elif path == "/api/netinfo":
                    self._send_json({"ip": core.get_lan_ip(), "port": PORT})
                elif path == "/api/timers":
                    self._send_json({"items": core.list_timers()})
                elif path == "/api/subscriptions":
                    self._send_json({"items": [b for b in core.list_bookmarks() if b.get("sub")]})
                elif path == "/api/sub_check":
                    self._send_json({"updates": core.check_subscriptions()})
                elif path == "/api/covers_wall":
                    html_path, _n = core.export_covers()
                    data = open(html_path, "rb").read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
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
                elif self.path == "/api/delete":
                    core.delete_album(body.get("id", ""))
                    self._send_json({"ok": True})
                elif self.path == "/api/bookmarks":
                    core.add_bookmark(body.get("id", ""), body.get("title", ""))
                    self._send_json({"ok": True})
                elif self.path == "/api/proxy":
                    core.set_proxy(body.get("proxy", ""))
                    self._send_json({"ok": True})
                elif self.path == "/api/timers":
                    core.add_timer(body.get("id", ""), body.get("time", "22:30"))
                    self._send_json({"ok": True})
                elif self.path == "/api/subscribe":
                    core.set_subscribe(body.get("id", ""), bool(body.get("on", True)))
                    self._send_json({"ok": True})
                else:
                    self._send_json({"error": "404"}, 404)
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)

        # noinspection PyPep8Naming
        def do_DELETE(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8") or "{}") if length else {}
                if self.path == "/api/bookmarks":
                    core.remove_bookmark(body.get("id", ""))
                    self._send_json({"ok": True})
                elif self.path == "/api/proxy":
                    core.set_proxy("")
                    self._send_json({"ok": True})
                elif self.path == "/api/timers":
                    core.remove_timer(body.get("id", ""))
                    self._send_json({"ok": True})
                else:
                    self._send_json({"error": "404"}, 404)
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, 500)

        def _send_html(self, html: str):
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
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

        def _send_image(self, album_id: str, name: str):
            """返回专辑内的一张图片（仅限 downloads/{album_id} 内，防目录穿越）"""
            if not album_id or not name:
                self._send_json({"error": "缺少参数"}, 400)
                return
            album_dir = os.path.join(core.DOWNLOADS_DIR, os.path.basename(str(album_id)))
            real = os.path.realpath(os.path.join(album_dir, os.path.basename(str(name))))
            if not real.startswith(os.path.realpath(album_dir) + os.sep) or not os.path.isfile(real):
                self._send_json({"error": "图片不存在"}, 404)
                return
            ctype = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
            }.get(os.path.splitext(real)[1].lower(), "application/octet-stream")
            with open(real, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=3600")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return Handler


def start_web(port=PORT):
    """启动 Web 服务（监听 0.0.0.0，支持手机局域网远程访问），返回 (server, port)"""
    srv = ThreadingHTTPServer(("0.0.0.0", port), build_handler())

    def _timer_loop():
        """后台线程：每 30 秒检查定时下载任务"""
        import time
        while True:
            try:
                core.run_due_timers()
            except Exception:
                pass
            time.sleep(30)

    def _sub_init():
        """启动时建立追更订阅的更新时间基线"""
        try:
            core.check_subscriptions()
        except Exception:
            pass

    threading.Thread(target=_timer_loop, daemon=True).start()
    threading.Thread(target=_sub_init, daemon=True).start()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port
