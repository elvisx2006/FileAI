# FileAI — AI 智能文件整理工具

<div align="center">

**macOS & Windows 双平台 · DeepSeek / OpenAI / Gemini 多模型 · iOS 风格 UI**

[![Build](https://github.com/elvisx2006/FileAI/actions/workflows/build.yml/badge.svg)](https://github.com/elvisx2006/FileAI/actions/workflows/build.yml)
[![Release](https://img.shields.io/github/v/release/elvisx2006/FileAI)](https://github.com/elvisx2006/FileAI/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## 功能特性

- **智能扫描** — 一键扫描 Downloads / Desktop / Documents 中的所有文件
- **两级分类** — 规则引擎（免费快速）+ AI 深度分类（智能精准）
- **30+ 分类目录** — 按类型、项目、用途细粒度归档
- **预览确认** — 展示置信度和分类理由，确认后再执行
- **一键撤销** — 所有操作可逐条撤销
- **实时进度** — 分类和执行均有实时进度条
- **错误详情** — 失败文件展示具体原因，支持一键复制

---

## 下载安装

### macOS

**系统要求**：macOS 10.15+（Apple Silicon M1/M2/M3/M4）

1. 前往 [**Releases**](https://github.com/elvisx2006/FileAI/releases/latest) 下载 `FileAI_x.x.x_aarch64.dmg`
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

在 App 的**设置页面**填入 API Key 并选择对应模型即可。

---

## 使用流程

```
扫描文件 → AI 分类 → 预览结果 → 确认执行 → 完成
```

1. 点击「**扫描并整理**」，扫描 Downloads / Desktop / Documents
2. 点击「**AI 分类**」，等待分类完成（有实时进度条）
3. 查看分类预览（绿=高置信度，黄=中等，红=低）
4. 点击「**确认执行**」，文件移动到 `~/Organized/`（Windows 为 `C:\Users\你的用户名\Organized\`）

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
A：检查 API Key 是否正确，以及账户是否有余额。

**Q：整理后的文件在哪里？**
A：macOS 在 `~/Organized/`，Windows 在 `C:\Users\你的用户名\Organized\`，可在 App 的「已整理文件」页面直接浏览。

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

MIT License
