# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-支持-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/许可证-MIT-yellow.svg?style=for-the-badge" alt="许可证" />
</p>

<p align="center"><strong>将电脑装进口袋 — 远程控制、AI 自动化和开发者工具，全部通过 Telegram 实现。</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">命令参考</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">开发文档</a> •
  <a href="CONTRIBUTING.md">贡献指南</a> •
  <a href="SECURITY.md">安全策略</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md"><strong>中文</strong></a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** 是一个自托管的 Telegram 机器人，让你可以从任何设备完全远程控制 Windows 电脑。它完全运行在你的本地机器上——无需云中继、无需订阅，除 Telegram 消息中转和可选的 Gemini API 外，没有任何数据离开你的网络。

开箱即用，无需 AI 配置：
- **浏览和读取文件**，限定在你批准的目录范围内
- **控制桌面** — 截图、键盘快捷键、剪贴板、窗口切换、睡眠、关机
- **UI 自动化**，使用基于 OCR 的文字点击（Tesseract）和元素检测（OpenCV）
- **远程驱动 Claude Desktop 和 VS Code**，无需触碰键盘
- **录制宏命令**，用一条指令重放多步骤工作流
- **定时任务**，在你睡觉时自动执行——重启后任务依然保留
- **构建并传输 Android APK**，通过 Telegram 处理 React Native 项目

添加 **Google Gemini 2.0 Flash** 凭据以解锁：
- **对话式 AI 聊天**，支持多轮记忆和图片分析
- **AI 代理控制**——Gemini 可以浏览文件、截图、点击、输入，并通过自然语言自动化操作你的电脑，对任何破坏性操作都需要人工确认
- **提示词增强**，通过 `/enhance` 命令

---

## 主要功能

以下功能无需任何 AI 配置即可使用：

- **文件系统浏览器**：从手机浏览、读取和搜索本地 PC 目录，限定在批准的路径范围内。
- **桌面控制**：截图、发送键盘快捷键、管理剪贴板、切换窗口、检查电量，以及触发睡眠/关机。
- **视觉与 UI 自动化**：基于 Tesseract 的 OCR 点击——查找并点击屏幕上任何可见文字。使用 OpenCV 进行图标和 UI 元素检测。
- **宏录制**：录制多步骤 UI 序列并用一条命令重放。
- **Claude Desktop 集成**：远程控制 Claude Desktop 应用——发送提示词、切换模型、管理工作区，无需触碰电脑。
- **VS Code / Antigravity 集成**：远程打开文件夹、切换 AI 模型，并驱动 Antigravity VS Code 扩展。
- **任务调度器**：在指定时间运行自动化流程或 Claude 提示词，即使在你睡觉时也能执行。任务在重启后依然保留。
- **构建自动化**：通过 Telegram 触发 React Native Android 构建并获取 APK。
- **自动更新**：机器人可按需检查并应用更新。
- **轻量级**：空闲内存约 55-70 MB，空闲 CPU 占用 <0.5%。重型依赖（OpenCV、NumPy、Dropbox）仅在使用对应命令时才会加载。

**可选功能——需要 Google Gemini 凭据：**

- **AI 聊天与计算机控制**：Google Gemini 2.0 Flash，支持多轮对话、图片分析和完整的代理工具调用。直接发送任何文字或照片即可聊天。Gemini 作为自主代理，可以原生浏览文件、分析截图，并根据自然语言请求使用 UI 自动化（点击、输入、导航）在你的 PC 上执行任务。所有破坏性或系统级操作都需要通过 Telegram 内联按钮进行明确的人工确认。
- **提示词增强**：使用 `/enhance` 让 Gemini 在将提示词发送到任何地方之前对其进行重写和改进。

---

## 工作原理

Pocket Desk Agent 作为本地进程在你的 Windows PC 上运行，并通过长轮询**向外**连接到 Telegram 服务器——无需入站端口转发、路由器配置或动态 DNS。

```
你的手机 → Telegram 服务器 → （出站轮询）→ Pocket Desk Agent（本地）→ PC 操作 → 回复
```

当你从手机发送消息时，Telegram 会持有该消息，直到机器人的轮询循环将其取走（通常不到 1 秒）。命令在本地 PC 上执行，结果通过相同的 Telegram 中继发回。

**核心内部组件：**

| 组件 | 作用 |
| :--- | :--- |
| `python-telegram-bot` | 异步 Telegram 客户端——接收并分发所有命令 |
| `GeminiClient` | 管理 Gemini API 会话、多轮历史记录和工具调用 |
| `FileManager` | 沙箱化文件 I/O——所有路径均针对 `APPROVED_DIRECTORIES` 进行验证 |
| `AuthManager` | 支持 Antigravity、Gemini CLI 和 API 密钥模式的多提供商 OAuth 封装器 |
| `SchedulerRegistry` | 将计划任务持久化到磁盘，每 60 秒检查一次；重启后任务依然保留 |
| `RateLimiter` | 自动应用于每条命令的每用户令牌桶速率限制器 |

