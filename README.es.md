# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Compatible-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Licencia-MIT-yellow.svg?style=for-the-badge" alt="Licencia" />
</p>

<p align="center"><strong>Tu PC en el bolsillo — control remoto, automatización con IA y herramientas de desarrollo — todo por Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Comandos</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Desarrollo</a> •
  <a href="CONTRIBUTING.md">Contribuir</a> •
  <a href="SECURITY.md">Seguridad</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md"><strong>Español</strong></a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** es un bot de Telegram autohospedado que te da control remoto completo de tu PC con Windows desde cualquier dispositivo. Se ejecuta completamente en tu máquina — sin retransmisión en la nube, sin suscripción, sin datos que salgan de tu red más allá de la retransmisión de mensajes de Telegram y la API opcional de Gemini.

De fábrica, sin configuración de IA:
- **Navega y lee archivos** en tus directorios aprobados
- **Controla el escritorio** — capturas de pantalla, atajos de teclado, portapapeles, cambio de ventanas, suspensión, apagado
- **Automatiza la UI** con clics por OCR (Tesseract) y detección de elementos (OpenCV)
- **Controla Claude Desktop y VS Code** de forma remota sin tocar el teclado
- **Graba macros** y reproduce flujos de varios pasos con un solo comando
- **Programa tareas** para que se ejecuten mientras duermes — sobreviven a los reinicios
- **Compila y entrega APKs de Android** desde proyectos React Native vía Telegram

- **Scheduled shutdown** — Use `/scheduleshutdown <HH:MM>` to schedule a one-time shutdown (confirmation only when scheduling).
Agrega credenciales de **Google Gemini 2.0 Flash** para desbloquear:
- **Chat conversacional con IA** con memoria de múltiples turnos y análisis de imágenes
- **Control de computadora agentivo** — Gemini puede navegar archivos, tomar capturas, hacer clic, escribir y automatizar tu PC en lenguaje natural, con confirmación humana para acciones destructivas
- **Mejora de prompts** con `/enhance`

---

## Características principales

Todo lo siguiente funciona sin configuración de IA:

- **Explorador de sistema de archivos**: navega, lee y busca archivos en el PC desde tu teléfono, limitado a rutas aprobadas.
- **Control de escritorio**: capturas, atajos de teclado, portapapeles, cambio de ventanas, estado de batería, suspensión/apagado.
- **Visión y automatización de UI**: clics por OCR con Tesseract, detección de elementos con OpenCV.
- **Grabación de macros**: graba secuencias de varios pasos y reprodúcelas con un comando.
- **Integración con Claude Desktop**: control remoto del app — envía prompts, cambia modelos, gestiona espacios de trabajo.
- **Integración con VS Code / Antigravity**: abre carpetas, cambia modelos de IA, controla la extensión Antigravity.
- **Programador de tareas**: ejecuta automatizaciones o prompts de Claude en un horario específico. Las tareas sobreviven a los reinicios.
- **Automatización de compilaciones**: activa compilaciones de React Native y recibe APKs por Telegram.
- **Escritorio remoto en vivo**: transmite tu escritorio a cualquier navegador a través de un túnel HTTPS seguro — sin reenvío de puertos. Control completo de ratón y teclado desde el móvil, con zoom, trackpad y autoinstalación de cloudflared. Ver [docs/REMOTE.md](docs/REMOTE.md).
- **Actualización automática**: el bot puede buscar y aplicar actualizaciones.
- **Ligero**: ~55-70 MB de RAM en reposo, <0.5% de CPU. Las dependencias pesadas se cargan solo cuando se usan.

**Opcional — requiere credenciales de Google Gemini:**

- **Chat de IA y control de computadora**: Gemini 2.0 Flash con conversación de múltiples turnos, análisis de imágenes y llamadas a herramientas. Todas las acciones destructivas requieren confirmación explícita vía botones de Telegram.
- **Mejora de prompts**: usa `/enhance` para que Gemini reescriba y mejore un prompt.

---

## Cómo funciona

Pocket Desk Agent se ejecuta como proceso local en tu PC y se conecta **hacia afuera** a los servidores de Telegram mediante long-polling — no se requiere reenvío de puertos, configuración de router ni DNS dinámico.

```
Tu teléfono → Servidores Telegram → (polling saliente) → Pocket Desk Agent (local) → Acción en PC → Respuesta
```

**Componentes internos clave:**

| Componente | Rol |
| :--- | :--- |
| `python-telegram-bot` | Cliente Telegram asíncrono |
| `GeminiClient` | Sesiones Gemini API e historial de conversación |
| `FileManager` | E/S de archivos en sandbox — valida rutas |
| `AuthManager` | OAuth para Antigravity, Gemini CLI y API key |
| `SchedulerRegistry` | Tareas persistidas en disco, verificación cada 5 s |
| `RateLimiter` | Limitador de velocidad por usuario en cada comando |

---

## Compatibilidad de plataformas

