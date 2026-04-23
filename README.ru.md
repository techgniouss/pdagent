# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Поддерживается-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Лицензия-MIT-yellow.svg?style=for-the-badge" alt="Лицензия" />
</p>

<p align="center"><strong>Ваш ПК в кармане — удалённое управление, ИИ-автоматизация и инструменты разработчика — всё через Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Команды</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Разработка</a> •
  <a href="CONTRIBUTING.md">Участие</a> •
  <a href="SECURITY.md">Безопасность</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md"><strong>Русский</strong></a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** — это самостоятельно размещаемый Telegram-бот, дающий вам полный удалённый контроль над Windows-ПК с любого устройства. Он работает полностью на вашей машине — без облачного ретранслятора, без подписки, никакие данные не покидают вашу сеть, кроме ретрансляции сообщений Telegram и опционального Gemini API.

Из коробки, без каких-либо настроек ИИ:
- **Просмотр и чтение файлов** в пределах разрешённых директорий
- **Управление рабочим столом** — скриншоты, горячие клавиши, буфер обмена, переключение окон, сон, выключение
- **Автоматизация UI** с OCR-кликами (Tesseract) и обнаружением элементов (OpenCV)
- **Удалённое управление Claude Desktop и VS Code** без прикосновения к клавиатуре
- **Запись макросов** и воспроизведение многошаговых рабочих процессов одной командой
- **Планирование задач** на нужное время — сохраняются после перезапуска
- **Сборка и доставка Android APK** из React Native проектов через Telegram

Добавьте **Google Gemini 2.0 Flash** для разблокировки:
- **Диалоговый ИИ-чат** с многоходовой памятью и анализом изображений
- **Агентное управление компьютером** — Gemini может просматривать файлы, делать скриншоты, кликать, печатать и автоматизировать действия на вашем ПК по запросу на естественном языке, с подтверждением всех деструктивных действий
- **Улучшение промптов** через `/enhance`

---

## Основные возможности

Всё перечисленное работает без настройки ИИ:

- **Проводник файловой системы**: просмотр, чтение и поиск файлов на ПК с телефона в пределах разрешённых путей.
- **Управление рабочим столом**: скриншоты, горячие клавиши, буфер обмена, переключение окон, заряд батареи, сон/выключение.
- **Зрение и автоматизация UI**: OCR-клики через Tesseract — найти и кликнуть любой видимый текст. Компьютерное зрение (OpenCV) для обнаружения иконок и элементов UI.
- **Запись макросов**: запись многошаговых последовательностей и воспроизведение одной командой.
- **Интеграция с Claude Desktop**: удалённое управление приложением Claude Desktop — отправка промптов, смена моделей, управление рабочими пространствами.
- **Интеграция с VS Code / Antigravity**: открытие папок, смена моделей ИИ, управление расширением Antigravity.
- **Планировщик задач**: запуск автоматизаций или промптов Claude в заданное время. Задачи сохраняются после перезапуска.
- **Автоматизация сборки**: запуск React Native Android сборок и получение APK через Telegram.
- **Автообновление**: бот может проверять и применять обновления по требованию.
- **Лёгкий**: ~55-70 МБ ОЗУ в простое, <0.5% CPU. Тяжёлые зависимости загружаются только при использовании соответствующих команд.

**Опционально — требуются учётные данные Google Gemini:**

- **ИИ-чат и управление компьютером**: Gemini 2.0 Flash с многоходовыми разговорами, анализом изображений и вызовом инструментов. Все деструктивные действия требуют явного подтверждения через кнопки Telegram.
- **Улучшение промптов**: `/enhance` — Gemini перепишет и улучшит ваш промпт.

---

## Как это работает

Pocket Desk Agent запускается как локальный процесс на вашем Windows-ПК и подключается **исходящим** соединением к серверам Telegram через long-polling — не требуется проброс портов, настройка роутера или динамический DNS.

```
Ваш телефон → Серверы Telegram → (исходящий polling) → Pocket Desk Agent (локально) → Действие на ПК → Ответ
```

**Ключевые внутренние компоненты:**

| Компонент | Роль |
| :--- | :--- |
| `python-telegram-bot` | Асинхронный Telegram-клиент |
| `GeminiClient` | Управление сессиями Gemini API и историей диалогов |
| `FileManager` | Файловые операции в песочнице — проверка путей |
| `AuthManager` | OAuth для Antigravity, Gemini CLI и API-ключа |
| `SchedulerRegistry` | Хранение задач на диске, проверка каждые 60 с |
| `RateLimiter` | Ограничитель скорости с токен-бакетом на каждую команду |

---

## Совместимость платформ

