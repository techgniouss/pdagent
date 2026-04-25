# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Підтримується-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Ліцензія-MIT-yellow.svg?style=for-the-badge" alt="Ліцензія" />
</p>

<p align="center"><strong>Ваш ПК у кишені — дистанційне керування, ШІ-автоматизація та інструменти розробника — все через Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Команди</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Розробка</a> •
  <a href="CONTRIBUTING.md">Внесок</a> •
  <a href="SECURITY.md">Безпека</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md"><strong>Українська</strong></a>
</p>

**Pocket Desk Agent** — це Telegram-бот із самостійним хостингом, який дає вам повне дистанційне керування Windows-ПК з будь-якого пристрою. Він працює повністю на вашій машині — без хмарного ретранслятора, без підписки, жодні дані не залишають вашу мережу, крім ретрансляції повідомлень Telegram та опціонального Gemini API.

З коробки, без налаштування ШІ:
- **Перегляд та читання файлів** у ваших схвалених директоріях
- **Керування робочим столом** — знімки екрана, гарячі клавіші, буфер обміну, перемикання вікон, сон, вимкнення
- **Автоматизація інтерфейсу** з OCR-кліками (Tesseract) та виявленням елементів (OpenCV)
- **Дистанційне керування Claude Desktop і VS Code** без дотику до клавіатури
- **Запис макросів** та відтворення багатокрокових робочих процесів однією командою
- **Планування завдань** — зберігаються після перезапуску
- **Збірка та доставка Android APK** із проєктів React Native через Telegram

- **Scheduled shutdown** — Use `/scheduleshutdown <HH:MM>` to schedule a one-time shutdown (confirmation only when scheduling).
Додайте **Google Gemini 2.0 Flash** для розблокування:
- **Діалоговий ШІ-чат** із багатоходовою пам'яттю та аналізом зображень
- **Агентне керування комп'ютером** — Gemini може переглядати файли, робити знімки, клікати, друкувати та автоматизувати ваш ПК природною мовою з підтвердженням для деструктивних дій
- **Покращення промптів** через `/enhance`

---

## Основні можливості

Все перелічене нижче працює без налаштування ШІ:

- **Провідник файлової системи**: перегляд, читання та пошук файлів на ПК з телефону в межах схвалених шляхів.
- **Керування робочим столом**: знімки екрана, гарячі клавіші, буфер обміну, управління вікнами, стан акумулятора, сон/вимкнення.
- **Зір та автоматизація інтерфейсу**: OCR-кліки через Tesseract, виявлення елементів через OpenCV.
- **Запис макросів**: запис багатокрокових послідовностей та відтворення однією командою.
- **Інтеграція з Claude Desktop**: дистанційне керування — надсилання промптів, зміна моделей, управління робочими просторами.
- **Інтеграція з VS Code / Antigravity**: відкриття папок, зміна моделей ШІ, керування розширенням Antigravity.
- **Планувальник завдань**: запуск автоматизацій або промптів Claude у визначений час. Завдання зберігаються після перезапуску.
- **Автоматизація збірки**: запуск збірок React Native Android та отримання APK через Telegram.
- **Живий віддалений робочий стіл**: стрімінг робочого стола в будь-який браузер через захищений HTTPS-тунель — без пробросу портів. Повне керування мишею та клавіатурою зі смартфона, зум, режим трекпада, автовстановлення cloudflared. Див. [docs/REMOTE.md](docs/REMOTE.md).
- **Автоматичне оновлення**: бот може перевіряти та застосовувати оновлення.
- **Легкий**: ~55-70 МБ RAM у простої, <0.5% CPU. Важкі залежності завантажуються лише при потребі.

**Опціонально — потрібні облікові дані Google Gemini:**

- **ШІ-чат та керування комп'ютером**: Gemini 2.0 Flash з багатоходовими розмовами, аналізом зображень та викликом інструментів. Усі деструктивні дії потребують явного підтвердження через кнопки Telegram.
- **Покращення промптів**: `/enhance` — Gemini перепише та покращить ваш промпт.

---

## Як це працює

Pocket Desk Agent запускається як локальний процес на вашому Windows-ПК і підключається **вихідним** з'єднанням до серверів Telegram через long-polling — не потрібне перенаправлення портів, налаштування роутера або динамічний DNS.

```
Ваш телефон → Сервери Telegram → (вихідний polling) → Pocket Desk Agent (локально) → Дія на ПК → Відповідь
```

**Ключові внутрішні компоненти:**

| Компонент | Роль |
| :--- | :--- |
| `python-telegram-bot` | Асинхронний Telegram-клієнт |
| `GeminiClient` | Управління сесіями Gemini API та історією діалогів |
| `FileManager` | Файлові операції в пісочниці — перевірка шляхів |
| `AuthManager` | OAuth для Antigravity, Gemini CLI та API-ключа |
| `SchedulerRegistry` | Збереження завдань на диску, перевірка кожні 5 с |
| `RateLimiter` | Обмежувач швидкості з токен-бакетом на кожну команду |

---

## Сумісність платформ

