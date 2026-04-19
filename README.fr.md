# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Compatible-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Licence-MIT-yellow.svg?style=for-the-badge" alt="Licence" />
</p>

<p align="center"><strong>Votre PC dans votre poche — contrôle à distance, automatisation IA et outils de développement — tout via Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Commandes</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Développement</a> •
  <a href="CONTRIBUTING.md">Contribuer</a> •
  <a href="SECURITY.md">Sécurité</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md"><strong>Français</strong></a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** est un bot Telegram auto-hébergé qui vous donne le contrôle total de votre PC Windows depuis n'importe quel appareil. Il fonctionne entièrement sur votre machine — sans relais cloud, sans abonnement, aucune donnée ne quitte votre réseau au-delà du relais de messages Telegram et de l'API Gemini optionnelle.

Prêt à l'emploi, sans configuration IA :
- **Parcourir et lire des fichiers** dans vos répertoires approuvés
- **Contrôler le bureau** — captures d'écran, raccourcis clavier, presse-papiers, changement de fenêtres, mise en veille, arrêt
- **Automatiser l'interface** avec des clics par OCR (Tesseract) et détection d'éléments (OpenCV)
- **Piloter Claude Desktop et VS Code** à distance sans toucher le clavier
- **Enregistrer des macros** et rejouer des flux multi-étapes en une seule commande
- **Planifier des tâches** — survivent aux redémarrages
- **Compiler et livrer des APK Android** depuis des projets React Native via Telegram

Ajoutez les identifiants **Google Gemini 2.0 Flash** pour débloquer :
- **Chat IA conversationnel** avec mémoire multi-tours et analyse d'images
- **Contrôle agentique de l'ordinateur** — Gemini peut parcourir des fichiers, prendre des captures, cliquer, taper et automatiser votre PC en langage naturel, avec confirmation humaine pour les actions destructives
- **Amélioration de prompts** via `/enhance`

---

## Fonctionnalités principales

Tout ce qui suit fonctionne sans configuration IA :

- **Explorateur de système de fichiers** : parcourez, lisez et recherchez des fichiers sur le PC depuis votre téléphone, limité aux chemins approuvés.
- **Contrôle du bureau** : captures d'écran, raccourcis clavier, presse-papiers, gestion des fenêtres, état de la batterie, veille/arrêt.
- **Vision et automatisation UI** : clics OCR via Tesseract, détection d'éléments via OpenCV.
- **Enregistrement de macros** : enregistrez des séquences multi-étapes et rejouez-les en une commande.
- **Intégration Claude Desktop** : contrôle à distance — envoyez des prompts, changez de modèles, gérez les espaces de travail.
- **Intégration VS Code / Antigravity** : ouvrez des dossiers, changez de modèles IA, pilotez l'extension Antigravity.
- **Planificateur de tâches** : exécutez des automatisations ou des prompts Claude à un moment précis. Les tâches survivent aux redémarrages.
- **Automatisation de build** : lancez des builds React Native Android et recevez les APK via Telegram.
- **Mise à jour automatique** : le bot peut vérifier et appliquer des mises à jour.
- **Léger** : ~55-70 Mo de RAM au repos, <0.5% de CPU. Les dépendances lourdes sont chargées uniquement à la demande.

**Optionnel — nécessite des identifiants Google Gemini :**

- **Chat IA et contrôle de l'ordinateur** : Gemini 2.0 Flash avec conversation multi-tours, analyse d'images et appels d'outils. Toutes les actions destructives nécessitent une confirmation explicite via les boutons Telegram.
- **Amélioration de prompts** : `/enhance` demande à Gemini de réécrire et améliorer un prompt.

---

## Comment ça fonctionne

Pocket Desk Agent s'exécute comme un processus local sur votre PC Windows et se connecte **en sortant** vers les serveurs Telegram via long-polling — aucune redirection de port, configuration de routeur ou DNS dynamique n'est nécessaire.

```
Votre téléphone → Serveurs Telegram → (polling sortant) → Pocket Desk Agent (local) → Action PC → Réponse
```

**Composants internes clés :**

| Composant | Rôle |
| :--- | :--- |
| `python-telegram-bot` | Client Telegram asynchrone |
| `GeminiClient` | Sessions API Gemini et historique de conversation |
| `FileManager` | E/S de fichiers en bac à sable — validation des chemins |
| `AuthManager` | OAuth pour Antigravity, Gemini CLI et clé API |
| `SchedulerRegistry` | Tâches persistées sur disque, vérification toutes les 60 s |
| `RateLimiter` | Limiteur de débit par jeton par utilisateur |

---

## Compatibilité des plateformes

