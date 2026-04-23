# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-Desteklenir-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Lisans-MIT-yellow.svg?style=for-the-badge" alt="Lisans" />
</p>

<p align="center"><strong>PC'niz cebinizde — uzaktan kontrol, yapay zeka otomasyonu ve geliştirici araçları — hepsi Telegram üzerinden.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">Komutlar</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">Geliştirme</a> •
  <a href="CONTRIBUTING.md">Katkıda Bulunma</a> •
  <a href="SECURITY.md">Güvenlik</a>
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
  <a href="README.tr.md"><strong>Türkçe</strong></a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent**, herhangi bir cihazdan Windows PC'nizi tamamen uzaktan kontrol etmenizi sağlayan kendi kendine barındırılan bir Telegram botudur. Tamamen kendi makinenizde çalışır — bulut geçişi yok, abonelik yok, Telegram mesaj geçişi ve isteğe bağlı Gemini API dışında ağınızdan veri çıkmaz.

Yapay zeka ayarı olmadan, kullanıma hazır:
- **Dosyaları gezin ve okuyun** — onaylı dizinlerinizdeki
- **Masaüstünü kontrol edin** — ekran görüntüsü, klavye kısayolları, pano, pencere değiştirme, uyku modu, kapatma
- **Arayüzü otomatikleştirin** — OCR tıklamaları (Tesseract) ve öğe tespiti (OpenCV) ile
- **Claude Desktop ve VS Code'u uzaktan kontrol edin** — klavyeye dokunmadan
- **Makro kayıt edin** — çok adımlı iş akışlarını tek komutla oynatın
- **Görevleri zamanlayın** — yeniden başlatmalar sonrasında da devam eder
- **Android APK'ları derleyin ve teslim edin** — React Native projelerinden Telegram üzerinden

**Google Gemini 2.0 Flash** kimlik bilgilerini ekleyerek açılacak özellikler:
- **Konuşmalı yapay zeka sohbeti** — çok turlu bellek ve görüntü analizi
- **Ajanlı bilgisayar kontrolü** — Gemini dosyaları gezebilir, ekran görüntüsü alabilir, tıklayabilir, yazabilir ve doğal dil ile PC'nizi otomatikleştirebilir. Yıkıcı işlemler için insan onayı gerekir
- **İstem geliştirme** `/enhance` komutu ile

---

## Temel Özellikler

Aşağıdakilerin tümü yapay zeka yapılandırması olmadan çalışır:

- **Dosya Sistemi Gezgini**: Telefonden PC dosyalarını gezin, okuyun ve arayın; onaylı yollarla sınırlı.
- **Masaüstü Kontrolü**: Ekran görüntüsü, klavye kısayolları, pano, pencere yönetimi, pil durumu, uyku/kapatma.
- **Görsel ve Arayüz Otomasyonu**: Tesseract OCR tıklamaları, OpenCV öğe tespiti.
- **Makro Kaydı**: Çok adımlı dizileri kaydedin ve tek komutla oynatın.
- **Claude Desktop Entegrasyonu**: Uzaktan kontrol — istemler gönderin, modeller değiştirin, çalışma alanlarını yönetin.
- **VS Code / Antigravity Entegrasyonu**: Klasörler açın, yapay zeka modeli değiştirin, Antigravity uzantısını kontrol edin.
- **Görev Zamanlayıcı**: Belirli bir zamanda otomasyon veya Claude istemleri çalıştırın. Görevler yeniden başlatmalar sonrasında da devam eder.
- **Derleme Otomasyonu**: React Native Android derlemelerini tetikleyin ve APK'ları Telegram ile alın.
- **Otomatik Güncelleme**: Bot güncellemeleri kontrol edip uygulayabilir.
- **Hafif**: Boşta ~55-70 MB RAM, <0.5% CPU. Ağır bağımlılıklar yalnızca ihtiyaç duyulduğunda yüklenir.

**İsteğe bağlı — Google Gemini kimlik bilgileri gerektirir:**

