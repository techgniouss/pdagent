# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Suportado-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Licença-MIT-yellow.svg?style=for-the-badge" alt="Licença" />
</p>

<p align="center"><strong>Seu PC no bolso — controle remoto, automação com IA e ferramentas de desenvolvimento — tudo pelo Telegram.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Comandos</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Desenvolvimento</a> •
  <a href="CONTRIBUTING.md">Contribuir</a> •
  <a href="SECURITY.md">Segurança</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md"><strong>Português</strong></a> •
  <a href="README.ko.md">한국어</a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent** é um bot Telegram auto-hospedado que oferece controle remoto completo do seu PC com Windows a partir de qualquer dispositivo. Funciona inteiramente na sua máquina — sem relay na nuvem, sem assinatura, nenhum dado sai da sua rede além do relay de mensagens do Telegram e da API opcional do Gemini.

Pronto para usar, sem configuração de IA:
- **Navegar e ler arquivos** nos seus diretórios aprovados
- **Controlar o desktop** — capturas de tela, atalhos de teclado, área de transferência, troca de janelas, suspensão, desligamento
- **Automatizar a interface** com cliques por OCR (Tesseract) e detecção de elementos (OpenCV)
- **Controlar Claude Desktop e VS Code remotamente** sem tocar no teclado
- **Gravar macros** e reproduzir fluxos com múltiplas etapas com um único comando
- **Agendar tarefas** — sobrevivem a reinicializações
- **Compilar e entregar APKs Android** de projetos React Native pelo Telegram

Adicione credenciais do **Google Gemini 2.0 Flash** para desbloquear:
- **Chat de IA conversacional** com memória de múltiplos turnos e análise de imagens
- **Controle agêntico do computador** — o Gemini pode navegar em arquivos, tirar capturas, clicar, digitar e automatizar seu PC em linguagem natural, com confirmação humana para ações destrutivas
- **Melhoria de prompts** com `/enhance`

---

## Principais funcionalidades

Tudo abaixo funciona sem configuração de IA:

- **Explorador de sistema de arquivos**: navegue, leia e pesquise arquivos no PC pelo celular, limitado a caminhos aprovados.
- **Controle do desktop**: capturas de tela, atalhos de teclado, área de transferência, gerenciamento de janelas, status da bateria, suspensão/desligamento.
- **Visão e automação de UI**: cliques OCR via Tesseract, detecção de elementos via OpenCV.
- **Gravação de macros**: grave sequências com múltiplas etapas e reproduza com um comando.
- **Integração com Claude Desktop**: controle remoto — envie prompts, troque modelos, gerencie espaços de trabalho.
- **Integração com VS Code / Antigravity**: abra pastas, troque modelos de IA, controle a extensão Antigravity.
- **Agendador de tarefas**: execute automações ou prompts do Claude em um horário específico. As tarefas sobrevivem a reinicializações.
- **Automação de build**: acione builds React Native Android e receba APKs pelo Telegram.
- **Atualização automática**: o bot pode verificar e aplicar atualizações.
- **Leve**: ~55-70 MB de RAM em repouso, <0.5% de CPU. Dependências pesadas são carregadas apenas quando necessário.

**Opcional — requer credenciais do Google Gemini:**

- **Chat de IA e controle do computador**: Gemini 2.0 Flash com conversação de múltiplos turnos, análise de imagens e chamadas de ferramentas. Todas as ações destrutivas requerem confirmação explícita via botões do Telegram.
- **Melhoria de prompts**: `/enhance` faz o Gemini reescrever e melhorar um prompt.

---

## Como funciona

O Pocket Desk Agent executa como processo local no seu PC Windows e se conecta **de saída** aos servidores do Telegram via long-polling — nenhum redirecionamento de porta, configuração de roteador ou DNS dinâmico é necessário.

```
Seu telefone → Servidores Telegram → (polling de saída) → Pocket Desk Agent (local) → Ação no PC → Resposta
```

**Componentes internos principais:**

| Componente | Função |
| :--- | :--- |
| `python-telegram-bot` | Cliente Telegram assíncrono |
| `GeminiClient` | Sessões da API Gemini e histórico de conversa |
| `FileManager` | E/S de arquivos em sandbox — validação de caminhos |
| `AuthManager` | OAuth para Antigravity, Gemini CLI e chave API |
| `SchedulerRegistry` | Tarefas persistidas em disco, verificação a cada 60 s |
| `RateLimiter` | Limitador de taxa por token por usuário |