| Fonctionnalité | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Système de fichiers | ✅ | ✅ |
| Chat IA (Gemini) | ✅ | ✅ |
| Planification de tâches | ✅ | ✅ |
| Captures d'écran | ✅ | ✅ |
| Raccourcis clavier | ✅ | ⚠️ partiel |
| Presse-papiers | ✅ | ⚠️ partiel |
| Automatisation UI (OCR) | ✅ | ❌ |
| Gestion des fenêtres | ✅ | ❌ |
| Intégration Claude Desktop | ✅ | ❌ |
| Intégration VS Code | ✅ | ❌ |
| Build APK | ✅ | ❌ |
| Démarrage automatique | ✅ | ❌ |

---

## Avant de commencer

### 1. Créer un bot Telegram

1. Ouvrez Telegram et écrivez à **[@BotFather](https://t.me/BotFather)**
2. Envoyez `/newbot` et suivez les instructions
3. Copiez le **token du bot** — c'est votre `TELEGRAM_BOT_TOKEN`

### 2. Obtenir votre ID utilisateur Telegram

1. Écrivez à **[@userinfobot](https://t.me/userinfobot)** sur Telegram
2. Il vous répondra avec votre ID numérique — c'est votre `AUTHORIZED_USER_IDS`

### 3. (Optionnel) Identifiants Google / Gemini

Uniquement nécessaires pour le chat IA, l'analyse d'images ou la commande `/enhance`.

**Option A — OAuth (recommandé) :** Support OAuth intégré, sans projet GCP séparé. Choisissez **Antigravity OAuth** ou **Gemini CLI OAuth** lors de la configuration.

**Option B — Clé API :**
1. Allez sur [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Créez une clé API — c'est votre `GOOGLE_API_KEY`

---

## Démarrage rapide et installation

### Configuration requise

- **Python 3.11+**
- **Windows 10 ou ultérieur** — requis pour les fonctions d'automatisation UI
- **Tesseract OCR** — pour `/findtext`, `/smartclick`. Exécutez `pdagent setup` pour l'installer
- **Visual C++ Redistributables** — généralement déjà installés

### Option A : Installation depuis PyPI (recommandé)

```bash
pip install pocket-desk-agent
pdagent
```

Au premier démarrage, `pdagent` lance un assistant de configuration interactif.

```bash
pdagent start        # démarrer comme démon en arrière-plan
pdagent configure    # relancer l'assistant de configuration
pdagent setup        # vérifier et installer les dépendances système
```

### Option B : Mode développeur local

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Lancer le bot

| Commande | Description |
| :--- | :--- |
| `pdagent` | Exécuter au premier plan |
| `pdagent start` | Démarrer comme démon en arrière-plan |
| `pdagent stop` | Arrêter le démon |
| `pdagent restart` | Redémarrer le démon |
| `pdagent status` | Vérifier l'état du démon |
| `pdagent configure` | Assistant de configuration |
| `pdagent auth` | Gérer les identifiants Gemini |
| `pdagent version` | Version installée |

---

## Sécurité

Pour des informations de sécurité détaillées, consultez **[SECURITY.md](SECURITY.md)**.

---

## Dépannage

**Le bot démarre mais ne répond pas aux messages**
- Confirmez que votre ID Telegram est dans `AUTHORIZED_USER_IDS`
- Vérifiez `bot.log` dans votre répertoire de travail
- Exécutez `/status` pour vérifier la connexion Gemini

**`/findtext` ou `/smartclick` retournent une erreur**
- Tesseract OCR n'est pas installé ou absent du PATH
- Exécutez `pdagent setup` ou installez manuellement : `winget install UB-Mannheim.TesseractOCR`

**L'authentification Gemini échoue**
- Exécutez `pdagent auth` et choisissez "Se connecter", ou utilisez `/login` dans Telegram
- Pour OAuth : assurez-vous que le port `51121` n'est pas bloqué par un pare-feu

---

**L'opération sur le fichier échoue avec "Access denied" ou "Path not allowed"**
- Le chemin demandé est en dehors de `APPROVED_DIRECTORIES`.
- Exécutez `pdagent configure` et choisissez **2) Approved Directories** pour ajouter un chemin unique à l'aide de l'option **A**, sans remplacer la liste existante.
- Ou modifiez directement la configuration : `APPROVED_DIRECTORIES="C:\Utilisateurs\VotreNom\Documents,C:\projets"` (chemins absolus séparés par des virgules).
- Remarque : `CLAUDE_DEFAULT_REPO_PATH` est **toujours** ajouté au bac à sable (sandbox) au moment de l'exécution, même s'il n'est pas répertorié dans `APPROVED_DIRECTORIES`.

**Les tâches planifiées ne se déclenchent pas**
- Le bot doit être en cours d'exécution au moment prévu — les tâches ne se déclenchent pas si le bot est arrêté.
- Exécutez `/listschedules` pour confirmer que la tâche est toujours en attente et que le format de l'heure est correct (`HH:MM` au format 24 heures).
- Vérifiez la sortie `LOG_LEVEL=DEBUG` pour les erreurs du planificateur.

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour la configuration du développement, les standards de code et l'ajout de nouvelles commandes.

---

## Licence

Distribué sous licence MIT. Voir [LICENSE](LICENSE) pour les détails.