全部 70 个命令处理器都集中注册在 `command_map.py` 中。每个处理器都由 `@safe_command` 包装，在一个地方统一执行授权、速率限制和错误报告——各处理器中无需手动进行身份验证检查。

---

## 平台兼容性

| 功能 | Windows | macOS / Linux |
| :--- | :---: | :---: |
| 文件系统（浏览、读取、搜索） | ✅ | ✅ |
| AI 聊天与图片分析（Gemini） | ✅ | ✅ |
| 任务调度 | ✅ | ✅ |
| 自动更新 | ✅ | ✅ |
| 截图 | ✅ | ✅ |
| 键盘快捷键（`/hotkey`） | ✅ | ⚠️ 部分支持 |
| 剪贴板读写 | ✅ | ⚠️ 部分支持 |
| 电量状态 | ✅ | ✅ |
| UI 自动化（OCR 点击、查找文字） | ✅ | ❌ |
| 元素检测（OpenCV） | ✅ | ❌ |
| 窗口管理（`/windows`、`/focuswindow`） | ✅ | ❌ |
| Claude Desktop 集成 | ✅ | ❌ |
| VS Code / Antigravity 集成 | ✅ | ❌ |
| React Native 构建自动化 | ✅ | ❌ |
| 登录后自动启动 | ✅ | ❌ |

> macOS/Linux 用户可以使用机器人进行文件系统访问、Gemini AI 聊天和任务调度。UI 自动化功能需要 Windows，OCR 命令还需要安装 Tesseract。

---

## 开始之前

你只需要两样东西即可开始使用。Google 凭据是可选的，仅在需要 AI 聊天时才需要。

### 1. 创建 Telegram 机器人

