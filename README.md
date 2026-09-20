# Neon Datapass

Neon/Lakebase Postgres control-plane foundation for **Datapass Workbench**.

This repository deliberately does **not** turn Postgres into the analytical engine. Datapass keeps DuckDB/DuckLake/MotherDuck and SparkLab responsible for data-engineering workloads; Neon stores durable application state and metadata.

## What belongs in Neon

- workspaces and user-owned settings
- notebook/workbench document state
- dataset catalog metadata and locators
- compact execution/run summaries
- interview and learning progress
- artifact references/checksums
- authentication metadata

Large datasets, Parquet/CSV payloads, full result sets, and model artifacts stay outside Postgres.

## Current validated Neon environment

The initial schema was validated on an isolated Neon child branch:

- project: `super-pine-64819564`
- production branch: `production`
- validation branch: `dev-datapass-control-plane-v1`
- database: `neondb`
- Postgres: 18
- region: `aws-us-east-2`

Production has not been migrated.

## Repository layout

- `migrations/0001_control_plane.sql` — initial schema
- `src/neondatapass/store.py` — async Psycopg pool adapter for FastAPI
- `docs/ARCHITECTURE.md` — Datapass/Neon responsibility split
- `.env.example` — pooled runtime vs direct migration URL contract

## FastAPI lifecycle

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from neondatapass import NeonStore

store = NeonStore()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.open()
    app.state.neon = store
    yield
    await store.close()

app = FastAPI(lifespan=lifespan)
```

Use Neon's pooled `DATABASE_URL` for application traffic. Use `DATABASE_URL_UNPOOLED` for migrations.

## Status

V1 schema is validated on the Neon development branch. Promotion to production is intentionally a separate operation.