| Функция | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Файловая система | ✅ | ✅ |
| ИИ-чат (Gemini) | ✅ | ✅ |
| Планирование задач | ✅ | ✅ |
| Скриншоты | ✅ | ✅ |
| Горячие клавиши | ✅ | ⚠️ частично |
| Буфер обмена | ✅ | ⚠️ частично |
| Автоматизация UI (OCR) | ✅ | ❌ |
| Управление окнами | ✅ | ❌ |
| Интеграция Claude Desktop | ✅ | ❌ |
| Интеграция VS Code | ✅ | ❌ |
| Сборка APK | ✅ | ❌ |
| Автозапуск после входа | ✅ | ❌ |

---

## Перед началом

### 1. Создайте Telegram-бота

1. Откройте Telegram и напишите **[@BotFather](https://t.me/BotFather)**
2. Отправьте `/newbot` и следуйте инструкциям
3. Скопируйте **токен бота** — это ваш `TELEGRAM_BOT_TOKEN`

### 2. Получите ваш Telegram ID

1. Напишите **[@userinfobot](https://t.me/userinfobot)** в Telegram
2. Он ответит вашим числовым ID — это ваш `AUTHORIZED_USER_IDS`

### 3. (Опционально) Учётные данные Google / Gemini

Нужны только для ИИ-чата, анализа изображений или команды `/enhance`.

**Вариант A — OAuth (рекомендуется):** Встроенная поддержка OAuth, не нужен отдельный проект GCP. Выберите **Antigravity OAuth** или **Gemini CLI OAuth** при настройке.

**Вариант B — API-ключ:**
1. Перейдите на [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Создайте API-ключ — это ваш `GOOGLE_API_KEY`

---

## Быстрый старт и установка

### Системные требования

- **Python 3.11+**
- **Windows 10 или новее** — для функций автоматизации UI
- **Tesseract OCR** — для `/findtext`, `/smartclick`. Запустите `pdagent setup` для установки
- **Visual C++ Redistributables** — обычно уже установлены

### Вариант A: Установка из PyPI (рекомендуется)

```bash
pip install pocket-desk-agent
pdagent
```

При первом запуске `pdagent` запустит интерактивный мастер настройки.

```bash
pdagent start        # запуск как фоновый демон
pdagent configure    # повторный запуск мастера настройки
pdagent setup        # проверка и установка системных зависимостей
```

### Вариант B: Режим разработчика

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Запуск бота

| Команда | Описание |
| :--- | :--- |
| `pdagent` | Запуск в режиме переднего плана |
| `pdagent start` | Запуск как фоновый демон |
| `pdagent stop` | Остановка демона |
| `pdagent restart` | Перезапуск демона |
| `pdagent status` | Проверка состояния |
| `pdagent configure` | Мастер настройки |
| `pdagent setup` | Check and install system dependencies (for example Tesseract OCR) |
| `pdagent startup <enable\|disable\|status\|configure>` | Manage automatic startup after Windows login |
| `pdagent auth` | Управление учётными данными Gemini |
| `pdagent version` | Версия |

---

## Безопасность

Подробную информацию о безопасности смотрите в **[SECURITY.md](SECURITY.md)**.

---

## Устранение неполадок

**Бот запущен, но не отвечает на сообщения**
- Убедитесь, что ваш Telegram ID указан в `AUTHORIZED_USER_IDS`
- Проверьте `bot.log` на наличие ошибок
- Выполните `/status` для проверки подключения

**`/findtext` или `/smartclick` возвращают ошибку**
- Tesseract OCR не установлен или не в PATH
- Запустите `pdagent setup` или выполните: `winget install UB-Mannheim.TesseractOCR`

**Сбой аутентификации Gemini**
- Запустите `pdagent auth` и выберите "Войти", или используйте `/login` в Telegram
- Убедитесь, что порт `51121` не заблокирован файерволом

---

**Операция с файлом завершается с ошибкой "Access denied" или "Path not allowed"**
- Запрошенный путь находится за пределами `APPROVED_DIRECTORIES`.
- Запустите `pdagent configure` и выберите **2) Approved Directories**, чтобы добавить один путь с помощью опции **A**, не заменяя существующий список.
- Или отредактируйте конфигурацию напрямую: `APPROVED_DIRECTORIES="C:\Users\YourName\Documents,C:\projects"` (абсолютные пути через запятую).
- Примечание: `CLAUDE_DEFAULT_REPO_PATH` **всегда** добавляется в песочницу во время выполнения, даже если он не указан в `APPROVED_DIRECTORIES`.

**Запланированные задачи не срабатывают**
- Бот должен быть запущен в момент наступления запланированного времени — задачи не срабатывают, если бот остановлен.
- Запустите `/listschedules`, чтобы подтвердить, что задача все еще ожидает выполнения и формат времени правильный (`HH:MM` в 24-часовом формате).
- Проверьте вывод `LOG_LEVEL=DEBUG` на наличие ошибок планировщика.

## Вклад в проект

Смотрите [CONTRIBUTING.md](CONTRIBUTING.md) для получения информации об настройке разработки.

---

## Лицензия

Распространяется под лицензией MIT. Подробности в [LICENSE](LICENSE).