| Функція | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Файлова система | ✅ | ✅ |
| ШІ-чат (Gemini) | ✅ | ✅ |
| Планування завдань | ✅ | ✅ |
| Знімки екрана | ✅ | ✅ |
| Гарячі клавіші | ✅ | ⚠️ частково |
| Буфер обміну | ✅ | ⚠️ частково |
| Автоматизація інтерфейсу (OCR) | ✅ | ❌ |
| Управління вікнами | ✅ | ❌ |
| Інтеграція Claude Desktop | ✅ | ❌ |
| Інтеграція VS Code | ✅ | ❌ |
| Збірка APK | ✅ | ❌ |
| Живий віддалений робочий стіл (`/remote`) | ✅ | ❌ |
| Автозапуск після входу | ✅ | ❌ |

---

## Перед початком

### 1. Створіть Telegram-бота

1. Відкрийте Telegram і напишіть **[@BotFather](https://t.me/BotFather)**
2. Надішліть `/newbot` і дотримуйтесь інструкцій
3. Скопіюйте **токен бота** — це ваш `TELEGRAM_BOT_TOKEN`

### 2. Отримайте ваш Telegram ID

1. Напишіть **[@userinfobot](https://t.me/userinfobot)** у Telegram
2. Він відповість вашим числовим ID — це ваш `AUTHORIZED_USER_IDS`

### 3. (Опціонально) Облікові дані Google / Gemini

Потрібні лише для ШІ-чату, аналізу зображень або команди `/enhance`.

**Варіант A — OAuth (рекомендовано):** Вбудована підтримка OAuth, окремий проєкт GCP не потрібен. Оберіть **Antigravity OAuth** або **Gemini CLI OAuth** під час налаштування.

**Варіант B — API-ключ:**
1. Перейдіть на [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Створіть API-ключ — це ваш `GOOGLE_API_KEY`

---

## Швидкий старт та встановлення

### Системні вимоги

- **Python 3.11+**
- **Windows 10 або новіше** — для функцій автоматизації інтерфейсу
- **Tesseract OCR** — для `/findtext`, `/smartclick`. Запустіть `pdagent setup` для встановлення
- **Visual C++ Redistributables** — зазвичай вже встановлені

### Варіант A: Встановлення з PyPI (рекомендовано)

```bash
pip install pocket-desk-agent
pdagent
```

При першому запуску `pdagent` запускає інтерактивний майстер налаштування.

```bash
pdagent start        # запуск як фоновий демон
pdagent configure    # повторний запуск майстра налаштування
pdagent setup        # перевірка та встановлення системних залежностей
```

### Варіант B: Режим розробника

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Запуск бота

| Команда | Опис |
| :--- | :--- |
| `pdagent` | Запуск на передньому плані |
| `pdagent start` | Запуск як фоновий демон |
| `pdagent stop` | Зупинка демона |
| `pdagent restart` | Перезапуск демона |
| `pdagent status` | Перевірка стану |
| `pdagent configure` | Майстер налаштування |
| `pdagent setup` | Check and install system dependencies (for example Tesseract OCR) |
| `pdagent startup <enable\|disable\|status\|configure>` | Manage automatic startup after Windows login |
| `pdagent auth` | Управління обліковими даними Gemini |
| `pdagent version` | Версія |

---

## Безпека

Детальну інформацію про безпеку дивіться у **[SECURITY.md](SECURITY.md)**.

---

## Усунення несправностей

**Бот запущений, але не відповідає на повідомлення**
- Переконайтесь, що ваш Telegram ID вказано в `AUTHORIZED_USER_IDS`
- Перевірте `bot.log` у робочій директорії на наявність помилок
- Виконайте `/status` для перевірки підключення до Gemini

**`/findtext` або `/smartclick` повертають помилку**
- Tesseract OCR не встановлено або відсутній у PATH
- Запустіть `pdagent setup` або встановіть вручну: `winget install UB-Mannheim.TesseractOCR`

**Помилка автентифікації Gemini**
- Запустіть `pdagent auth` і оберіть "Увійти", або використайте `/login` у Telegram
- Для OAuth: переконайтесь, що порт `51121` не заблоковано брандмауером

---

**Операція з файлом завершується з помилкою "Access denied" або "Path not allowed"**
- Запитаний шлях знаходиться за межами `APPROVED_DIRECTORIES`.
- Запустіть `pdagent configure` і виберіть **2) Approved Directories**, щоб додати один шлях за допомогою опції **A**, не заменяючи існуючий список.
- Або відредагуйте конфігурацію безпосередньо: `APPROVED_DIRECTORIES="C:\Users\ВашеІмя\Documents,C:\projects"` (абсолютні шляхи через кому).
- Примітка: `CLAUDE_DEFAULT_REPO_PATH` **завжди** додається в пісочницю під час виконання, навіть якщо він не вказаний у `APPROVED_DIRECTORIES`.

**Заплановані завдання не спрацьовують**
- Бот повинен бути запущений у момент наступного запланованого часу — завдання не спрацьовують, якщо бот зупинений.
- Запустіть `/listschedules`, щоб підтвердити, що завдання все ще очікує виконання і формат часу правильний (`HH:MM` у 24-годинному форматі).
- Перевірте вивід `LOG_LEVEL=DEBUG` на наявність помилок планувальника.

## Внесок у проєкт

Дивіться [CONTRIBUTING.md](CONTRIBUTING.md) для отримання інформації про налаштування розробки.

---

## Ліцензія

Розповсюджується під ліцензією MIT. Подробиці у [LICENSE](LICENSE).
