# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-対応-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/ライセンス-MIT-yellow.svg?style=for-the-badge" alt="ライセンス" />
</p>

<p align="center"><strong>PCをポケットに — リモートコントロール、AI自動化、開発ツールをすべてTelegramで。</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">コマンド</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">開発</a> •
  <a href="CONTRIBUTING.md">コントリビュート</a> •
  <a href="SECURITY.md">セキュリティ</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md"><strong>日本語</strong></a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** は、Windows PCをどこからでも完全にリモート操作できる、セルフホスト型のTelegramボットです。完全にあなたのマシン上で動作し、クラウドリレーや定期購読は不要です。Telegramのメッセージリレーとオプションのgemini API以外、ネットワークからデータが流出することはありません。

AIの設定なしで、すぐに使える機能：
- **ファイルの閲覧・読み取り**（承認済みディレクトリ内）
- **デスクトップの制御** — スクリーンショット、キーボードショートカット、クリップボード、ウィンドウ切り替え、スリープ、シャットダウン
- **UI自動化** — OCRクリック（Tesseract）と要素検出（OpenCV）
- **Claude DesktopとVS Codeをリモート操作**（キーボードに触れずに）
- **マクロ記録**で複数ステップのワークフローを1コマンドで再生
- **タスクスケジューリング** — 再起動後も保持
- **AndroidのAPKをビルド・配信** — TelegramでReact Nativeプロジェクトから

**Google Gemini 2.0 Flash**の認証情報を追加すると解放される機能：
- **会話型AIチャット** — マルチターン記憶と画像分析
- **エージェント型コンピュータ制御** — Geminiがファイル閲覧、スクリーンショット、クリック、入力、自然言語によるPC操作を行い、破壊的な操作は人間が確認
- **プロンプト改善** `/enhance`コマンド

---

## 主な機能

以下はすべてAI設定なしで動作します：

- **ファイルシステムエクスプローラー**：承認済みパスに限定して、スマホからPCのファイルを閲覧・読み取り・検索。
- **デスクトップ制御**：スクリーンショット、キーボードショートカット、クリップボード、ウィンドウ管理、バッテリー状態、スリープ/シャットダウン。
- **ビジョン・UI自動化**：TesseractによるOCRクリック、OpenCVによる要素検出。
- **マクロ記録**：複数ステップのシーケンスを記録して1コマンドで再生。
- **Claude Desktop連携**：リモートからプロンプト送信、モデル切り替え、ワークスペース管理。
- **VS Code / Antigravity連携**：フォルダを開く、AIモデル切り替え、Antigravity拡張機能の操作。
- **タスクスケジューラー**：指定した時間に自動化フローやClaudeプロンプトを実行。再起動後も保持。
- **ビルド自動化**：React Native AndroidビルドをトリガーしてTelegramでAPKを受け取る。
- **自動更新**：ボットが更新を確認・適用可能。
- **軽量**：アイドル時約55-70 MB RAM、CPU <0.5%。重い依存関係はコマンド使用時のみ読み込み。

**オプション（Google Gemini認証情報が必要）：**

- **AIチャット・コンピュータ制御**：Gemini 2.0 Flashでマルチターン会話、画像分析、ツール呼び出し。破壊的なアクションはすべてTelegramのインラインボタンで明示的な承認が必要。
- **プロンプト改善**：`/enhance`でGeminiがプロンプトを書き直し・改善。

---

## 仕組み

Pocket Desk AgentはWindows PCのローカルプロセスとして動作し、Long-Pollingで**アウトバウンド**でTelegramサーバーに接続します。ポートフォワーディングやルーター設定、動的DNSは不要です。

```
あなたの電話 → Telegramサーバー → (アウトバウンドポーリング) → Pocket Desk Agent（ローカル） → PCアクション → 返信
```

**主要内部コンポーネント：**

| コンポーネント | 役割 |
| :--- | :--- |
| `python-telegram-bot` | 非同期Telegramクライアント |
| `GeminiClient` | Gemini APIセッションと会話履歴の管理 |
| `FileManager` | サンドボックス化されたファイルI/O — パス検証 |
| `AuthManager` | Antigravity、Gemini CLI、APIキー用マルチプロバイダーOAuth |
| `SchedulerRegistry` | ディスクへのタスク永続化、60秒ごとに確認 |
| `RateLimiter` | コマンドごとのユーザー別トークンバケット |

