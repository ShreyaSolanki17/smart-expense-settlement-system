# Smart Expense Settlement System

A Django + DRF expense-splitting app (Splitwise-style) that simplifies group
debts with a min-cash-flow algorithm to minimize the number of settlement
transactions.

## Stack
Django, Django REST Framework, PostgreSQL, Redis, Celery, pytest.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Docker

```bash
docker compose up --build
```

## Project status

Built incrementally; see commit history for progress on models, the debt
simplification algorithm, API, caching, async tasks, auth, and tests.
