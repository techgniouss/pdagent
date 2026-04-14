# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Unterstützt-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Lizenz-MIT-yellow.svg?style=for-the-badge" alt="Lizenz" />
</p>

<p align="center"><strong>Dein PC in der Hosentasche — Fernsteuerung, KI-Automatisierung und Entwicklerwerkzeuge — alles über Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Befehle</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Entwicklung</a> •
  <a href="CONTRIBUTING.md">Mitwirken</a> •
  <a href="SECURITY.md">Sicherheit</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md"><strong>Deutsch</strong></a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** ist ein selbst gehosteter Telegram-Bot, der dir die vollständige Fernsteuerung deines Windows-PCs von jedem Gerät aus ermöglicht. Er läuft vollständig auf deiner Maschine — kein Cloud-Relay, kein Abonnement, keine Daten verlassen dein Netzwerk außer dem Telegram-Nachrichten-Relay und der optionalen Gemini-API.

Sofort einsatzbereit, ohne KI-Konfiguration:
- **Dateien durchsuchen und lesen** in deinen genehmigten Verzeichnissen
- **Desktop steuern** — Screenshots, Tastenkürzel, Zwischenablage, Fensterwechsel, Ruhezustand, Herunterfahren
- **UI automatisieren** mit OCR-Klicks (Tesseract) und Elementerkennung (OpenCV)
- **Claude Desktop und VS Code fernsteuern** ohne die Tastatur zu berühren
- **Makros aufzeichnen** und mehrstufige Arbeitsabläufe mit einem Befehl wiederholen
- **Aufgaben planen** für einen späteren Zeitpunkt — überleben Neustarts
- **Android-APKs erstellen und liefern** aus React-Native-Projekten über Telegram

**Google Gemini 2.0 Flash**-Zugangsdaten hinzufügen für:
- **Konversationellen KI-Chat** mit Mehrfach-Gesprächsgedächtnis und Bildanalyse
- **Agentische Computersteuerung** — Gemini kann Dateien durchsuchen, Screenshots machen, klicken, tippen und deinen PC auf natürliche Sprache hin automatisieren, mit menschlicher Bestätigung für destruktive Aktionen
- **Prompt-Verbesserung** über `/enhance`

---

## Hauptfunktionen

Alles unten funktioniert ohne KI-Konfiguration:

- **Dateisystem-Explorer**: Dateien auf dem PC vom Telefon durchsuchen, lesen und suchen, beschränkt auf genehmigte Pfade.
- **Desktop-Steuerung**: Screenshots, Tastenkürzel, Zwischenablage, Fensterverwaltung, Akkustand, Ruhezustand/Herunterfahren.
- **Sicht- und UI-Automatisierung**: OCR-Klicks über Tesseract, Elementerkennung über OpenCV.
- **Makro-Aufzeichnung**: Mehrstufige UI-Sequenzen aufzeichnen und mit einem Befehl wiederholen.
- **Claude-Desktop-Integration**: Remote-Steuerung — Prompts senden, Modelle wechseln, Arbeitsbereiche verwalten.
- **VS Code / Antigravity-Integration**: Ordner öffnen, KI-Modelle wechseln, Antigravity-Erweiterung steuern.
- **Aufgabenplaner**: Automatisierungsabläufe oder Claude-Prompts zu einem bestimmten Zeitpunkt ausführen. Aufgaben überleben Neustarts.
- **Build-Automatisierung**: React-Native-Android-Builds starten und APKs über Telegram empfangen.
- **Automatische Updates**: Der Bot kann Updates prüfen und anwenden.
- **Leichtgewichtig**: ~55-70 MB RAM im Leerlauf, <0.5% CPU. Schwere Abhängigkeiten werden nur bei Bedarf geladen.

**Optional — erfordert Google-Gemini-Zugangsdaten:**

- **KI-Chat und Computersteuerung**: Gemini 2.0 Flash mit Mehrfach-Gesprächen, Bildanalyse und Tool-Aufrufen. Alle destruktiven Aktionen erfordern explizite Bestätigung über Telegram-Schaltflächen.
- **Prompt-Verbesserung**: `/enhance` lässt Gemini einen Prompt umschreiben und verbessern.

---

## Funktionsweise

Pocket Desk Agent läuft als lokaler Prozess auf deinem Windows-PC und verbindet sich **ausgehend** mit Telegrams Servern über Long-Polling — kein Port-Forwarding, keine Router-Konfiguration oder dynamisches DNS erforderlich.

```
Dein Telefon → Telegram-Server → (ausgehendes Polling) → Pocket Desk Agent (lokal) → PC-Aktion → Antwort
```

**Wichtige interne Komponenten:**

