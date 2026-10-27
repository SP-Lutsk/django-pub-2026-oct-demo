# Django Pub AI Edition

AI-асистент заходу Django.Pub @ ЛНТУ. Відповідає на питання про виступи Ореста Новосада, Олександра Шипуліна і Влада Гетманенка та допомагає глибше розібратися в їхніх темах. Питання не про захід відхиляє.

Демо стеку з блоку 3:

- **RAG на pgvector** — фрагменти знань і їхні ембединги лежать у звичайному PostgreSQL, пошук робить Django ORM;
- **LangGraph** — граф `retrieve → agent ⇄ tools` з інструментом, що читає програму через ORM;
- **Django Channels** — відповідь стрімиться токенами через WebSocket, генерацію можна зупинити.

## Швидкий старт

**Потрібні:** Docker з Docker Compose і `make`.

```bash
git clone <посилання на репозиторій>
cd django-pub-2026-oct-demo
make env
```

Відкрийте `env/.env` і вставте ключ OpenAI (тимчасовий ключ дають організатори):

```dotenv
OPENAI_API_KEY=sk-...
```

```bash
make up
```

Відкрийте http://localhost:8000.

Під час першого старту застосовуються міграції і розгортається база знань з дампу `fixtures/knowledge.json.gz`: спікери, програма і фрагменти з уже порахованими ембедингами. Індексувати нічого не треба.

Без `make`: `cp env/.env.example env/.env`, потім `docker compose up --build`.

## Що спитати

- «Хто спікери і в якому порядку виступають?»
- «Що розповідав Олександр про ONNX?»
- «Покажи програму третього блоку» — агент викличе інструмент `list_sessions`
- «Як винести інференс PyTorch у Celery? Приклад коду»
- «Яка погода в Луцьку?» — асистент відмовить, це поза темою
- довге питання і кнопка «Зупинити» — генерація обірветься на бекенді

## Як це працює

```
браузер ──WebSocket──▶ ChatConsumer ──▶ LangGraph
                                         ├─ retrieve: ембединг питання → pgvector (CosineDistance)
                                         ├─ agent:    системний промпт + контекст → LLM
                                         └─ tools:    list_sessions → Django ORM
           ◀── токени ───────────────────┘
```

| Файл | Що всередині |
|---|---|
| [conference/models.py](conference/models.py) | `KnowledgeChunk` з `VectorField(dimensions=1536)` і HNSW-індексом |
| [assistant/retrieval.py](assistant/retrieval.py) | ембединг питання і пошук найближчих фрагментів через `CosineDistance` з порогом релевантності |
| [assistant/graph.py](assistant/graph.py) | `StateGraph`: вузли `retrieve`, `agent`, `tools` і умовні переходи |
| [assistant/tools.py](assistant/tools.py) | інструмент `list_sessions` — модель не ходить у базу сама, запит робить Python-код |
| [assistant/prompts.py](assistant/prompts.py) | системний промпт: межі тем, атрибуція спікерам, відмова поза темою |
| [assistant/consumers.py](assistant/consumers.py) | WebSocket-consumer: валідація, rate limit, стрімінг токенів, зупинка через `task.cancel()` |
| [conference/chunking.py](conference/chunking.py), [conference/indexing.py](conference/indexing.py) | нарізка тексту на фрагменти з перекриттям і префікс сесії |
| [assistant/static/js/chat.js](assistant/static/js/chat.js) | фронтенд на Alpine.js: сокет, markdown, підсвітка коду |

## Команди

| Команда | Що робить |
|---|---|
| `make up` | зібрати і запустити стек |
| `make down` | зупинити стек |
| `make logs` | логи застосунку (видно, які фрагменти знайшов пошук) |
| `make test` | офлайн-тести в контейнері, ключ OpenAI не потрібен |
| `make reload` | замінити базу знань вмістом дампу (після `git pull` з новим дампом) |
| `make shell` | Django shell у контейнері |

## Змінні оточення

| Змінна | Опис |
|---|---|
| `OPENAI_API_KEY` | ключ OpenAI (обов'язково для чату) |
| `OPENAI_CHAT_MODEL` | модель чату, за замовчуванням `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | модель ембедингів `text-embedding-3-small`; дамп порахований саме нею, тому не змінюйте |
| `RAG_TOP_K` | скільки фрагментів брати в контекст |
| `RAG_MAX_DISTANCE` | максимальна косинусна відстань, далі фрагмент вважається нерелевантним |
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | налаштування Django |
| `POSTGRES_*`, `REDIS_URL` | підключення до бази і Redis |

## Для організаторів: оновити базу знань

Вихідні матеріали не входять у репозиторій. Вони лежать локально в `documents/` (є в `.gitignore` і `.dockerignore`):

- `documents/event_materials.yaml` — спікери і нотатки виступів;
- `documents/tech_knowledge.yaml` — технічний довідник для поглиблених питань.

```bash
make knowledge
```

Команда рахує ембединги лише для змінених фрагментів, прибирає застарілі сесії та спікерів і перезаписує `fixtures/knowledge.json.gz`. Закомітьте новий дамп — учасники отримають його через `git pull` і `make reload`.

## Структура

```
config/      — налаштування, ASGI-маршрутизація
conference/  — моделі бази знань, нарізка, команди seed_event / load_knowledge / dump_knowledge
assistant/   — граф LangGraph, пошук, інструменти, WebSocket-consumer, сторінка чату
fixtures/    — дамп бази знань (knowledge.json.gz)
tests/       — офлайн-тести
docker/      — entrypoint контейнера
env/         — приклад файлу оточення
```
