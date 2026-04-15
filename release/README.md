# FileAI — AI 智能文件整理工具

<p align="center">
  <strong>让 AI 帮你整理电脑里的文件</strong><br>
  macOS 原生应用 · DeepSeek / OpenAI / Gemini 多模型支持 · iOS 暗色风格 UI
</p>

---

## 功能特性

- **智能扫描** — 一键扫描 Downloads / Desktop / Documents 中的所有文件
- **两级分类** — 规则引擎（免费快速）+ AI 深度分类（智能精准），节省 API 开销
- **30+ 分类目录** — 按类型、项目、用途细粒度归档，支持日期子目录
- **预览确认** — AI 分类后先预览，展示置信度和分类理由，确认后再执行
- **一键撤销** — 所有操作记录到数据库，任意操作可单条撤销
- **实时监控** — 后台监听目录变化，新文件自动提醒
- **环形图仪表盘** — 一目了然的分类分布和操作历史

## 系统要求

- macOS 10.15 (Catalina) 或更高版本
- Apple Silicon (M1 / M2 / M3 / M4) Mac
- AI API Key（DeepSeek / OpenAI / Gemini 任选一个）

---

## 安装方式

### 方式一：DMG 安装包（推荐）

1. 下载 `FileAI_1.0.0_aarch64.dmg`
2. 双击打开 DMG
3. 将 `FileAI.app` 拖到 `Applications` 文件夹
4. **重要：首次打开前，必须在终端执行以下命令去除隔离标记：**

```bash
xattr -cr /Applications/FileAI.app
```

> ⚠️ 如果不执行此命令，macOS 会提示"文件已损坏"或"无法验证开发者"——这不是文件真的损坏了，而是 macOS 的安全机制在拦截未签名的应用。

5. 然后双击 FileAI.app 即可正常启动

### 方式二：从源码运行（开发者）

```bash
# 1. 启动后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入你的 API Key
cd ..
python run_server.py

# 2. 启动前端（新终端窗口）
cd frontend
npm install
npm run dev
```

然后访问 http://localhost:5173

---

## 配置 AI API Key

FileAI 需要一个 AI 模型的 API Key 来对文件进行智能分类。

### 第一步：获取 API Key

| 模型 | 获取地址 | 费用 |
|---|---|---|
| **DeepSeek**（推荐） | https://platform.deepseek.com | 极低，约 ¥0.01/千次 |
| OpenAI | https://platform.openai.com | 较高 |
| Gemini | https://aistudio.google.com | 有免费额度 |

### 第二步：配置 Key

编辑 `backend/.env` 文件（DMG 用户请编辑 App 目录内的 `.env`）：

```bash
# 使用 DeepSeek（推荐，最便宜）
DEEPSEEK_API_KEY=sk-你的密钥

# 或使用 OpenAI
# OPENAI_API_KEY=sk-proj-你的密钥

# 或使用 Gemini
# GEMINI_API_KEY=你的密钥
```

### 第三步：选择 AI 模型

编辑 `backend/config.yaml` 中的 `ai` 部分：

```yaml
ai:
  provider: deepseek          # 可选: deepseek / openai / gemini / siliconflow
  model: deepseek-chat        # 对应 provider 的模型名
  base_url: https://api.deepseek.com
```

---

## 使用指南

### 基本流程

```
扫描文件 → AI 分类 → 预览结果 → 确认执行 → 完成
```

1. 打开 FileAI，进入**仪表盘**页面
2. 点击 Hero Card 上的「**扫描并整理**」按钮
3. 系统会扫描 Downloads、Desktop、Documents 中的文件
4. 勾选需要整理的文件（默认全选），点击「**AI 分类**」
5. 等待 AI 分析完成，查看分类预览：
   - 每个文件显示目标目录、置信度（高/中/低）、分类理由
   - 绿色 = 高置信度，黄色 = 中等，红色 = 低置信度
6. 确认无误后点击「**确认执行**」
7. 文件被移动到 `~/Organized/` 对应子目录

### 页面说明

| 页面 | 功能 |
|---|---|
| 仪表盘 | 总览统计、环形图分布、最近操作、快捷入口 |
| 整理文件 | 扫描 → 分类 → 执行的主操作页面 |
| 已整理文件 | 浏览 ~/Organized 目录结构，一键在 Finder 中打开 |
| 操作历史 | 查看所有操作记录，支持逐条撤销 |
| 设置 | 查看监控目录、AI 模型配置、实时监控开关 |

### 撤销操作

如果对某个文件的整理结果不满意：
1. 进入「**操作历史**」页面
2. 找到对应记录，点击右侧的撤销按钮
3. 文件会被移回原始位置

### 实时监控