| Komponente | Rolle |
| :--- | :--- |
| `python-telegram-bot` | Asynchroner Telegram-Client |
| `GeminiClient` | Gemini-API-Sitzungen und Gesprächsverlauf |
| `FileManager` | Datei-I/O in Sandbox — Pfadvalidierung |
| `AuthManager` | OAuth für Antigravity, Gemini CLI und API-Key |
| `SchedulerRegistry` | Aufgaben auf Disk gespeichert, Prüfung alle 60 s |
| `RateLimiter` | Token-Bucket-Ratenbegrenzer pro Benutzer |

---

## Plattformkompatibilität

| Funktion | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Dateisystem | ✅ | ✅ |
| KI-Chat (Gemini) | ✅ | ✅ |
| Aufgabenplanung | ✅ | ✅ |
| Screenshots | ✅ | ✅ |
| Tastenkürzel | ✅ | ⚠️ teilweise |
| Zwischenablage | ✅ | ⚠️ teilweise |
| UI-Automatisierung (OCR) | ✅ | ❌ |
| Fensterverwaltung | ✅ | ❌ |
| Claude-Desktop-Integration | ✅ | ❌ |
| VS-Code-Integration | ✅ | ❌ |
| APK-Build | ✅ | ❌ |
| Autostart nach Anmeldung | ✅ | ❌ |

---

## Vorbereitung

### 1. Telegram-Bot erstellen

1. Öffne Telegram und schreibe **[@BotFather](https://t.me/BotFather)**
2. Sende `/newbot` und folge den Anweisungen
3. Kopiere den **Bot-Token** — das ist dein `TELEGRAM_BOT_TOKEN`

### 2. Telegram-Benutzer-ID ermitteln

1. Schreibe **[@userinfobot](https://t.me/userinfobot)** in Telegram
2. Er antwortet mit deiner numerischen ID — das ist dein `AUTHORIZED_USER_IDS`

### 3. (Optional) Google-/Gemini-Zugangsdaten

Nur für KI-Chat, Bildanalyse oder den Befehl `/enhance` erforderlich.

**Option A — OAuth (empfohlen):** Integrierte OAuth-Unterstützung, kein separates GCP-Projekt nötig. Wähle **Antigravity OAuth** oder **Gemini CLI OAuth** beim Setup.

**Option B — API-Schlüssel:**
1. Gehe zu [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Erstelle einen API-Schlüssel — das ist dein `GOOGLE_API_KEY`

---

## Schnellstart und Installation

### Systemanforderungen

- **Python 3.11+**
- **Windows 10 oder neuer** — für UI-Automatisierungsfunktionen erforderlich
- **Tesseract OCR** — für `/findtext`, `/smartclick`. `pdagent setup` ausführen zum Installieren
- **Visual C++ Redistributables** — normalerweise bereits installiert

### Option A: Installation über PyPI (empfohlen)

```bash
pip install pocket-desk-agent
pdagent
```

Beim ersten Start startet `pdagent` einen interaktiven Einrichtungsassistenten.

```bash
pdagent start        # als Hintergrunddienst starten
pdagent configure    # Einrichtungsassistenten erneut ausführen
pdagent setup        # Systemabhängigkeiten prüfen und installieren
```

### Option B: Lokaler Entwicklermodus

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Bot starten

| Befehl | Beschreibung |
| :--- | :--- |
| `pdagent` | Im Vordergrund ausführen |
| `pdagent start` | Als Hintergrunddienst starten |
| `pdagent stop` | Dienst stoppen |
| `pdagent restart` | Dienst neu starten |
| `pdagent status` | Status prüfen |
| `pdagent configure` | Einrichtungsassistent |
| `pdagent auth` | Gemini-Zugangsdaten verwalten |
| `pdagent version` | Installierte Version anzeigen |

---

## Sicherheit

Ausführliche Sicherheitsinformationen findest du in **[SECURITY.md](SECURITY.md)**.

---

## Fehlerbehebung

**Bot startet, reagiert aber nicht auf Nachrichten**
- Bestätige, dass deine Telegram-ID in `AUTHORIZED_USER_IDS` steht
- Prüfe `bot.log` im Arbeitsverzeichnis auf Fehler
- Führe `/status` aus, um die Gemini-Verbindung zu prüfen

**`/findtext` oder `/smartclick` geben einen Fehler zurück**
- Tesseract OCR ist nicht installiert oder nicht im PATH
- Führe `pdagent setup` aus oder installiere manuell: `winget install UB-Mannheim.TesseractOCR`

**Gemini-Authentifizierung schlägt fehl**
- Führe `pdagent auth` aus und wähle "Anmelden", oder nutze `/login` in Telegram
- Für OAuth: Stelle sicher, dass Port `51121` nicht durch eine Firewall blockiert wird

---

## Mitwirken

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Entwicklungssetup, Coding-Standards und das Hinzufügen neuer Befehle.

---

## Lizenz

Vertrieben unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.