| Función | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Sistema de archivos | ✅ | ✅ |
| Chat de IA (Gemini) | ✅ | ✅ |
| Programación de tareas | ✅ | ✅ |
| Capturas de pantalla | ✅ | ✅ |
| Atajos de teclado | ✅ | ⚠️ parcial |
| Portapapeles | ✅ | ⚠️ parcial |
| Automatización UI (OCR) | ✅ | ❌ |
| Gestión de ventanas | ✅ | ❌ |
| Integración Claude Desktop | ✅ | ❌ |
| Integración VS Code | ✅ | ❌ |
| Compilación de APK | ✅ | ❌ |
| Escritorio remoto (`/remote`) | ✅ | ❌ |
| Inicio automático | ✅ | ❌ |

---

## Antes de empezar

### 1. Crea un bot de Telegram

1. Abre Telegram y escríbele a **[@BotFather](https://t.me/BotFather)**
2. Envía `/newbot` y sigue las instrucciones
3. Copia el **token del bot** — es tu `TELEGRAM_BOT_TOKEN`

### 2. Obtén tu ID de usuario de Telegram

1. Escríbele a **[@userinfobot](https://t.me/userinfobot)** en Telegram
2. Te responderá con tu ID numérico — es tu `AUTHORIZED_USER_IDS`

### 3. (Opcional) Credenciales de Google / Gemini

Solo necesarias para chat de IA, análisis de imágenes o el comando `/enhance`.

**Opción A — OAuth (recomendado):** Soporte OAuth integrado, sin proyecto GCP separado. Elige **Antigravity OAuth** o **Gemini CLI OAuth** durante la configuración.

**Opción B — Clave API:**
1. Ve a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Crea una clave API — es tu `GOOGLE_API_KEY`

---

## Inicio rápido e instalación

### Requisitos del sistema

- **Python 3.11+**
- **Windows 10 o posterior** — requerido para funciones de automatización de UI
- **Tesseract OCR** — para `/findtext`, `/smartclick`. Ejecuta `pdagent setup` para instalarlo
- **Visual C++ Redistributables** — normalmente ya están instalados

### Opción A: Instalar desde PyPI (recomendado)

```bash
pip install pocket-desk-agent
pdagent
```

En el primer arranque, `pdagent` lanza un asistente de configuración interactivo.

```bash
pdagent start        # ejecutar como demonio en segundo plano
pdagent configure    # volver a ejecutar el asistente de configuración
pdagent setup        # verificar e instalar dependencias del sistema
```

### Opción B: Modo desarrollador local

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Ejecutar el bot

| Comando | Descripción |
| :--- | :--- |
| `pdagent` | Ejecutar en primer plano |
| `pdagent start` | Iniciar como demonio en segundo plano |
| `pdagent stop` | Detener el demonio |
| `pdagent restart` | Reiniciar el demonio |
| `pdagent status` | Verificar estado del demonio |
| `pdagent configure` | Asistente de configuración |
| `pdagent setup` | Check and install system dependencies (for example Tesseract OCR) |
| `pdagent startup <enable\|disable\|status\|configure>` | Manage automatic startup after Windows login |
| `pdagent auth` | Gestionar credenciales de Gemini |
| `pdagent version` | Versión instalada |

---

## Seguridad

Para información de seguridad detallada, consulta **[SECURITY.md](SECURITY.md)**.

---

## Solución de problemas

**El bot arranca pero no responde a los mensajes**
- Confirma que tu ID de Telegram está en `AUTHORIZED_USER_IDS`
- Revisa `bot.log` en tu directorio de trabajo
- Ejecuta `/status` para verificar la conexión con Gemini

**`/findtext` o `/smartclick` devuelven un error**
- Tesseract OCR no está instalado o no está en PATH
- Ejecuta `pdagent setup` o instálalo manualmente: `winget install UB-Mannheim.TesseractOCR`

**Falla la autenticación de Gemini**
- Ejecuta `pdagent auth` y elige "Iniciar sesión", o usa `/login` en Telegram
- Para OAuth: asegúrate de que el puerto `51121` no esté bloqueado por el firewall

---

**La operación de archivo falla con "Access denied" o "Path not allowed"**
- La ruta solicitada está fuera de `APPROVED_DIRECTORIES`.
- Ejecute `pdagent configure` y elija **2) Approved Directories** para agregar una sola ruta usando la opción **A**, sin reemplazar la lista existente.
- O edite la configuración directamente: `APPROVED_DIRECTORIES="C:\Users\SuNombre\Documents,C:\projects"` (rutas absolutas separadas por comas).
- Nota: `CLAUDE_DEFAULT_REPO_PATH` **siempre** se agrega al sandbox en tiempo de ejecución, incluso si no figura en `APPROVED_DIRECTORIES`.

**Las tareas programadas no se activan**
- El bot debe estar ejecutándose cuando llegue la hora programada; las tareas no se activan si el bot está detenido.
- Ejecute `/listschedules` para confirmar que la tarea aún está pendiente y que el formato de hora es correcto (`HH:MM` en formato de 24 horas).
- Verifique la salida de `LOG_LEVEL=DEBUG` para ver errores del programador.

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para la configuración de desarrollo, estándares de código y cómo agregar nuevos comandos.

---

## Licencia

Distribuido bajo la licencia MIT. Consulta [LICENSE](LICENSE) para más detalles.
