# 📥 JM Downloader

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-GPL--3.0-green)
![Release](https://img.shields.io/github/v/release/qwwqeras1145-bot/jm-downloader)
![Stars](https://img.shields.io/github/stars/qwwqeras1145-bot/jm-downloader)


> 禁漫天堂（JM）Windows 本地下载工具 · 免安装单文件 exe · 网页图形界面 + 命令行双模式

基于开源库 [jmcomic](https://github.com/hect0x7/jmcomic) 封装，一键搜索、查看详情、批量下载并自动打包 ZIP，开箱即用，无需安装 Python 环境。

---

## ✨ 功能特性

| 功能 | 说明 |
|---|---|
| 🔍 **关键词搜索** | 按漫画标题/作者搜索，支持分页，默认每页 20 条 |
| 📈 **排行榜** | 日榜 / 周榜 / 月榜，随时看热门 |
| 📖 **详情查询** | 输入漫画 ID 查看作者、分类、页数、点赞、浏览量 |
| 🎲 **随机推荐** | 随机给你推荐一本，解决书荒 |
| ⬇️ **单本下载** | 输入 ID 一键下载全部原图 |
| 🚀 **批量下载** | 一次导入多个 ID 自动排队依次下载，中途失败自动跳过 |
| 📦 **自动 ZIP 打包** | 每本下载完成后自动压缩成 zip，方便保存/传阅 |
| 📚 **下载历史** | 记录已下载漫画，随时查看 |
| 🌐 **网页图形界面** | 浏览器操作，带实时进度条，零学习成本 |
| 📁 **本地管理** | 所有文件保存在 exe 同目录 `downloads/`，结构清晰 |
| 🌍 **代理支持** | 支持 HTTP/HTTPS 代理，网络环境受限也能用 |

---

## 🚀 快速开始（推荐）

### 方式一：双击 exe（最简单）

1. 下载 `jm-downloader.exe`（见下方 Release 链接）
2. **双击运行**，弹出模式选择菜单：

```
========== JM Downloader ==========
  1. 网页版图形界面（推荐）
  2. 命令行模式
  3. 退出
请输入序号：
```

3. 输入 `1` 回车，浏览器自动打开 **http://127.0.0.1:8123**，开始使用！

### 方式二：命令行直用

```
jm-downloader.exe search 无职转生            # 搜索
jm-downloader.exe top week                   # 周榜（week/month/day）
jm-downloader.exe about 1114751              # 查询详情
jm-downloader.exe dl 1114751                 # 下载并打包 ZIP
jm-downloader.exe batch 1114751 123456       # 批量下载多本
jm-downloader.exe random                     # 随机推荐
jm-downloader.exe web                        # 启动网页版
```

> 💡 命令行输出为 JSON 格式，方便脚本二次处理。

---

## 🌐 网页版界面详解

![网页版界面](docs/screenshot.png)

*JM Downloader 网页版图形界面*


打开 http://127.0.0.1:8123 后：

- **搜索框**：输入关键词回车，展示结果列表（标题/作者/分类/页数/点赞/浏览量），点 **下载** 按钮即可下载
- **排行榜**：一键切换日榜/周榜/月榜
- **随机推荐**：点一下随机出一本
- **下载进度**：页面实时显示下载进度条、当前章节、完成状态
- **下载历史**：列出已下载漫画，可下载对应 ZIP

> 🔧 端口默认 `8123`，若被占用会自动换端口并在控制台提示。

---

## 📁 下载内容位置

所有文件保存在 **exe 所在目录**：

```
jm-downloader.exe
downloads/
├── 1114751/          # 每本一个文件夹（原始图片）
│   ├── 001.jpg
│   ├── 002.jpg
│   └── ...
└── _zips/
    └── JM1114751.zip # 自动打包好的压缩包
```

- 原始图片目录：`downloads/{漫画ID}/`
- 打包 ZIP 目录：`downloads/_zips/JM{漫画ID}.zip`

---

## 🛠 从源码运行

需要 Python 3.9+：

```bash
pip install -r requirements.txt
python main.py              # 交互式启动器
python main.py web          # 网页版
python main.py gui          # 桌面图形界面（需 tkinter）
python main.py search 无职转生
python main.py dl 1114751
```

> ⚠️ 桌面 GUI（tkinter）需要系统自带 Python 的 `tkinter` 模块；若 `import tkinter` 失败，请使用网页版。

---

## 📦 打包成 exe

双击运行 `build.bat`（需已安装 Python + PyInstaller），产物输出到 `dist\jm-downloader.exe`：

```bash
pip install pyinstaller
build.bat
```

---

## 🌍 代理配置

网络受限时可设置环境变量（任选其一）：

| 变量 | 示例 |
|---|---|
| `JM_PROXY` | `http://127.0.0.1:7890` |
| `HTTP_PROXY` / `HTTPS_PROXY` | `http://127.0.0.1:7890` |

---

## ❓ 常见问题（FAQ）

**Q1：exe 被杀毒软件/Windows Defender 报毒？**
PyInstaller 单文件打包容易被误报（无签名 exe 通病）。可添加信任，或从源码运行、自行打包。

**Q2：双击 exe 弹出黑框闪退？**
可能是终端编码问题。请用命令行方式运行：打开 cmd 进入 exe 目录，执行 `jm-downloader.exe web` 查看具体报错。

**Q3：下载失败 / 超时？**
JM 服务器偶尔波动，可重试；或配置代理（见上文）。

**Q4：终端中文乱码？**
控制台执行 `chcp 65001` 切换 UTF-8 编码后重试。

**Q5：网页版打不开？**
确认 exe 窗口提示的端口，手动访问 http://127.0.0.1:8123 ；若端口被占用会自动切换，以控制台提示为准。

**Q6：下载目录在哪？**
默认在 exe 同目录 `downloads/` 下，按漫画 ID 分文件夹。

---

## 🧩 技术栈

- 下载引擎：[jmcomic](https://github.com/hect0x7/jmcomic)（GPL-3.0）
- 网页界面：Python 标准库 `http.server`，零额外 Web 依赖
- 桌面界面：Python 标准库 `tkinter`
- 打包：PyInstaller 单文件模式

---

## ⚖️ 许可证

本项目基于 [GPL-3.0](LICENSE) 发布。

## 📢 免责声明

本工具**仅用于个人学习与技术研究**，请勿用于商业用途；下载内容版权归原作者所有，请自觉遵守当地法律法规，支持正版。使用本工具产生的任何后果由使用者自行承担。
