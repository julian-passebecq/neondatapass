# Datapass + Neon architecture

## Role of Neon

Neon/Lakebase Postgres is the durable control plane for Datapass Workbench.

Store in Neon:
- workspace identity and preferences
- notebook/workbench document state
- catalog metadata and logical dataset locators
- run summaries and compact output previews
- learning/interview progress
- artifact metadata and references
- authentication metadata

Do not store in Postgres:
- Parquet/CSV payloads
- DuckLake data files
- full Spark-like result sets
- large logs
- notebook binary attachments
- model artifacts

Those stay in DuckDB/DuckLake/MotherDuck or object storage. Neon stores only the locator and metadata.

## Runtime split

React + Fluent UI 2
  -> FastAPI runtime
      -> Neon: control-plane state
      -> DuckDB/DuckLake: local analytical execution and learning datasets
      -> MotherDuck: optional shared analytical backend
      -> SparkLab: simulated Spark execution
      -> Object storage: optional large artifacts

## Free-tier discipline

The current Neon Free plan is appropriate for Datapass metadata:
- 0.5 GB Postgres storage per project
- 100 CU-hours/project/month
- 10 branches/project
- 5 GB public egress/project/month
- compute scales to zero after 5 minutes
- 5 GB Object Storage included

Design rules:
1. Persist previews, not full result sets.
2. Keep JSON documents compact.
3. Prefer references/URIs over blobs.
4. Use one production branch plus short-lived dev/preview branches.
5. Do not poll Neon continuously from the UI.
6. Batch run telemetry writes.
7. Avoid storing duplicate notebook snapshots on every keystroke; debounce and revision only on meaningful changes.

## Branch workflow

- production: canonical application state
- dev-datapass-control-plane-v1: current schema-validation branch
- future feature branches: short-lived child branches for migrations/tests

Schema changes should be tested on a Neon child branch before promotion.
