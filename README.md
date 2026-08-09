# Smart Expense Settlement System

A Django + DRF expense-splitting app (Splitwise-style) that simplifies group
debts with a min-cash-flow algorithm to minimize the number of settlement
transactions.

## Stack
Django, Django REST Framework, GraphQL (graphene-django), PostgreSQL, Redis, Celery, pytest.

## Setup

`.env` holds secrets only (`DEBUG`, `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`) —
the same file works for both paths below, since Postgres/Redis URLs are set
directly in `docker-compose.yml` rather than `.env`.

```bash
cp .env.example .env
```

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

## API docs

Swagger UI at `/api/docs/`, Redoc at `/api/redoc/`, raw OpenAPI schema at `/api/schema/`.

## GraphQL API

Alongside REST, `/graphql/` exposes the same domain through GraphQL (GraphiQL
browser enabled in dev) — added to demonstrate schema design on top of an
existing DRF app, reusing its serializers for mutation validation rather than
duplicating the rules. Same token auth as REST: `Authorization: Token <key>`.

The frontend's group-detail screen uses it end-to-end: one query replaces
what used to be two REST round trips (expenses + balances), and
create-expense/create-settlement are GraphQL mutations.

```graphql
query {
  groups { id name }
}

mutation {
  createExpense(group: 1, description: "lunch", amount: "12.00", paidBy: 3) {
    expense { id }
  }
}
```

## Testing

```bash
pytest
```

## Docker

Full stack (Postgres, Redis, web, Celery worker):

```bash
docker compose up --build
```

## Project status

Built incrementally; see commit history for progress on models, the debt
simplification algorithm, API, caching, async tasks, auth, and tests.