- **Yapay Zeka Sohbeti ve Bilgisayar Kontrolü**: Gemini 2.0 Flash ile çok turlu konuşma, görüntü analizi ve araç çağrıları. Tüm yıkıcı işlemler Telegram düğmeleri aracılığıyla açık insan onayı gerektirir.
- **İstem Geliştirme**: `/enhance`, Gemini'nin bir istemi yeniden yazmasını ve geliştirmesini sağlar.

---

## Nasıl Çalışır

Pocket Desk Agent, Windows PC'nizde yerel bir süreç olarak çalışır ve long-polling ile **dışa doğru** Telegram sunucularına bağlanır — bağlantı noktası yönlendirme, yönlendirici yapılandırması veya dinamik DNS gerekmez.

```
Telefonunuz → Telegram Sunucuları → (giden polling) → Pocket Desk Agent (yerel) → PC İşlemi → Yanıt
```

**Temel dahili bileşenler:**

| Bileşen | Rol |
| :--- | :--- |
| `python-telegram-bot` | Asenkron Telegram istemcisi |
| `GeminiClient` | Gemini API oturumları ve konuşma geçmişi |
| `FileManager` | Korumalı dosya G/Ç — yol doğrulama |
| `AuthManager` | Antigravity, Gemini CLI ve API anahtarı için OAuth |
| `SchedulerRegistry` | Görevler diske kalıcı olarak kaydedilir, 60 sn'de bir kontrol |
| `RateLimiter` | Komut başına kullanıcı başına token kova hız sınırlayıcısı |

---

## Platform Uyumluluğu

| Özellik | Windows | macOS / Linux |
| :--- | :---: | :---: |
| Dosya sistemi | ✅ | ✅ |
| Yapay zeka sohbeti (Gemini) | ✅ | ✅ |
| Görev zamanlama | ✅ | ✅ |
| Ekran görüntüsü | ✅ | ✅ |
| Klavye kısayolları | ✅ | ⚠️ kısmi |
| Pano | ✅ | ⚠️ kısmi |
| Arayüz otomasyonu (OCR) | ✅ | ❌ |
| Pencere yönetimi | ✅ | ❌ |
| Claude Desktop entegrasyonu | ✅ | ❌ |
| VS Code entegrasyonu | ✅ | ❌ |
| APK derlemesi | ✅ | ❌ |
| Oturum açma sonrası otomatik başlatma | ✅ | ❌ |

---

## Başlamadan Önce

### 1. Telegram Botu Oluşturun

1. Telegram'ı açın ve **[@BotFather](https://t.me/BotFather)**'a mesaj gönderin
2. `/newbot` gönderin ve talimatları izleyin
3. **Bot tokenını** kopyalayın — bu sizin `TELEGRAM_BOT_TOKEN`'ınız

### 2. Telegram Kullanıcı ID'nizi Alın

1. Telegram'da **[@userinfobot](https://t.me/userinfobot)**'a mesaj gönderin
2. Sayısal ID ile yanıt verecek — bu sizin `AUTHORIZED_USER_IDS`'iniz

### 3. (İsteğe Bağlı) Google / Gemini Kimlik Bilgileri

Yalnızca yapay zeka sohbeti, görüntü analizi veya `/enhance` komutu için gereklidir.

**Seçenek A — OAuth (önerilen):** Dahili OAuth desteği, ayrı GCP projesi gerekmez. Kurulum sırasında **Antigravity OAuth** veya **Gemini CLI OAuth** seçin.