1. 打开 Telegram 并向 **[@BotFather](https://t.me/BotFather)** 发消息
2. 发送 `/newbot` 并按提示为机器人命名
3. 复制**机器人令牌**（格式如 `123456789:ABCdef...`）——这是你的 `TELEGRAM_BOT_TOKEN`

### 2. 获取你的 Telegram 用户 ID

1. 在 Telegram 上向 **[@userinfobot](https://t.me/userinfobot)** 发消息
2. 它会回复你的数字用户 ID——这是你的 `AUTHORIZED_USER_IDS`

> 只有 `AUTHORIZED_USER_IDS` 中列出的 Telegram 账号才能控制机器人。请妥善保管。

### 3. （可选）获取 Google / Gemini 凭据

仅在需要 AI 聊天、图片分析或 `/enhance` 命令时才需要。所有其他功能无需此项。

**选项 A — OAuth（推荐，零配置）：** 机器人内置 OAuth 支持——推荐的浏览器登录流程无需单独的 GCP 项目或 API 密钥。在设置过程中，选择 **Antigravity OAuth** 或 **Gemini CLI OAuth**，或选择**稍后设置**，随时通过 Telegram 中的 `/login` 进行身份验证。

**选项 B — API 密钥：** 无需登录流程，直接粘贴密钥。
1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建 API 密钥——这是你的 `GOOGLE_API_KEY`

> **自定义 OAuth 应用：** 如果你想使用自己的 GCP OAuth 凭据而不是内置的，请在配置中设置 `GOOGLE_OAUTH_CLIENT_ID` 和 `GOOGLE_OAUTH_CLIENT_SECRET`。要注册的重定向 URI 为 `http://localhost:51121/oauth-callback`。

---

## 快速开始与安装

### 系统要求

- **Python 3.11+**
- **Windows 10 或更高版本** — UI 自动化功能（`pywinauto`、`pyautogui`、`pygetwindow`）需要 Windows。文件系统访问、Gemini AI 聊天和任务调度也可在 macOS/Linux 上使用（参见[平台兼容性](#平台兼容性)）。
- **Tesseract OCR** — `/findtext`、`/smartclick` 以及 Claude/Antigravity UI 自动化所需。`pdagent` 在首次运行时会检测其是否缺失，并通过 winget 提供自动安装。随时运行 `pdagent setup` 重新检查。
- **Visual C++ 运行时** — `pywinauto` 和 `pyautogui` 在 Windows 上需要此组件。通常已预装；若启动时出现 `ImportError`，请从 Microsoft 官网安装最新版本。

### 选项 A：从 PyPI 安装（推荐）

```bash
pip install pocket-desk-agent
pdagent
```

首次运行时，`pdagent` 会启动交互式设置向导，引导你完成所有配置值的设置，并提供自动安装 Tesseract OCR 的选项。就这么简单。

```bash
pdagent start        # 作为后台守护进程运行
pdagent configure    # 随时重新运行设置向导
pdagent setup        # 重新检查并安装系统依赖（如 Tesseract）
pdagent startup status
pdagent startup configure
```

### 选项 B：本地开发者模式

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

完整的本地开发指南（虚拟环境设置、实时重载、make 目标、资源占用）请参见 **[docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)**。

---

## 配置

### 使用设置向导（推荐）

```bash
pdagent configure
```

在 **首次运行** 时，`pdagent configure` 会引导你完成所有三个部分（Telegram、Gemini 认证和可选设置）并将所有内容保存到 `~/.pdagent/config`。

在 **后续运行** 中（当配置已存在时），它会显示你当前的值并呈现一个 **选择性更新菜单** —— 你可以更改单个字段（例如：授权用户 ID 或批准的目录），而无需重新输入其他所有内容。


Gemini 身份验证步骤提供四个选项：

| 选项 | 描述 | 最适合 |
| :--- | :--- | :--- |
| `1) Antigravity OAuth` | 立即打开浏览器，使用内置凭据登录。令牌自动刷新。 | 大多数用户——零配置，会话时长最长 |
| `2) Gemini CLI OAuth` | 使用公共 Gemini API 进行浏览器登录。无需 GCP 项目。令牌自动刷新。 | 已使用 Gemini CLI 生态系统的用户 |
| `3) API 密钥` | 粘贴 Google AI Studio 密钥。无需登录流程或浏览器。 | 自动化、无头服务器或偏好 API 密钥 |
| `4) 稍后设置` | 跳过 Gemini 设置。随时通过 Telegram 中的 `/login` 进行身份验证。 | 先不使用 AI 功能试用机器人 |

### 运行机器人

| 命令 | 描述 |
| :--- | :--- |
| `pdagent` | 在前台运行（附加到终端） |
| `pdagent start` | 作为后台守护进程启动 |
| `pdagent stop` | 停止后台守护进程 |
| `pdagent restart` | 重启守护进程 |
| `pdagent status` | 检查守护进程是否正在运行 |
| `pdagent configure` | 运行交互式设置向导 |
| `pdagent setup` | 检查并安装系统依赖 |
| `pdagent auth` | 管理 Gemini 身份验证凭据 |
| `pdagent version` | 打印已安装版本 |

---

## 安全性

Pocket Desk Agent **完全在你的本地机器上运行**——除 Google 的 Gemini API 和 Telegram 的消息中转外，不会向任何第三方服务器发送数据。请谨慎配置，因为它提供对你工作站的系统级访问权限。

详细的安全信息，请参见 **[SECURITY.md](SECURITY.md)**。

---

## 故障排除

**机器人启动后不响应消息**
- 确认你的 Telegram 用户 ID 在 `AUTHORIZED_USER_IDS` 中（从 [@userinfobot](https://t.me/userinfobot) 获取）
- 检查工作目录中的 `bot.log` 是否有错误
- 在机器人聊天中运行 `/status` 验证 Gemini 连接

**`/findtext` 或 `/smartclick` 返回错误**
- Tesseract OCR 未安装或不在 PATH 中
- 运行 `pdagent setup` 自动安装，或手动安装：`winget install UB-Mannheim.TesseractOCR`
- 安装后，在再次运行机器人之前重启终端

**Gemini 身份验证失败**
- 运行 `pdagent auth` 并选择"登录"重新验证，或在 Telegram 中使用 `/login`
- 对于 OAuth：确保端口 `51121` 未被防火墙阻止或被其他进程占用

**机器人启动时崩溃并出现 `ImportError`**
- 运行 `pip install --upgrade pocket-desk-agent` 确保所有依赖项是最新的
- 在 Windows 上，某些包需要 Visual C++ 运行时

---

**文件操作失败并显示 "Access denied" (拒绝访问) 或 "Path not allowed" (路径不被允许)**
- 请求的路径在 `APPROVED_DIRECTORIES` 之外
- 运行 `pdagent configure` 并选择 **2) Approved Directories**，使用 **A** 选项添加单个路径，而无需替换现有列表
- 或者直接编辑配置：`APPROVED_DIRECTORIES="C:\Users\YourName\Documents,C:\projects"` (逗号分隔的绝对路径)
- 注意：`CLAUDE_DEFAULT_REPO_PATH` **始终**在运行时添加到沙箱中，即使它没有列在 `APPROVED_DIRECTORIES` 中

**计划任务不触发**
- 计划时间到达时机器人必须正在运行 —— 如果机器人已停止，任务将不会触发
- 运行 `/listschedules` 确认任务仍在挂起且时间格式正确（24 小时制 `HH:MM`）
- 检查 `LOG_LEVEL=DEBUG` 记录以查看调度器错误

## 贡献

请参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发设置、编码标准以及如何添加新命令。

---

## 许可证

基于 MIT 许可证分发。详情请参见 [LICENSE](LICENSE)。