---

## Compatibilidade de plataformas

| Funcionalidade | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Sistema de arquivos | ✅ | ✅ |
| Chat de IA (Gemini) | ✅ | ✅ |
| Agendamento de tarefas | ✅ | ✅ |
| Capturas de tela | ✅ | ✅ |
| Atalhos de teclado | ✅ | ⚠️ parcial |
| Área de transferência | ✅ | ⚠️ parcial |
| Automação UI (OCR) | ✅ | ❌ |
| Gerenciamento de janelas | ✅ | ❌ |
| Integração Claude Desktop | ✅ | ❌ |
| Integração VS Code | ✅ | ❌ |
| Build de APK | ✅ | ❌ |
| Inicialização automática | ✅ | ❌ |

---

## Antes de começar

### 1. Criar um bot no Telegram

1. Abra o Telegram e escreva para **[@BotFather](https://t.me/BotFather)**
2. Envie `/newbot` e siga as instruções
3. Copie o **token do bot** — é o seu `TELEGRAM_BOT_TOKEN`

### 2. Obter seu ID de usuário do Telegram

1. Escreva para **[@userinfobot](https://t.me/userinfobot)** no Telegram
2. Ele responderá com seu ID numérico — é o seu `AUTHORIZED_USER_IDS`

### 3. (Opcional) Credenciais do Google / Gemini

Necessárias apenas para chat de IA, análise de imagens ou o comando `/enhance`.

**Opção A — OAuth (recomendado):** Suporte OAuth integrado, sem projeto GCP separado. Escolha **Antigravity OAuth** ou **Gemini CLI OAuth** durante a configuração.

**Opção B — Chave API:**
1. Acesse [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Crie uma chave API — é o seu `GOOGLE_API_KEY`

---

## Início rápido e instalação

### Requisitos do sistema

- **Python 3.11+**
- **Windows 10 ou posterior** — necessário para funções de automação de UI
- **Tesseract OCR** — para `/findtext`, `/smartclick`. Execute `pdagent setup` para instalar
- **Visual C++ Redistributables** — normalmente já instalado

### Opção A: Instalar pelo PyPI (recomendado)

```bash
pip install pocket-desk-agent
pdagent
```

Na primeira execução, o `pdagent` inicia um assistente de configuração interativo.

```bash
pdagent start        # executar como daemon em segundo plano
pdagent configure    # executar novamente o assistente de configuração
pdagent setup        # verificar e instalar dependências do sistema
```

### Opção B: Modo desenvolvedor local

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Executar o bot

| Comando | Descrição |
| :--- | :--- |
| `pdagent` | Executar em primeiro plano |
| `pdagent start` | Iniciar como daemon em segundo plano |
| `pdagent stop` | Parar o daemon |
| `pdagent restart` | Reiniciar o daemon |
| `pdagent status` | Verificar status do daemon |
| `pdagent configure` | Assistente de configuração |
| `pdagent setup` | Check and install system dependencies (for example Tesseract OCR) |
| `pdagent startup <enable\|disable\|status\|configure>` | Manage automatic startup after Windows login |
| `pdagent auth` | Gerenciar credenciais do Gemini |
| `pdagent version` | Versão instalada |

---

## Segurança

Para informações detalhadas de segurança, consulte **[SECURITY.md](SECURITY.md)**.

---

## Solução de problemas

**O bot inicia mas não responde às mensagens**
- Confirme que seu ID do Telegram está em `AUTHORIZED_USER_IDS`
- Verifique `bot.log` no seu diretório de trabalho
- Execute `/status` para verificar a conexão com o Gemini

**`/findtext` ou `/smartclick` retornam erro**
- Tesseract OCR não está instalado ou não está no PATH
- Execute `pdagent setup` ou instale manualmente: `winget install UB-Mannheim.TesseractOCR`

**Falha na autenticação do Gemini**
- Execute `pdagent auth` e escolha "Entrar", ou use `/login` no Telegram
- Para OAuth: certifique-se de que a porta `51121` não está bloqueada pelo firewall

---

## Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para configuração de desenvolvimento, padrões de código e como adicionar novos comandos.

---

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.
