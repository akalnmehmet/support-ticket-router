# Support Ticket Router - Teknik Dokuman

> Musteri destek taleplerini kural tabanli olarak siniflandiran, onceliklendiren, dogru ekibe yonlendiren ve bu sureci CLI, REST API, Celery worker, Streamlit arayuzu ve veritabani katmanlariyla uctan uca sunan teknik sistem dokumani.

Bu dokuman, projedeki README'nin anlattigi urun ve calistirma bilgisini daha teknik bir seviyeye indirger: mimari kararlar, moduller arasi veri akisi, is kurallari, veritabani semasi, API sozlesmesi, Docker servisleri, test kapsami ve gelistirme notlari tek yerde toplanmistir.

---

## Icindekiler

- [1. Proje Ozeti](#1-proje-ozeti)
- [2. Temel Yetenekler](#2-temel-yetenekler)
- [3. Teknoloji Yigini](#3-teknoloji-yigini)
- [4. Mimari Genel Bakis](#4-mimari-genel-bakis)
- [5. Klasor ve Dosya Yapisi](#5-klasor-ve-dosya-yapisi)
- [6. Calisma Modlari](#6-calisma-modlari)
- [7. Veri Modeli](#7-veri-modeli)
- [8. Siniflandirma ve Onceliklendirme Motoru](#8-siniflandirma-ve-onceliklendirme-motoru)
- [8b. Yapay Zeka Siniflandirma Katmani](#8b-yapay-zeka-siniflandirma-katmani)
- [9. Veritabani Katmani](#9-veritabani-katmani)
- [10. REST API Katmani](#10-rest-api-katmani)
- [11. Celery Worker ve Kuyruk Mimarisi](#11-celery-worker-ve-kuyruk-mimarisi)
- [12. Streamlit UI ve Admin Panel](#12-streamlit-ui-ve-admin-panel)
- [13. Webhook Bildirimleri](#13-webhook-bildirimleri)
- [14. Docker ve Servis Orkestrasyonu](#14-docker-ve-servis-orkestrasyonu)
- [15. Konfigurasyon](#15-konfigurasyon)
- [16. Test Stratejisi](#16-test-stratejisi)
- [17. Loglama ve Hata Yonetimi](#17-loglama-ve-hata-yonetimi)
- [18. Guvenlik Degerlendirmesi](#18-guvenlik-degerlendirmesi)
- [19. Tasarim Kararlari ve Varsayimlar](#19-tasarim-kararlari-ve-varsayimlar)
- [20. Gelistirme ve Yayina Alma Notlari](#20-gelistirme-ve-yayina-alma-notlari)
- [21. Gelecek Gelistirme Onerileri](#21-gelecek-gelistirme-onerileri)

---

## 1. Proje Ozeti

Support Ticket Router, gelen destek taleplerini otomatik olarak isleyen bir destek talebi yonlendirme motorudur. Sistem, ticket metnini ve musteri tipini analiz ederek uc temel ciktinin uretilmesini saglar:

| Cikti | Aciklama |
|---|---|
| `category` | Talebin konusu: `billing`, `account`, `technical` veya `general` |
| `priority` | Is onceligi: `high`, `medium`, `low` |
| `assignedTeam` | Talebi devralacak destek ekibi |
| `confidence` | AI'in siniflandirma guven skoru (0.0–1.0) |
| `aiUsed` | Siniflandirmada AI mi RegEx mi kullanildi |

Proje yalnizca tek bir script olarak degil, farkli kullanim senaryolarini destekleyen cok katmanli bir uygulama olarak tasarlanmistir:

- **Hibrit AI motoru** — Gemini, HuggingFace, Transformers, Ollama destegi; dusuk guven veya hata durumunda RegEx'e otomatik fallback
- CLI ile batch JSON isleme
- FastAPI ile HTTP uzerinden asenkron ticket kabul etme
- Celery + Redis ile arka planda isleme
- PostgreSQL veya SQLite ile kural ve gecmis saklama
- Streamlit ile son kullanici paneli, AI badge ve admin kural yonetimi
- Discord/Slack uyumlu webhook bildirimleri
- Docker Compose ile cok servisli calistirma

---

## 2. Temel Yetenekler

| Ozellik | Teknik Karsilik |
|---|---|
| Otomatik kategori tespiti | `TicketEvaluator.evaluate_category()` |
| Oncelik hesaplama | Premium musteri, aciliyet kelimeleri ve kategori baglami |
| Ekip yonlendirme | `TeamRouter.route_ticket()` |
| Dinamik kural yonetimi | `categories` ve `priority_rules` tablolarindan okunan kurallar |
| Kalici islem gecmisi | `processed_tickets` tablosu |
| CLI cikti dosyasi | `data/processed_tickets.json` |
| REST API | `POST /api/v1/process-ticket`, `GET /api/v1/task/{task_id}` |
| Asenkron isleme | Celery task + Redis broker/result backend |
| UI | Streamlit dashboard ve admin panel |
| Bildirim | Takim bazli veya genel webhook URL'i |
| Rate limiting | SlowAPI ile IP bazli limit |
| Test kapsami | Unit ve E2E pytest testleri |

---

## 3. Teknoloji Yigini

| Katman | Teknoloji |
|---|---|
| Dil | Python |
| **AI (Birincil)** | **Google Gemini 2.5 Flash Lite** (`google-genai`) |
| **AI (Yedek 1)** | **HuggingFace Inference API** (`huggingface_hub`) |
| **AI (Yedek 2)** | **Yerel Transformers** (`transformers`, `torch`) |
| **AI (Yedek 3)** | **Ollama** (yerel LLM, ayri kurulum) |
| API | FastAPI, Uvicorn |
| Veri dogrulama | Pydantic |
| Arka plan isleri | Celery |
| Kuyruk ve sonuc backend'i | Redis |
| Veritabani | PostgreSQL 16 veya SQLite |
| UI | Streamlit |
| Admin panel tablo gorunumu | Pandas + Streamlit dataframe |
| Bildirim | `requests` ile webhook POST |
| Konfigurasyon | `.env`, `config/settings.py` |
| Rate limiting | SlowAPI |
| Test | pytest, unittest.mock (72 test) |
| Konteyner | Docker, Docker Compose |

---

## 4. Mimari Genel Bakis

Sistemin cekirdegi artik `HybridClassifier` uzerinden calisir. CLI, API worker ve Streamlit UI ayni siniflandirici zincirini kullanir:

```text
Input Ticket
    |
    v
┌─────────────────────────────┐
│      HybridClassifier       │
│  ┌────────────────────────┐ │
│  │     AI Provider        │ │  <- Gemini / HuggingFace / Transformers / Ollama
│  └───────────┬────────────┘ │
│  confidence >= threshold?   │
│              | Hayir        │
│              v              │
│  ┌────────────────────────┐ │
│  │   TicketEvaluator      │ │  <- RegEx motoru (degismez)
│  └────────────────────────┘ │
│       TeamRouter            │
└─────────────────────────────┘
    |
    v
ProcessedTicket { category, priority, assignedTeam, reason, confidence, aiUsed }
```

Docker/API senaryosunda asenkron akis:

```text
Client
  |
  | POST /api/v1/process-ticket
  v
FastAPI
  |
  | process_ticket_task.delay(...)
  v
Redis Broker
  |
  v
Celery Worker
  |
  | HybridClassifier.process(ticket)
  |   -> AI Provider (Gemini vs.)
  |   -> fallback: TicketEvaluator
  | TeamRouter.route_ticket()
  | send_webhook()
  | save_processed_ticket()
  v
Redis Result Backend + Database
  ^
  |
  | GET /api/v1/task/{task_id}
Client polls result
```

Bu ayrim sayesinde:

- API hizli cevap verir ve uzun sureli AI islemini kuyruga devreder.
- Worker sayisi arttirilarak isleme kapasitesi yatay olarak buyutulebilir.
- AI provider `.env` degiskeni ile kod degisikligi olmadan degistirilebilir.
- CLI, UI ve API ayni `HybridClassifier` kullandigi icin tutarlilik korunur.

---

## 5. Klasor ve Dosya Yapisi

```text
support_ticket_router/
|
|-- api.py                      # FastAPI REST API
|-- worker.py                   # Celery worker (HybridClassifier kullaniyor)
|-- main.py                     # CLI batch processor
|-- app.py                      # Streamlit UI + AI badge
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
|-- README.md
|-- TECHNICAL_DOCUMENTATION.md
|
|-- config/
|   |-- settings.py             # AI_PROVIDER, API key'ler dahil tum env vars
|
|-- database/
|   |-- db.py
|
|-- engine/
|   |-- evaluator.py            # RegEx motoru (degismez)
|   |-- router.py
|   |-- notifier.py
|   |-- ai_classifier.py        # [YENİ] HybridClassifier
|   |-- providers/              # [YENİ] AI provider modulleri
|       |-- __init__.py         #   BaseAIProvider soyut sinifi
|       |-- gemini_provider.py  #   Google Gemini
|       |-- huggingface_provider.py
|       |-- transformers_provider.py
|       |-- ollama_provider.py
|
|-- models/
|   |-- ticket.py               # confidence + aiUsed alanlari eklendi
|
|-- tests/
|   |-- test_evaluator.py       # 27 unit test
|   |-- test_e2e.py             # 15 E2E test
|   |-- test_ai_classifier.py   # [YENİ] 30 AI testi
|
|-- data/
|   |-- tickets.json
|   |-- processed_tickets.json
|   |-- rules.db
|
|-- assets/
|   |-- styles.css
|
|-- .streamlit/
|   |-- config.toml
```

### Ana dosyalar

| Dosya | Gorev |
|---|---|
| `main.py` | JSON dosyasindan ticket okuyup isleyen CLI giris noktasi |
| `api.py` | FastAPI uygulamasi ve HTTP endpoint'leri |
| `worker.py` | Celery uygulamasi ve background task tanimi |
| `app.py` | Streamlit dashboard ve admin panel |
| `database/db.py` | Veritabani baglanti, sema, seed, CRUD ve history islemleri |
| `engine/evaluator.py` | Kategori, oncelik ve gerekce uretimi |
| `engine/router.py` | Kategoriden takim atamasi |
| `engine/notifier.py` | Webhook bildirimi |
| `models/ticket.py` | `Ticket` ve `ProcessedTicket` dataclass modelleri |
| `config/settings.py` | Ortam degiskenlerinin merkezi okuma noktasi |

---

## 6. Calisma Modlari

### 6.1 CLI Batch Modu

`main.py`, `data/tickets.json` dosyasini okur, her ticket icin siniflandirma yapar ve sonucu hem konsola hem de `data/processed_tickets.json` dosyasina yazar.

```bash
python main.py
```

Varsayilan giris:

```text
data/tickets.json
```

Varsayilan cikis:

```text
data/processed_tickets.json
```

CLI akisi:

```text
Read JSON -> init_db -> load rules -> create evaluator/router -> process each ticket -> write output
```

### 6.2 REST API Modu

`api.py`, ticket'i HTTP uzerinden kabul eder fakat dogrudan islemek yerine Celery kuyruguna ekler. Bu sayede API request'i hizli cevaplanir.

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 6.3 Celery Worker Modu

Worker, Redis kuyrugundan ticket islerini alir ve cekirdek motoru calistirir.

```bash
celery -A worker.celery_app worker --loglevel=info
```

### 6.4 Streamlit UI Modu

`app.py`, son kullanici ve admin panel deneyimini sunar.

```bash
streamlit run app.py
```

### 6.5 Docker Compose Modu

Tavsiye edilen tam sistem calistirma modudur.

```bash
docker compose up --build
```

Bu komut su servisleri ayaga kaldirir:

- PostgreSQL
- Redis
- FastAPI
- Celery worker
- CLI batch processor

---

## 7. Veri Modeli

### 7.1 Gelen Ticket

Python tarafinda `models/ticket.py` icindeki `Ticket` dataclass'i kullanilir:

```python
@dataclass
class Ticket:
    id: int
    subject: str
    message: str
    customer_type: str
    created_at: str
```

API ve JSON girisinde dis sozlesme camelCase kullanir:

```json
{
  "id": 1,
  "subject": "Payment failed",
  "message": "My payment failed but money was withdrawn from my card.",
  "customerType": "premium",
  "createdAt": "2026-04-29T10:00:00Z"
}
```

Kod icinde PEP 8 uyumlu snake_case kullanilir:

| JSON/API | Python |
|---|---|
| `customerType` | `customer_type` |
| `createdAt` | `created_at` |
| `assignedTeam` | `assigned_team` |

### 7.2 Islenmis Ticket

`ProcessedTicket` modeli islenmis sonucu temsil eder:

```python
@dataclass
class ProcessedTicket:
    id: int
    category: str
    priority: str
    assigned_team: str
    reason: str
    confidence: float = 1.0   # AI guven skoru; RegEx icin 1.0 (deterministik)
    ai_used: bool = False      # AI mi yoksa RegEx mi kullanildi
```

Dis cikti formati (AI aktif):

```json
{
  "id": 1,
  "category": "billing",
  "priority": "high",
  "assignedTeam": "payments-team",
  "reason": "The ticket mentions a failed payment and withdrawn money, indicating a billing issue.",
  "confidence": 0.95,
  "aiUsed": true
}
```

Dis cikti formati (RegEx fallback):

```json
{
  "id": 1,
  "category": "billing",
  "priority": "high",
  "assignedTeam": "payments-team",
  "reason": "Classified as billing because payment and money matched strongest. Marked high priority because customer is premium.",
  "confidence": 1.0,
  "aiUsed": false
}
```

---

## 8. Siniflandirma ve Onceliklendirme Motoru

Cekirdek is mantigi `engine/evaluator.py` icindeki `TicketEvaluator` sinifindadir.

### 8.1 Kategori Tespiti

`evaluate_category(ticket)` metodu, ticket'in `subject` ve `message` alanlarini birlestirir, lowercase hale getirir ve veritabanindan yuklenen kategori kurallari uzerinden arama yapar.

Varsayilan kategoriler:

| Kategori | Anahtar Kelimeler | Ekip |
|---|---|---|
| `billing` | `refund`, `invoice`, `charge`, `payment`, `billing`, `money`, `paid`, `card`, `withdrawn` | `payments-team` |
| `account` | `password`, `login`, `authentication`, `account`, `access` | `account-support` |
| `technical` | `crash`, `bug`, `error`, `broken`, `loading`, `upload`, `not working` | `technical-support` |
| `general` | Bos kural, fallback kategori | `general-support` |

Eger hicbir kategori kelimesi eslesmezse sonuc `general` olur.

### 8.2 Regex Kelime Siniri

Anahtar kelime aramasi basit substring aramasi degildir. Kod su yaklasimi kullanir:

```python
re.search(rf"\b{re.escape(keyword)}\b", text)
```

Bu karar onemlidir cunku yanlis pozitifleri azaltir:

| Metin | Anahtar Kelime | Beklenen |
|---|---|---|
| `refund request` | `refund` | Eslesir |
| `non-refundable product` | `refund` | Eslesmez |
| `forgot my password` | `password` | Eslesir |

### 8.3 Kategori Cakismasi

Bir ticket birden fazla kategori sinyali tasiyabilir. Yeni davranista kategori secimi artik "ilk eslesen kazanir" mantigina bagli degildir. Bunun yerine `evaluate_category_details()` her kategori icin skor uretir; `evaluate_category()` ise bu detay analizindeki en guclu primary kategoriyi string olarak dondurur.

Skorlama modeli:

| Eslesme yeri | Puan |
|---|---:|
| Subject icindeki keyword eslesmesi | `+2` |
| Message icindeki keyword eslesmesi | `+1` |

Ayni kategoride birden fazla keyword eslesirse puanlar toplanir. Hicbir kategoride eslesme yoksa tum skorlar `0` olur ve sonuc `general` olarak doner.

Ornek 1:

```text
Subject: Payment card issue
Message: I need a refund and cannot login.
```

Skorlar:

| Kategori | Eslesen keyword'ler | Skor |
|---|---|---:|
| `billing` | `payment`, `card`, `refund` | `5` |
| `account` | `login` | `1` |

Bu durumda primary kategori `billing` olur. `account` ise secondary kategori olarak analiz sonucunda korunur.

Ornek 2:

```text
Subject: Cannot login to account
Message: There is a payment problem.
```

Skorlar:

| Kategori | Eslesen keyword'ler | Skor |
|---|---|---:|
| `account` | `login`, `account` subject icinde | `4` |
| `billing` | `payment` message icinde | `1` |

Subject eslesmeleri daha yuksek agirlikli oldugu icin primary kategori `account` olur.

Skor esitliginde deterministik tie-break sirasi kullanilir:

1. Daha yuksek toplam skor kazanir.
2. Toplam skor esitse daha fazla subject keyword eslesmesi olan kategori kazanir.
3. Hala esitse kategori onceligi kullanilir: `billing > technical > account > general`.
4. Hala esitse mevcut kural sirasi fallback olarak kullanilir.

Detay analizi ornek ciktisi:

```json
{
  "category": "billing",
  "scores": {
    "billing": 5,
    "account": 1,
    "technical": 0
  },
  "matched_keywords": {
    "billing": ["refund", "payment", "card"],
    "account": ["login"]
  },
  "secondary_categories": ["account"]
}
```

Bu yapi dis API sozlesmesini bozmaz: `evaluate_category()` hala sadece `"billing"` gibi tek bir kategori string'i dondurur. Daha zengin analiz gerektiginde `evaluate_category_details()` kullanilir.

### 8.4 Oncelik Kurallari

`evaluate_priority(ticket, category)` uc seviyeli sonuc uretir:

| Priority | Kosul |
|---|---|
| `high` | Musteri `premium` ise |
| `high` | Ticket aciliyet kelimesi iceriyorsa |
| `high` | Kategori `billing` ve finansal/acil kelime varsa |
| `medium` | Kategori `technical` veya `account` ise |
| `low` | Diger tum durumlar |

Varsayilan aciliyet kelimeleri:

```text
urgent, asap, emergency, immediately, blocked, cannot use
```

Varsayilan billing urgency kelimeleri:

```text
lawsuit, legal, fraud, scam, money, withdrawn, refund
```

### 8.5 Gerekce Uretimi

`generate_reason(ticket, category, priority)` kullaniciya okunabilir bir aciklama uretir. High priority ise sebepler tek tek birlestirilir:

- Premium musteri
- Aciliyet kelimesi
- Billing baglaminda finansal/acil kelime

Ornek:

```text
Classified as billing and marked high priority because customer is premium and billing ticket contains financial urgency keywords.
```

---

## 8b. Yapay Zeka Siniflandirma Katmani

### 8b.1 HybridClassifier

`engine/ai_classifier.py` icindeki `HybridClassifier` sinifi, AI'yi birincil siniflandirici olarak kullanir; dusuk guven veya hata durumunda mevcut `TicketEvaluator`'e devir yapar.

```python
class HybridClassifier:
    def __init__(self, evaluator, router, ai_provider=None,
                 confidence_threshold=0.65):
        ...

    def process(self, ticket) -> ProcessedTicket:
        # 1. AI provider varsa dene
        # 2. confidence >= threshold -> AI sonucu kullan (aiUsed=True)
        # 3. confidence < threshold veya hata -> RegEx fallback (aiUsed=False)
```

**Temel prensipler:**
- `TicketEvaluator` ve `TeamRouter` degistirilmez; `HybridClassifier` bunlarin ustune yapi kurar.
- `ai_provider=None` durumunda sistem eski davranisiyla tamamen ayni calisir.
- Tum AI hatalari (timeout, rate limit, gecersiz JSON) sessizce yakalanir; caller hic etkilenmez.

### 8b.2 BaseAIProvider Abstraction

`engine/providers/__init__.py`'daki soyut sinif, yeni provider eklemeyi standartlastirir:

```python
class BaseAIProvider(ABC):
    @abstractmethod
    def classify(self, ticket: Ticket) -> dict:
        # Donmesi gereken: {category, priority, reason, confidence}
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...
```

### 8b.3 Provider Karsilastirmasi

| Provider | Paket | Internet | Hiz | `.env` Degeri |
|---|---|---|---|---|
| **Gemini 2.5 Flash Lite** | `google-genai` | Gerekli | Hizli | `gemini` |
| **HuggingFace API** | `huggingface_hub` | Gerekli | Orta | `huggingface` |
| **Yerel Transformers** | `transformers torch` | Yalnizca indirme | Yavas (CPU) | `transformers` |
| **Ollama** | Ayri kurulum | Hayir | Orta | `ollama` |
| **RegEx Only** | Yok | Hayir | Anlik | `none` |

### 8b.4 Guven Esigi

`AI_CONFIDENCE_THRESHOLD` (varsayilan `0.65`) altinda kalan AI sonuclari kabul edilmez ve RegEx motoru devreye girer. Bu degisken `.env` uzerinden ayarlanabilir.

### 8b.5 Sistem Prompt (Gemini)

Gemini provider'i, modeli JSON ciktisina zorlamak icin yapilandirilmis bir sistem promptu kullanir:

```
You are a customer support ticket classifier.
Output ONLY valid JSON: {category, priority, reason, confidence}
billing: payment, refund, invoice...
account: login, password, access...
technical: crash, bug, error...
```

---



Veritabani islemleri `database/db.py` dosyasinda toplanmistir.

### 9.1 Dual Backend Yaklasimi

Sistem iki veritabani modunu destekler:

| Ortam | Backend |
|---|---|
| Docker / production benzeri ortam | PostgreSQL |
| Lokal veya Streamlit Cloud benzeri hafif ortam | SQLite |

Backend secimi `DATABASE_URL` uzerinden yapilir:

```python
DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")
```

Bu kosul saglanirsa `psycopg2` ile PostgreSQL baglantisi kurulur. Saglanmazsa `SQLITE_PATH` uzerinden SQLite dosyasi kullanilir.

### 9.2 Sema

#### `categories`

Kategori ve takim eslestirmelerini tutar.

| Kolon | Tip | Aciklama |
|---|---|---|
| `id` | `SERIAL` veya `INTEGER` | Birincil anahtar |
| `name` | `VARCHAR(100)` | Kategori adi, unique |
| `keywords` | `TEXT` | Virgulle ayrilmis anahtar kelimeler |
| `assigned_team` | `VARCHAR(100)` | Yonlendirilecek ekip |

#### `priority_rules`

Oncelik kelime gruplarini tutar.

| Kolon | Tip | Aciklama |
|---|---|---|
| `id` | `SERIAL` veya `INTEGER` | Birincil anahtar |
| `rule_type` | `VARCHAR(100)` | Ornek: `urgency`, `billing_urgency` |
| `keywords` | `TEXT` | Virgulle ayrilmis kelimeler |

#### `processed_tickets`

Islem gecmisini tutar.

| Kolon | Aciklama |
|---|---|
| `ticket_id` | Orijinal ticket ID |
| `subject` | Talep basligi |
| `message` | Talep metni |
| `customer_type` | Musteri tipi |
| `category` | Uretilen kategori |
| `priority` | Uretilen oncelik |
| `assigned_team` | Atanan ekip |
| `reason` | Uretilen gerekce |
| `processed_at` | Veritabani timestamp'i |

### 9.3 Seed Mekanizmasi

`init_db()` su islemleri yapar:

1. Veritabani baglantisini acar.
2. Tablolari yoksa olusturur.
3. `categories` tablosu bossa varsayilan kategorileri ekler.
4. `priority_rules` tablosu icin varsayilan oncelik kelime gruplarini ekler.
5. `processed_tickets` history tablosunu olusturur.

### 9.4 Admin CRUD Fonksiyonlari

Streamlit admin panel su fonksiyonlari kullanir:

| Fonksiyon | Gorev |
|---|---|
| `add_category()` | Yeni kategori ekler |
| `update_category()` | Kategori adini, kelimelerini ve ekibini gunceller |
| `delete_category()` | Kategori siler |
| `update_priority_keywords()` | Priority kelimelerini gunceller |
| `get_all_categories_raw()` | Admin tablo gorunumu icin kategori listesi |
| `get_all_priority_rules_raw()` | Admin panel icin priority rule listesi |

### 9.5 History Fonksiyonlari

| Fonksiyon | Gorev |
|---|---|
| `save_processed_ticket()` | Islenmis sonucu `processed_tickets` tablosuna yazar |
| `get_recent_processed_tickets()` | UI icin son kayitlari getirir |

---

## 10. REST API Katmani

FastAPI uygulamasi `api.py` icindedir.

### 10.1 Uygulama Baslatma

FastAPI `lifespan` mekanizmasi ile uygulama acilirken `init_db()` cagrilir:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
```

Bu sayede API ayaga kalktiginda veritabani semasi hazir olur.

### 10.2 Request Modeli

`ApiTicketRequest` Pydantic modelidir:

```python
class ApiTicketRequest(BaseModel):
    id: int
    subject: str = ""
    message: str = ""
    customerType: str = Field(default="standard")
    createdAt: str = ""
```

`subject` ve `message` icin whitespace temizligi yapilir. `None` gelen degerler bos string'e normalize edilir.

### 10.3 `POST /api/v1/process-ticket`

Ticket'i asenkron islenmek uzere Celery kuyruguna ekler.

Rate limit:

```text
30 request / minute / IP
```

Request:

```json
{
  "id": 1001,
  "subject": "Urgent refund request",
  "message": "My payment was charged twice, this looks like fraud!",
  "customerType": "premium",
  "createdAt": "2026-05-05T10:00:00Z"
}
```

Response:

```json
{
  "task_id": "celery-task-id",
  "status": "PENDING",
  "result": null
}
```

### 10.4 `GET /api/v1/task/{task_id}`

Celery task durumunu ve hazirsa sonucu dondurur.

Rate limit:

```text
120 request / minute / IP
```

Processing sirasinda:

```json
{
  "task_id": "celery-task-id",
  "status": "PENDING",
  "result": null
}
```

Tamamlandiginda:

```json
{
  "task_id": "celery-task-id",
  "status": "SUCCESS",
  "result": {
    "id": 1001,
    "category": "billing",
    "priority": "high",
    "assignedTeam": "payments-team",
    "reason": "Classified as billing and marked high priority because customer is premium and billing ticket contains financial urgency keywords."
  }
}
```

### 10.5 `GET /health`

Basit liveness endpoint'idir.

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## 11. Celery Worker ve Kuyruk Mimarisi

`worker.py`, Redis'i hem broker hem de result backend olarak kullanan Celery uygulamasini tanimlar:

```python
celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)
```

### 11.1 Worker Engine Cache

Worker, `HybridClassifier` nesnesini (AI provider dahil) thread-local cache ile olusturur:

```python
_thread_local = threading.local()

def _get_classifier() -> HybridClassifier:
    if not getattr(_thread_local, 'initialized', False):
        init_db()
        evaluator = TicketEvaluator(...)
        router = TeamRouter(...)
        ai_provider = _build_ai_provider()  # .env'den okur
        _thread_local.classifier = HybridClassifier(
            evaluator, router, ai_provider, AI_CONFIDENCE_THRESHOLD
        )
        _thread_local.initialized = True
    return _thread_local.classifier
```

Bu yaklasim:

- Her task icin tekrar tekrar AI provider ve engine olusturma maliyetini azaltir.
- Celery concurrency senaryolarinda thread bazli izolasyon saglar.
- AI provider (Gemini connection vb.) worker baslangicinda bir kez kurulur.

### 11.2 Task Akisi

`process_ticket_task(ticket_data)` su adimlari izler:

1. `_get_classifier()` ile thread-local `HybridClassifier` alinir.
2. Raw dictionary, `Ticket` dataclass'ina map edilir.
3. `classifier.process(ticket)` cagrilir — AI veya RegEx yoluyla siniflandirilir.
4. Sonuc `result_data` dict'ine aktarilir (`confidence` ve `aiUsed` dahil).
5. Webhook bildirimi denenir.
6. Sonuc history tablosuna yazilir.
7. Sonuc Redis result backend'e task result olarak doner.

Webhook ve DB history yazimi basarisiz olursa task tamamen fail edilmez; hata loglanir ve ana sonuc donmeye devam eder.

---

## 12. Streamlit UI ve Admin Panel

Streamlit uygulamasi `app.py` icindedir ve iki ana sayfa sunar:

| Sayfa | Gorev |
|---|---|
| Dashboard | Ticket girisi, siniflandirma ve gecmis goruntuleme |
| Admin Panel | Kategori ve priority kurallarini yonetme |

### 12.1 Dashboard

Dashboard'da kullanici:

- Subject girer.
- Message girer.
- Customer Type secer: `Standard` veya `Premium`.
- `Process Ticket` butonuyla ticket'i isler.

UI, CLI ve worker ile ayni motoru kullanir:

```python
evaluator = TicketEvaluator(...)
router = TeamRouter(...)
```

Islem sonucunda:

- Kategori
- Oncelik
- Atanan takim
- Gerekce

ekranda gosterilir ve veritabanina kaydedilmeye calisilir.

### 12.2 History

Ilk yuklemede `get_recent_processed_tickets(50)` ile son 50 kayit alinir. Yeni UI islemleri session state'in basina eklenir.

### 12.3 Admin Login

Admin panel tek parola ile korunur:

```python
ADMIN_PASSWORD
```

Varsayilan deger `config/settings.py` icinde `admin123` olarak tanimlidir, `.env` ile degistirilmelidir.

### 12.4 Admin Panel Kural Yonetimi

Admin panel ile:

- Priority keyword listeleri guncellenebilir.
- Yeni kategori eklenebilir.
- Mevcut kategoriler tablo olarak goruntulenebilir.
- Kategori silinebilir.

`general` fallback kategorisinin silinmesi UI tarafinda engellenir.

### 12.5 Cache Davranisi

`setup_database()` fonksiyonu `@st.cache_resource` ile cache'lenir. Admin panelde kural degisikligi sonrasi:

```python
setup_database.clear()
```

cagrilir ve uygulama yeniden calistirilir. Boylece yeni kurallar aktif hale gelir.

---

## 13. Webhook Bildirimleri

Bildirim katmani `engine/notifier.py` icindedir.

### 13.1 URL Secimi

Takim bazli webhook onceliklidir:

```text
WEBHOOK_<TEAM_NAME>
```

Ornek:

```text
payments-team -> WEBHOOK_PAYMENTS_TEAM
```

Takim bazli URL yoksa genel fallback kullanilir:

```text
DISCORD_WEBHOOK_URL
```

Hic URL yoksa bildirim atlanir.

### 13.2 Payload

Payload Discord embed formatina uygundur:

- Ticket ID ve subject
- Message
- Category
- Priority
- Customer type
- Reason

Priority'ye gore renk atanir:

| Priority | Renk |
|---|---|
| `high` | Kirmizi |
| `medium` | Turuncu |
| `low` | Yesil |

Webhook basarisiz olursa hata loglanir; ticket isleme akisi durdurulmaz.

---

## 14. Docker ve Servis Orkestrasyonu

`docker-compose.yml` bes servis tanimlar:

| Servis | Port | Gorev |
|---|---|---|
| `db` | `5432` | PostgreSQL veritabani |
| `redis` | `6379` | Celery broker/result backend |
| `ticket-router-api` | `8000` | FastAPI uygulamasi |
| `celery-worker` | Yok | Background ticket processor |
| `ticket-router-cli` | Yok | Ornek JSON batch isleme job'i |

### 14.1 Healthcheck

PostgreSQL icin:

```text
pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

Redis icin:

```text
redis-cli ping
```

API, worker ve CLI servisleri bu healthcheck'lere bagli olarak baslar.

### 14.2 Volume Kullanimi

PostgreSQL verisi named volume'da saklanir:

```text
postgres_data:/var/lib/postgresql/data
```

Uygulama `data/` klasoru container icine mount edilir:

```text
./data:/app/data
```

Bu sayede SQLite dosyasi, input/output JSON ve lokal veri dosyalari container ile host arasinda paylasilir.

### 14.3 Dockerfile

Dockerfile multi-stage yapidadir:

| Stage | Gorev |
|---|---|
| `base` | Python, sistem bagimliliklari, requirements kurulumu |
| `cli` | `python main.py` calistiran CLI image |
| `api` | Uvicorn API image; worker da ayni target'i kullanir |

---

## 15. Konfigurasyon

Konfigurasyon `config/settings.py` icinde merkezi olarak okunur. Tum degiskenler `.env` dosyasindan yuklenir.

### 15.1 Ortam Bagimsizligi (Zero-Config)

**Ayni `.env` dosyasi tum ortamlarda calisir.** Hicbir degisken manuel olarak degistirilmez:

| Ortam | Veritabani | Redis | Nasil Calisir |
|---|---|---|---|
| **Lokal CLI** | SQLite (otomatik) | Gerekmez | `python main.py` |
| **Lokal Streamlit** | SQLite (otomatik) | Gerekmez | `streamlit run app.py` |
| **Lokal Testler** | SQLite (gecici) | Gerekmez | `pytest tests/` |
| **Docker** | PostgreSQL (otomatik) | Docker Redis (otomatik) | `docker compose up` |
| **Streamlit Cloud** | SQLite (otomatik) | Gerekmez | Otomatik deploy |

Docker Compose, her servis icin `DATABASE_URL` ve `REDIS_URL` degiskenlerini kendi `environment` blogundan **override** eder. Bu sayede `.env` her zaman lokal ayarlariyla kalir.

### 15.2 Degisken Tablosu

| Degisken | Varsayilan | Gorev |
|---|---|---|
| `DATABASE_URL` | Bos (`""`) | Bos ise SQLite kullanilir; Docker PostgreSQL URL'ini inject eder |
| `SQLITE_PATH` | `data/rules.db` | SQLite dosya yolu |
| `REDIS_URL` | `redis://localhost:6379/0` | Lokal Redis; Docker `redis://redis:6379/0` olarak override eder |
| `ADMIN_PASSWORD` | `admin123` | Streamlit admin parolasi |
| `DISCORD_WEBHOOK_URL` | Bos string | Genel webhook fallback |
| `CELERY_TASK_MAX_RETRIES` | `3` | Celery task retry sayisi |
| `CELERY_TASK_RETRY_BACKOFF` | `true` | Retry backoff ayari |
| `AI_PROVIDER` | `none` | `gemini` / `huggingface` / `transformers` / `ollama` / `none` |
| `GEMINI_API_KEY` | Bos | Google Gemini API anahtari |
| `GEMINI_MODEL` | `gemini-2.5-flash-lite` | Kullanilacak Gemini modeli |
| `HF_API_TOKEN` | Bos | HuggingFace API token'i |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model adi |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama sunucu adresi |
| `AI_CONFIDENCE_THRESHOLD` | `0.65` | AI guven esigi — alti RegEx'e duser |

`.env.example` dosyasi her kurulum icin sablon saglar.

Guvenlik notu: Gercek secret degerleri `.env` icinde tutulmali ve git'e commit edilmemelidir.

---

## 16. Test Stratejisi

Testler `tests/` klasorundedir.

### 16.1 Unit Testler

`tests/test_evaluator.py`, `TicketEvaluator` davranisini 27 test ile kapsar.

### 16.2 E2E Testler

`tests/test_e2e.py`, tam pipeline'i 15 test ile kapsar (gecici SQLite DB kullanir).

### 16.3 AI Testleri

`tests/test_ai_classifier.py`, yapay zeka katmanini **30 test** ile kapsar:

| Test Sinifi | Kapsam |
|---|---|
| `TestHybridClassifierAIPath` | AI yolu: kategori, priority, reason, team routing |
| `TestHybridClassifierFallback` | Low confidence, API hatasi, unavailable, None provider |
| `TestHybridClassifierThreshold` | Tam esik, altinda, 0.0 ve 1.0 uc degerler |
| `TestProcessedTicketFields` | confidence ve aiUsed alanlari |
| `TestBaseAIProviderContract` | ABC enforce + mock interface |
| `TestOllamaProvider` | JSON parsing, validation, integration |
| `TestTransformersProvider` | Label mapping, priority, integration |

Tum AI testleri **mock** kullanir — gercek API cagrisi yapilmaz, tamamen offline calisir.

### 16.4 Test Calistirma

```bash
pytest tests/ -v
```

Beklenen sonuc:

```text
72 passed
```

---

## 17. Loglama ve Hata Yonetimi

### 17.1 CLI Loglama

`main.py`, Python `logging` modulunu kullanir ve iki handler tanimlar:

- `app.log`
- Console output

Log formati:

```text
timestamp - level - message
```

### 17.2 Dosya Okuma/Yazma Hatalari

`main()` su durumlarda hata loglar ve kontrollu sekilde cikar:

- Input dosyasi yoksa
- JSON okunamazsa
- Output yazilamazsa

### 17.3 Hatali Ticket Kayitlari

Batch icinde hatali bir ticket varsa butun islem durdurulmaz. Ilgili kayit `WARNING` ile atlanir, gecerli ticket'lar islenmeye devam eder.

### 17.4 Worker Hatalari

Webhook gonderimi veya history persistence basarisiz olursa:

- Hata loglanir.
- Celery task sonucu yine de doner.
- Ana siniflandirma is akisi fail edilmez.

---

## 18. Guvenlik Degerlendirmesi

### Mevcut Onlemler

| Alan | Onlem |
|---|---|
| API abuse | SlowAPI rate limiting |
| Input validation | Pydantic request model |
| SQL injection | Parametreli query kullanimi |
| Secret yonetimi | `.env` ve `config/settings.py` |
| Admin panel | Parola korumasi |
| Webhook hata izolasyonu | Bildirim hatasi ana akisi bozmaz |

### Dikkat Edilmesi Gerekenler

- `ADMIN_PASSWORD` varsayilan degeri production'da mutlaka degistirilmelidir.
- Streamlit admin panel tek parola ile korunur; cok kullanicili yetkilendirme yoktur.
- Webhook URL'leri secret kabul edilmeli ve commit edilmemelidir.
- API'de auth yoktur; public production senaryosunda API key, OAuth2 veya JWT eklenmelidir.
- Rate limit memory-backed varsayilanlarla calisabilir; cok instance'li production'da paylasimli backend dusunulmelidir.

---

## 19. Tasarim Kararlari ve Varsayimlar

### 19.1 Kural Tabanli Motor

Proje NLP modeli yerine deterministik regex ve keyword kurallari kullanir. Bu tercih:

- Test etmeyi kolaylastirir.
- Sonuclari aciklanabilir yapar.
- Admin panel ile davranisin kodsuz degistirilmesini saglar.
- Kucuk ve orta olcekli destek taleplerinde hizli sonuc verir.

### 19.2 Veritabani Kurallari

Kategori ve oncelik kurallari kod icine gomulmek yerine DB'de tutulur. Bu sayede admin panel degisiklikleri runtime davranisa etki eder.

### 19.3 Arayuzden Bagimsiz Cekirdek

`TicketEvaluator` ve `TeamRouter` herhangi bir framework'e bagimli degildir. Bu sayede ayni mantik:

- CLI'da
- Streamlit'te
- Celery worker'da

tekrar kullanilir.

### 19.4 Bilinen Sinirlar

| Sinir | Aciklama |
|---|---|
| Negation anlamaz | "I do not want a refund" yine `refund` sinyali tasiyabilir |
| Semantik benzerlik yok | Keyword listesinde olmayan es anlamli kelimeler yakalanmaz |
| Dil destegi sinirli | Varsayilan kurallar Ingilizce keyword'lere gore tasarlanmistir |
| Kategori onceligi siraya bagli | Coklu kategori sinyali varsa ilk eslesen kazanir |
| Worker kural cache'i | Admin panel degisikligi calisan worker cache'ine aninda yansimayabilir |

---

## 20. Gelistirme ve Yayina Alma Notlari

> **Not:** Tum ortamlar ayni `.env` dosyasiyla calisir. Hicbir degisken ortama gore manuel degistirilmez.

### 20.1 Lokal CLI (AI destekli)

```bash
pip install -r requirements.txt
python main.py
```

- Veritabani: SQLite (otomatik olusturulur)
- AI: `.env`'deki `AI_PROVIDER` ayarina gore
- Cikti: `data/processed_tickets.json`

### 20.2 Lokal Streamlit UI

```bash
streamlit run app.py
```

- Veritabani: SQLite
- AI badge ve confidence bar gorunur
- Admin panel: sol sidebar > Admin Panel > `admin123`

### 20.3 Lokal Testler

```bash
pytest tests/ -v
# Beklenen: 72 passed
```

- Veritabani: Gecici SQLite (temp dizin, otomatik temizlenir)
- AI testleri: Mock kullanir, API cagrisi yapilmaz

### 20.4 Lokal API + Worker (Redis gerekli)

```bash
uvicorn api:app --reload
celery -A worker.celery_app worker --loglevel=info
```

- Redis lokal kurulu olmalidir
- `.env`'deki `REDIS_URL=redis://localhost:6379/0` kullanilir

### 20.5 Docker (Tam Stack)

```bash
docker compose up --build
```

- PostgreSQL, Redis, FastAPI, Celery Worker ve CLI otomatik baslar
- `DATABASE_URL` ve `REDIS_URL` Docker tarafindan otomatik override edilir
- `.env` dosyasinda hicbir degisiklik gerekmez

API dokumani: `http://localhost:8000/docs`
Healthcheck: `http://localhost:8000/health`

### 20.6 Streamlit Cloud Deploy

- `app.py`'yi Streamlit Cloud'a bagla
- Secrets bolumune sadece AI anahtarini ekle:
  ```
  GEMINI_API_KEY = "your_key_here"
  AI_PROVIDER = "gemini"
  ```
- Veritabani otomatik SQLite olarak calisir

### 20.7 Ornek API Cagrisi

```bash
curl -X POST http://localhost:8000/api/v1/process-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1001,
    "subject": "Urgent refund request",
    "message": "My payment was charged twice and this looks like fraud.",
    "customerType": "premium",
    "createdAt": "2026-05-05T10:00:00Z"
  }'
```

Sonra task sonucu:

```bash
curl http://localhost:8000/api/v1/task/<task_id>
```

---

## 21. Gelecek Gelistirme Onerileri

| Alan | Oneri |
|---|---|
| Fine-tuned model | Zero-shot yerine domain'e ozel egitilmis model |
| Streaming API | FastAPI SSE/WebSocket ile gercek zamanli siniflandirma |
| Auth | API key, OAuth2 veya JWT tabanli kimlik dogrulama |
| Admin | Role-based access control |
| Rule versioning | Kural degisiklik gecmisi ve rollback |
| Worker refresh | Admin kural degisikliginde worker cache invalidation |
| Observability | Prometheus metrics, structured JSON logs, tracing |
| API history | `GET /api/v1/tickets/recent` gibi history endpoint'i |
| Validation | `customerType` icin enum, `createdAt` icin datetime validasyonu |
| Deployment | CI/CD pipeline, image tagging, environment-specific config |
| Webhook | Takim bazli webhook URL'lerini DB'de yonetme |

---

## Kisa Sonuc

Support Ticket Router, kucuk bir rule engine olarak baslayip production benzeri bir mikroservis yapisina genisletilmis ve son olarak **Hibrit AI motoruyla** zenginlestirilmis bir projedir.

En guclu yani, is mantiginin framework'lerden bagimsiz tutulmasi ve farkli arayuzlerin ayni `HybridClassifier` zincirini kullanmasidir:

- `python main.py` → CLI, AI kullanir
- `streamlit run app.py` → UI, AI badge + confidence bar gosterir
- `POST /api/v1/process-ticket` → REST API, Celery worker uzerinden AI kullanir

AI provider tek bir `.env` degiskeniyle (`AI_PROVIDER`) degistirilebilir; provider hata verirse veya guven esiginin altinda kalirsa sistem sessizce RegEx motoruna duser — cagiran taraf hic etkilenmez.