**Seçenek B — API Anahtarı:**
1. [Google AI Studio](https://aistudio.google.com/app/apikey)'ya gidin
2. API anahtarı oluşturun — bu sizin `GOOGLE_API_KEY`'iniz

---

## Hızlı Başlangıç ve Kurulum

### Sistem Gereksinimleri

- **Python 3.11+**
- **Windows 10 veya üzeri** — UI otomasyon özellikleri için gerekli
- **Tesseract OCR** — `/findtext`, `/smartclick` için. `pdagent setup` ile kurulum yapın
- **Visual C++ Yeniden Dağıtılabilir Dosyaları** — genellikle zaten yüklü

### Seçenek A: PyPI'dan Kurulum (önerilen)

```bash
pip install pocket-desk-agent
pdagent
```

İlk çalıştırmada `pdagent` etkileşimli bir kurulum sihirbazı başlatır.

```bash
pdagent start        # arka plan daemon olarak çalıştır
pdagent configure    # kurulum sihirbazını yeniden çalıştır
pdagent setup        # sistem bağımlılıklarını kontrol et ve kur
```

### Seçenek B: Yerel Geliştirici Modu

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## Botu Çalıştırma

| Komut | Açıklama |
| :--- | :--- |
| `pdagent` | Ön planda çalıştır |
| `pdagent start` | Arka plan daemon olarak başlat |
| `pdagent stop` | Daemon'ı durdur |
| `pdagent restart` | Daemon'ı yeniden başlat |
| `pdagent status` | Daemon durumunu kontrol et |
| `pdagent configure` | Kurulum sihirbazı |
| `pdagent setup` | Check and install system dependencies (for example Tesseract OCR) |
| `pdagent startup <enable\|disable\|status\|configure>` | Manage automatic startup after Windows login |
| `pdagent auth` | Gemini kimlik bilgilerini yönet |
| `pdagent version` | Kurulu sürüm |

---

## Güvenlik

Ayrıntılı güvenlik bilgileri için **[SECURITY.md](SECURITY.md)**'ye bakın.

---

## Sorun Giderme

**Bot başlıyor ama mesajlara yanıt vermiyor**
- Telegram ID'nizin `AUTHORIZED_USER_IDS`'te olduğunu doğrulayın
- Çalışma dizinindeki `bot.log`'u kontrol edin
- Gemini bağlantısını doğrulamak için `/status` çalıştırın

**`/findtext` veya `/smartclick` hata döndürüyor**
- Tesseract OCR yüklü değil veya PATH'te yok
- `pdagent setup` çalıştırın veya manuel kurulum: `winget install UB-Mannheim.TesseractOCR`

**Gemini kimlik doğrulaması başarısız oluyor**
- `pdagent auth` çalıştırın ve "Giriş Yap" seçin, ya da Telegram'da `/login` kullanın
- OAuth için: `51121` numaralı portun güvenlik duvarı tarafından engellenmediğinden emin olun

---

**Dosya işlemi "Access denied" veya "Path not allowed" hatasıyla başarısız oluyor**
- İstenen yol `APPROVED_DIRECTORIES` dışında.
- `pdagent configure` komutunu çalıştırın ve mevcut listeyi değiştirmeden **A** seçeneğini kullanarak tek bir yol eklemek için **2) Approved Directories** öğesini seçin.
- Veya yapılandırmayı doğrudan düzenleyin: `APPROVED_DIRECTORIES="C:\Kullanıcılar\Adınız\Belgeler,C:\projeler"` (virgülle ayrılmış mutlak yollar).
- Not: `CLAUDE_DEFAULT_REPO_PATH`, `APPROVED_DIRECTORIES` içinde listelenmese bile çalışma zamanında sandbox'a **her zaman** eklenir.

**Planlanan görevler çalışmıyor**
- Planlanan zaman geldiğinde bot çalışıyor olmalıdır; bot durdurulursa görevler tetiklenmez.
- Görevin hala beklemede olduğunu ve zaman formatının doğru olduğunu (`24 saatlik formatta HH:MM`) onaylamak için `/listschedules` komutunu çalıştırın.
- Zamanlayıcı hataları için `LOG_LEVEL=DEBUG` çıktısını kontrol edin.

## Katkıda Bulunma

Geliştirme kurulumu, kodlama standartları ve yeni komut ekleme hakkında bilgi için [CONTRIBUTING.md](CONTRIBUTING.md)'ye bakın.

---

## Lisans

MIT Lisansı kapsamında dağıtılmaktadır. Ayrıntılar için [LICENSE](LICENSE)'a bakın.
