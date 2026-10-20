# Django Pub AI Edition

Інтерактивний AI асистент заходу Django.Pub @ ЛНТУ. Шукає відповіді в програмі виступів і технічному довіднику (PostgreSQL + pgvector), будує відповідь графом LangGraph і стрімить токени в чат через Django Channels.

## Швидкий старт

**Потрібні:** Docker і Docker Compose.

### 1. Створити `.env`

```bash
cp env/.env.example env/.env
```

### 2. Додати ключ OpenAI

Відкрийте `env/.env` і вставте ключ:

```dotenv
OPENAI_API_KEY=sk-...
```

### 3. Запустити

```bash
docker compose up --build
```

Перший запуск застосовує міграції, збирає статику і будує векторний індекс. Повторний запуск індексацію пропускає.

Відкрийте → http://localhost:8000

---

## Змінні оточення

| Змінна | Опис |
|---|---|
| `OPENAI_API_KEY` | Ключ OpenAI (обов'язково) |
| `OPENAI_CHAT_MODEL` | Модель чату (за замовчуванням `gpt-4o-mini`) |
| `OPENAI_EMBEDDING_MODEL` | Модель ембедингів (за замовчуванням `text-embedding-3-small`) |
| `DJANGO_SECRET_KEY` | Секретний ключ Django |
| `DJANGO_DEBUG` | `0` — production, `1` — debug |
| `DJANGO_ALLOWED_HOSTS` | Дозволені хости через кому |
| `POSTGRES_*` | Параметри підключення до бази |
| `REDIS_URL` | URL Redis |
| `RAG_TOP_K` | Кількість фрагментів для RAG-контексту |
| `RAG_MAX_DISTANCE` | Максимальна косинусна відстань (pgvector) |

---

## Оновити матеріали заходу

```bash
docker compose run --rm web python manage.py seed_event
```

Команда дописує нові фрагменти і видаляє застарілі.

---

## Структура

```
config/      — налаштування, ASGI, маршрути
conference/  — спікери, сесії, фрагменти знань, журнал чату
assistant/   — граф LangGraph, інструменти, WebSocket, сторінка чату
fixtures/    — матеріали заходу і технічний довідник (YAML)
env/         — файли оточення
docker/      — entrypoint
```