开启监控后，FileAI 会在后台监听 Downloads / Desktop / Documents 的变化：
- 新文件出现时，仪表盘底部的「实时动态」面板会自动展开提示
- 可以在仪表盘或设置页开启/关闭监控

---

## 分类目录结构

文件整理后统一存放在 `~/Organized/` 目录下：

```
~/Organized/
├── Documents/
│   ├── Work/           ← 报告、演示文稿、合同等
│   ├── Personal/       ← 财务、医疗、简历等
│   └── Study/          ← 笔记、论文、电子书
├── Images/
│   ├── Screenshots/    ← 按月份归档
│   ├── Photos/         ← 按月份归档
│   ├── Design/         ← UI 设计稿、图标、插画
│   └── Wallpapers/
├── Videos/
│   ├── Recordings/     ← 屏幕录制
│   ├── Tutorials/      ← 教程视频
│   └── Entertainment/
├── Code/
│   ├── Projects/       ← 按项目名归档
│   ├── Scripts/
│   ├── Configs/
│   └── Data/           ← CSV、JSON、SQL 文件
├── Audio/              ← 音乐、播客、录音
├── Archives/           ← 压缩包、磁盘镜像
├── Design/             ← Figma、Sketch、PSD、字体
├── Installers/         ← 安装包
└── Misc/
    └── Needs_Review/   ← AI 不确定的文件放这里
```

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 桌面壳 | Tauri 2 (Rust) |
| 前端 | React 19 + TypeScript + Vite 8 + TailwindCSS 4 |
| 后端 | Python + FastAPI + uvicorn |
| AI | DeepSeek / OpenAI / Gemini（统一 OpenAI SDK 接口） |
| 文件监控 | watchdog |
| 数据库 | SQLite (aiosqlite) |
| 通信 | REST API + WebSocket 实时推送 |
| 打包 | PyInstaller (Python 后端) + Tauri Bundle (macOS .app/.dmg) |

---

## 常见问题

### Q: 打开 App 提示"文件已损坏"或"无法验证开发者"

这是 macOS Gatekeeper 安全机制的限制，通过微信、AirDrop、网盘等传输的未签名应用都会遇到。在终端执行以下命令即可：

```bash
xattr -cr /Applications/FileAI.app
```

如果 App 在 Downloads 文件夹里还没拖到 Applications：
```bash
xattr -cr ~/Downloads/FileAI.app
```

执行完后再双击打开就正常了。

### Q: AI 分类失败

1. 检查 `backend/.env` 中的 API Key 是否正确
2. 检查网络是否能访问对应 AI 服务（DeepSeek 需要访问 api.deepseek.com）
3. 查看 App 日志确认具体错误

### Q: 文件整理后找不到了

整理后的文件统一存放在 `~/Organized/` 目录下。你可以：
- 在 App 内点击「**已整理文件**」页面浏览
- 在仪表盘点击「**在 Finder 中打开**」直接跳转
- 在 Finder 中手动导航到 `~/Organized/`

### Q: 如何更换 AI 模型

编辑 `backend/config.yaml`，修改 `ai.provider` 字段：
```yaml
ai:
  provider: openai     # deepseek / openai / gemini / siliconflow
  model: gpt-4o-mini   # 对应的模型名
```
然后重启 App。

### Q: 可以发给朋友用吗

可以。将 `FileAI_1.0.0_aarch64.dmg` 发给朋友，对方 Mac 需要满足：
- Apple Silicon 芯片（M1 及以上）
- macOS 10.15 或更高
- 自行配置 AI API Key

---

## 项目结构

```
file_management/
├── backend/                 # Python 后端
│   ├── main.py             # FastAPI 入口
│   ├── config.yaml         # 分类规则配置
│   ├── services/           # 核心服务
│   │   ├── scanner.py      # 文件扫描
│   │   ├── classifier.py   # AI 分类
│   │   ├── rule_engine.py  # 规则引擎
│   │   ├── organizer.py    # 文件移动
│   │   ├── history.py      # 操作历史
│   │   └── watcher.py      # 实时监控
│   └── .env                # API Key 配置
├── frontend/               # React 前端
│   ├── src/
│   │   ├── App.tsx         # 主应用组件
│   │   ├── api.ts          # API 接口
│   │   ├── App.css         # 组件样式
│   │   └── index.css       # 全局样式
│   └── src-tauri/          # Tauri 桌面壳
│       ├── tauri.conf.json # Tauri 配置
│       └── src/main.rs     # Rust 入口
├── release/                # 打包产物
│   ├── FileAI.app
│   └── FileAI_1.0.0_aarch64.dmg
└── run_server.py           # 后端启动脚本
```

---

## License

MIT