---

## プラットフォーム互換性

| 機能 | Windows | macOS / Linux |
| :--- | :---: | :---: |
| ファイルシステム | ✅ | ✅ |
| AIチャット（Gemini） | ✅ | ✅ |
| タスクスケジューリング | ✅ | ✅ |
| スクリーンショット | ✅ | ✅ |
| キーボードショートカット | ✅ | ⚠️ 部分的 |
| クリップボード | ✅ | ⚠️ 部分的 |
| UI自動化（OCR） | ✅ | ❌ |
| ウィンドウ管理 | ✅ | ❌ |
| Claude Desktop連携 | ✅ | ❌ |
| VS Code連携 | ✅ | ❌ |
| APKビルド | ✅ | ❌ |
| ログイン後の自動起動 | ✅ | ❌ |

---

## 始める前に

### 1. Telegramボットの作成

1. Telegramを開き、**[@BotFather](https://t.me/BotFather)**にメッセージを送る
2. `/newbot`を送信してプロンプトに従う
3. **ボットトークン**をコピー — これが`TELEGRAM_BOT_TOKEN`

### 2. TelegramユーザーIDの取得

1. Telegramで**[@userinfobot](https://t.me/userinfobot)**にメッセージを送る
2. 数字のユーザーIDが返ってきます — これが`AUTHORIZED_USER_IDS`

### 3. （オプション）Google / Gemini認証情報

AIチャット、画像分析、または`/enhance`コマンドにのみ必要です。

**オプションA — OAuth（推奨）：** ビルトインOAuthサポート、GCPプロジェクト不要。設定時に**Antigravity OAuth**または**Gemini CLI OAuth**を選択。

**オプションB — APIキー：**
1. [Google AI Studio](https://aistudio.google.com/app/apikey)にアクセス
2. APIキーを作成 — これが`GOOGLE_API_KEY`

---

## クイックスタートとインストール

### システム要件

- **Python 3.11+**
- **Windows 10以降** — UI自動化機能に必要
- **Tesseract OCR** — `/findtext`、`/smartclick`用。`pdagent setup`でインストール
- **Visual C++ 再頒布可能パッケージ** — 通常すでにインストール済み

### オプションA：PyPIからインストール（推奨）

```bash
pip install pocket-desk-agent
pdagent
```

初回起動時に`pdagent`がインタラクティブな設定ウィザードを起動します。

```bash
pdagent start        # バックグラウンドデーモンとして実行
pdagent configure    # 設定ウィザードを再実行
pdagent setup        # システム依存関係の確認とインストール
```

### オプションB：ローカル開発者モード

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## ボットの起動

| コマンド | 説明 |
| :--- | :--- |
| `pdagent` | フォアグラウンドで実行 |
| `pdagent start` | バックグラウンドデーモンとして起動 |
| `pdagent stop` | デーモンを停止 |
| `pdagent restart` | デーモンを再起動 |
| `pdagent status` | デーモンの状態を確認 |
| `pdagent configure` | 設定ウィザード |
| `pdagent auth` | Gemini認証情報の管理 |
| `pdagent version` | インストール済みバージョン |

---

## セキュリティ

詳細なセキュリティ情報は **[SECURITY.md](SECURITY.md)** を参照してください。

---

## トラブルシューティング

**ボットが起動してもメッセージに返答しない**
- `AUTHORIZED_USER_IDS`にあなたのTelegram IDが含まれているか確認
- 作業ディレクトリの`bot.log`でエラーを確認
- `/status`でGemini接続を検証

**`/findtext`や`/smartclick`がエラーを返す**
- Tesseract OCRがインストールされていないかPATHにない
- `pdagent setup`を実行するか、手動で：`winget install UB-Mannheim.TesseractOCR`

**Gemini認証が失敗する**
- `pdagent auth`を実行して「ログイン」を選択するか、Telegramで`/login`を使用
- OAuth：ポート`51121`がファイアウォールでブロックされていないか確認

---

## コントリビュート

開発設定、コーディング標準、新しいコマンドの追加方法については [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

---

## ライセンス

MITライセンスの下で配布されています。詳細は [LICENSE](LICENSE) を参照してください。
