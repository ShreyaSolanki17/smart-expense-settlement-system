# Smart Expense Settlement System

A Django + DRF expense-splitting app (Splitwise-style) that simplifies group
debts with a min-cash-flow algorithm to minimize the number of settlement
transactions.

## Stack
Django, Django REST Framework, PostgreSQL, Redis, Celery, pytest.

## Local development

Runs on sqlite, no Postgres/Redis required (Celery notifications will no-op
without a broker):

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Testing

```bash
pytest
```

## Docker

Full stack (Postgres, Redis, web, Celery worker):

```bash
cp .env.example .env
docker compose up --build
```

## Project status

Built incrementally; see commit history for progress on models, the debt
simplification algorithm, API, caching, async tasks, auth, and tests.
