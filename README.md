# JM Downloader（Windows exe 版）

禁漫天堂（JM）本地下载工具，双击即用，无需安装 Python。

- 🖥️ **图形界面**：桌面窗口操作
- 🌐 **网页版**：浏览器控制台（自动打开 http://127.0.0.1:8123）
- 🚀 **批量下载**：一次导入多个漫画 ID 依次下载
- 📦 **自动打包 ZIP**：每本下载完成后自动打包成 zip
- 📚 **下载历史**：查看本地已下载内容

## 快速开始

**方式一：双击 `jm-downloader.exe`** → 弹出模式选择 → 选"图形界面"或"网页版"

**方式二：命令行**

```
jm-downloader.exe gui                       # 图形界面
jm-downloader.exe web                       # 网页版
jm-downloader.exe search 无职转生           # 搜索
jm-downloader.exe top week                  # 周榜
jm-downloader.exe about 1114751             # 查询详情
jm-downloader.exe dl 1114751                # 下载并打包
jm-downloader.exe batch 1114751 123456      # 批量下载
jm-downloader.exe random                    # 随机推荐
```

## 下载内容位置

所有文件保存在 **exe 所在目录**：

```
jm-downloader.exe
downloads/
  1114751/          # 每本一个文件夹（原始图片）
  _zips/
    JM1114751.zip   # 自动打包好的压缩包
```

## 从源码运行

```bash
pip install -r requirements.txt
python main.py              # 启动器
python main.py gui          # 图形界面
python main.py web          # 网页版
```

## 打包成 exe

双击 `build.bat`，产物为 `dist\jm-downloader.exe`。

## 技术说明

- 基于开源库 [jmcomic](https://github.com/hect0x7/jmcomic)（GPL-3.0）
- 图形界面使用 Python 自带 tkinter，无额外依赖
- 支持代理：设置环境变量 `JM_PROXY` / `HTTPS_PROXY` / `HTTP_PROXY`

## 免责声明

本工具仅用于个人学习与技术研究，请勿用于商业用途；下载内容版权归原作者所有，请自觉遵守当地法律法规，支持正版。
