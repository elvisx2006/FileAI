# FileAI — AI 智能文件整理工具

macOS 原生应用 · DeepSeek / OpenAI / Gemini 多模型支持 · iOS 暗色风格 UI

---

## 功能特性

- **智能扫描** — 一键扫描 Downloads / Desktop / Documents 中的所有文件
- **两级分类** — 规则引擎（免费快速）+ AI 深度分类（智能精准）
- **30+ 分类目录** — 按类型、项目、用途细粒度归档
- **预览确认** — 展示置信度和分类理由，确认后再执行
- **一键撤销** — 所有操作可逐条撤销
- **实时监控** — 后台监听目录变化，新文件自动提醒

## 系统要求

- macOS 10.15+ (Catalina 及以上)
- Apple Silicon (M1 / M2 / M3 / M4)
- AI API Key（DeepSeek / OpenAI / Gemini 任选其一）

---

## 安装

### DMG 安装包（推荐）

1. 下载 `FileAI_1.0.0_aarch64.dmg`，双击打开
2. 将 `FileAI.app` 拖到 `Applications` 文件夹
3. **首次打开前，在终端执行：**

```bash
xattr -cr /Applications/FileAI.app
```

4. 双击 FileAI.app 启动

> 如果 App 还在 Downloads 里，命令改为 `xattr -cr ~/Downloads/FileAI.app`

### 从源码运行

```bash
# 启动后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 API Key
cd ..
python run_server.py

# 新终端窗口，启动前端
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

---

## 配置 AI

### 1. 获取 API Key

| 模型 | 地址 | 费用 |
|---|---|---|
| **DeepSeek**（推荐） | https://platform.deepseek.com | 极低，约 ¥0.01/千次 |
| OpenAI | https://platform.openai.com | 较高 |
| Gemini | https://aistudio.google.com | 有免费额度 |

### 2. 写入 Key

编辑 `backend/.env`：

```bash
DEEPSEEK_API_KEY=sk-你的密钥

# 或 OpenAI / Gemini（取消注释对应行）
# OPENAI_API_KEY=sk-proj-你的密钥
# GEMINI_API_KEY=你的密钥
```

### 3. 选择模型

编辑 `backend/config.yaml` 的 `ai` 部分：

```yaml
ai:
  provider: deepseek          # deepseek / openai / gemini / siliconflow
  model: deepseek-chat
  base_url: https://api.deepseek.com
```

修改后需重启应用。

---

## 使用流程

```
扫描文件 → AI 分类 → 预览结果 → 确认执行 → 完成
```

1. 打开 FileAI，点击仪表盘上的「**扫描并整理**」
2. 勾选文件后点击「**AI 分类**」
3. 查看分类预览（绿色=高置信度，黄色=中等，红色=低）
4. 确认后点击「**确认执行**」，文件被移动到 `~/Organized/` 对应子目录

### 页面说明

| 页面 | 功能 |
|---|---|
| 仪表盘 | 统计总览、环形图分布、最近操作 |
| 整理文件 | 扫描 → 分类 → 执行 |
| 已整理文件 | 浏览 ~/Organized 目录，一键在 Finder 中打开 |
| 操作历史 | 所有记录，支持逐条撤销 |
| 设置 | 监控目录、AI 模型、实时监控开关 |

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
│   ├── Photos/         ← 按月份归档
│   └── Design/         ← UI 设计稿、图标
├── Videos/
│   ├── Recordings/     ← 屏幕录制
│   ├── Tutorials/
│   └── Entertainment/
├── Code/
│   ├── Projects/       ← 按项目名归档
│   ├── Scripts/
│   └── Data/           ← CSV、JSON、SQL
├── Audio/              ← 音乐、播客、录音
├── Archives/           ← 压缩包
├── Design/             ← Figma、Sketch、PSD、字体
├── Installers/         ← 安装包
└── Misc/
    └── Needs_Review/   ← AI 不确定的文件
```

---

## 常见问题

### 打开提示"文件已损坏"或"无法验证开发者"

macOS 对未签名应用的安全拦截，不是文件真的损坏。终端执行：

```bash
xattr -cr /Applications/FileAI.app
```

### 运行时提示"无法验证 xxx.so 是否包含恶意软件"

从源码运行时，`pip install` 安装的部分 Python 包含有编译后的 `.so` 动态库（如 `jiter.cpython-39-darwin.so`），macOS 同样会拦截。解决方法：

**方法一（推荐）：一次性放行整个虚拟环境**

```bash
xattr -cr backend/venv
```

**方法二：通过系统设置放行**

1. 打开 **系统设置 → 隐私与安全性**
2. 页面底部会显示被阻止的文件，点击「**仍然允许**」
3. 重新运行程序，再次弹窗时点击「**打开**」

> 每次 `pip install` 新包后如果再次出现，重新执行方法一即可。

### AI 分类失败

1. 检查 `backend/.env` 中的 API Key 是否正确
2. 检查网络能否访问对应 AI 服务
3. 查看终端日志确认具体错误

### 文件整理后找不到

整理后的文件在 `~/Organized/` 目录下，可以：
- App 内「**已整理文件**」页面浏览
- 仪表盘点击「**在 Finder 中打开**」
- Finder 手动前往 `~/Organized/`

---

## 技术栈

| 层级 | 技术 |
|---|---|
| 桌面壳 | Tauri 2 (Rust) |
| 前端 | React 19 + TypeScript + Vite + TailwindCSS |
| 后端 | Python + FastAPI + uvicorn |
| AI | DeepSeek / OpenAI / Gemini（统一 OpenAI SDK 接口） |
| 数据库 | SQLite (aiosqlite) |
| 通信 | REST API + WebSocket |
| 打包 | PyInstaller + Tauri Bundle |

## 项目结构

```
file_management/
├── backend/
│   ├── main.py             # FastAPI 入口
│   ├── config.yaml         # 分类规则配置
│   ├── services/           # 核心服务（扫描/分类/整理/历史/监控）
│   └── .env                # API Key
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # 主应用组件
│   │   ├── api.ts          # API 接口
│   │   └── *.css           # 样式
│   └── src-tauri/          # Tauri 桌面壳
├── release/                # 打包产物（.app / .dmg）
└── run_server.py           # 后端启动脚本
```

---

MIT
