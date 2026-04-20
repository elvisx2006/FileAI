# FileAI — AI 智能文件整理工具

<div align="center">

**macOS & Windows 双平台 · DeepSeek / OpenAI / Gemini 多模型 · iOS 风格 UI**

[![Build](https://github.com/elvisx2006/FileAI/actions/workflows/build.yml/badge.svg)](https://github.com/elvisx2006/FileAI/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/elvisx2006/FileAI)](https://github.com/elvisx2006/FileAI/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## 功能特性

- **智能扫描** — 一键扫描配置的监控目录中的文件（默认 Downloads / Desktop / Documents），**默认递归子文件夹**；自动跳过整理目标目录、可选跳过项目根（含 `package.json` / `.git` 等）
- **自定义监控路径** — 在应用「**设置**」中增删监控目录、修改整理目标；支持一键添加 **iCloud Drive** 路径
- **iCloud 占位符**（macOS）— 识别仅云端的 `*.icloud` 占位文件；**确认执行**前会提示，执行时通过 `brctl download` 尝试拉取到本地后再移动
- **两级分类** — 规则引擎（免费快速）+ AI 深度分类（智能精准）
- **30+ 分类目录** — 按类型、项目、用途细粒度归档
- **预览确认** — 展示置信度和分类理由，确认后再执行
- **一键撤销** — 所有操作可逐条撤销
- **实时进度** — 分类和执行均有实时进度条
- **错误详情** — 失败文件展示具体原因，支持一键复制
- **单实例后端** — 桌面版启动前会尝试释放本机 **8000** 端口，降低「端口已被占用」导致的启动失败

---

## 下载安装

### macOS

**系统要求**：macOS 10.15+（Apple Silicon M1/M2/M3/M4）

1. 前往 [**Releases**](https://github.com/elvisx2006/FileAI/releases/latest) 下载 `FileAI_x.x.x_aarch64.dmg`（具体版本号以发布页为准）
2. 双击 `.dmg` 打开，将 **FileAI** 拖入 **Applications（应用程序）** 文件夹
3. **打开终端，执行以下命令解除系统安全限制（必须）：**

```bash
xattr -cr /Applications/FileAI.app
```

4. 双击 FileAI.app 启动即可

> **为什么需要执行这条命令？**
> macOS Gatekeeper 会对未经 Apple 官方签名的应用添加隔离标志，执行上面的命令可以清除该标志，应用本身是安全的。

---

### Windows

**系统要求**：Windows 10 / 11（64 位）

1. 前往 [**Releases**](https://github.com/elvisx2006/FileAI/releases/latest) 下载 `FileAI_x.x.x_x64-setup.exe`
2. 双击运行安装程序，按提示完成安装
3. 从开始菜单或桌面快捷方式启动 FileAI

> **如果 Windows Defender 弹出安全警告：** 点击「更多信息」→「仍要运行」即可，原因与 macOS 相同（未购买代码签名证书）。

---

## 配置 AI

首次使用需要配置一个 AI API Key，推荐使用 **DeepSeek**（费用极低）。

| 模型 | 获取地址 | 费用 |
|------|---------|------|
| **DeepSeek**（推荐） | https://platform.deepseek.com | 极低，约 ¥0.001/次 |
| OpenAI | https://platform.openai.com | 较高 |
| Gemini | https://aistudio.google.com | 有免费额度 |

1. 复制 `backend/.env.example` 为 `backend/.env`（若仓库中无 example，可直接新建 `backend/.env`）
2. 在 `.env` 中填入对应服务商的 API Key（如 `DEEPSEEK_API_KEY=`）
3. 可选：编辑 `backend/config.yaml` 中的 `ai.provider`、`ai.model` 等（保存后重启后端生效）

> 切换模型与 provider 的说明见应用内「设置」页面底部提示。

---

## 监控目录与 iCloud Drive

- 打开应用 **「设置」**，可编辑 **监控目录**、**整理目标**与 **扫描行为**（扫描深度、是否跳过项目目录、整理后是否删除空文件夹）。保存后会写入 `backend/config.yaml`。
- 点击 **「添加 iCloud Drive」** 会加入路径：  
  `~/Library/Mobile Documents/com~apple~CloudDocs`  
  （若系统未登录 iCloud 或路径不存在，仍可手动粘贴其他路径。）
- **建议**：若希望减少跨盘同步流量，可将 **整理目标** 也设为 iCloud 下的某个子文件夹（例如 iCloud Drive 内的 `Organized`）。
- **仅云端文件**：macOS 上未完全下载的文件可能以 `*.icloud` 形式存在；列表中会显示云图标。执行整理前会二次确认；下载依赖网络与 `brctl`（随系统提供）。**整理前**也可在 Finder 中对文件夹使用 **「立即下载」**，尽量先本地化。

---

## 使用流程

```
（可选）设置监控目录 / 整理目标 → 扫描文件 → AI 分类 → 预览结果 → 确认执行 → 完成
```

1. 在 **「设置」** 中按需调整监控目录、整理目标与扫描选项（或使用默认）
2. 在 **「整理文件」** 点击「**扫描目录**」，递归扫描当前配置下的所有监控目录（列表按子文件夹分组，可折叠、可按文件夹全选）
3. 点击「**AI 分类**」，等待分类完成（有实时进度条）
4. 查看分类预览（绿=高置信度，黄=中等，红=低）
5. 点击「**确认执行**」，文件移动到配置中的 **整理目标** 下（默认 `~/Organized/`）

---

## 整理后的目录结构

```
~/Organized/
├── Documents/
│   ├── Work/           ← 报告、演示文稿、合同
│   ├── Personal/       ← 财务、医疗、简历
│   └── Study/          ← 笔记、论文、电子书
├── Images/
│   ├── Screenshots/    ← 按月份归档
│   ├── Photos/
│   └── Design/
├── Videos/
├── Code/
├── Audio/
├── Archives/
├── Design/
├── Installers/
└── Misc/Needs_Review/  ← AI 不确定的文件
```

（若你修改了「整理目标」路径，则根目录为所设路径，子结构不变。）

---

## 从源码运行

```bash
# 克隆项目
git clone https://github.com/elvisx2006/FileAI.git
cd FileAI

# 安装后端依赖
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # 编辑填入 API Key
cd ..

# 启动后端
python run_server.py

# 新终端，启动前端
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

> macOS 从源码运行时，如遇 `.so` 文件被拦截，执行：`xattr -cr backend/venv`

---

## 常见问题

**Q：macOS 提示"文件已损坏"或"无法验证开发者"？**
A：执行 `xattr -cr /Applications/FileAI.app` 后重试。

**Q：Windows 安装后打开没反应？**
A：检查是否有杀毒软件拦截了后端进程（`fileai-backend.exe`），将其加入白名单即可。

**Q：AI 分类失败？**
A：检查 `backend/.env` 中 API Key 是否正确，以及账户是否有余额；确认后端日志无报错。

**Q：整理后的文件在哪里？**
A：默认 macOS 在 `~/Organized/`，Windows 在 `C:\Users\你的用户名\Organized\`；若在「设置」中修改了整理目标，则以设置为准。可在 App 的「已整理文件」页面直接浏览。

**Q：提示端口 8000 已被占用或 Load failed？**
A：不要同时多开多个会启动后端的实例（例如既开 FileAI.app 又用脚本启动 `run_server.py`）。关闭多余实例或结束占用 8000 的进程后重试；桌面版已会在启动 sidecar 前尝试释放该端口。

**Q：iCloud 文件整理失败或一直等待？**
A：确认已登录 iCloud、网络正常；占位符文件需下载到本地后才能移动。可在 Finder 中先「立即下载」再整理，或检查是否被系统限制访问「iCloud Drive」。

**Q：为什么某个开发/项目文件夹没有被扫描？**
A：默认开启「跳过项目目录」：若文件夹内含有 `package.json`、`pyproject.toml`、`.git` 等标记，会整棵树跳过，避免打乱工程结构。可在设置中关闭该选项（不推荐）。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 桌面壳 | Tauri 2 (Rust) |
| 前端 | React 19 + TypeScript + Vite + TailwindCSS |
| 后端 | Python + FastAPI + uvicorn |
| AI | DeepSeek / OpenAI / Gemini（统一 OpenAI SDK 接口） |
| 数据库 | SQLite (aiosqlite) |
| 通信 | REST API + WebSocket |
| 打包 | PyInstaller + Tauri Bundle + GitHub Actions |

---

## 最近更新（摘要）

- **v1.5.0**：**递归扫描**监控目录子文件夹；跳过整理目标与项目根目录；**Bundle**（`.app` / `.xcodeproj` 等）作为整体条目；整理后可选**清理空文件夹**；同名冲突使用 `名称 (2).ext`；设置页可配置扫描深度与开关；整理页按子文件夹分组展示。详见 [Releases](https://github.com/elvisx2006/FileAI/releases)。
- **v1.4.4**：与 **v1.4.3** 功能一致；README 与版本号对齐。
- **v1.4.3**：设置页路径、iCloud 占位符、端口与异步修复等。

---

MIT License
