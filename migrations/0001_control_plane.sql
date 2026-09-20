CREATE SCHEMA IF NOT EXISTS datapass;

CREATE TABLE IF NOT EXISTS datapass.workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_subject text NOT NULL,
  name text NOT NULL,
  slug text NOT NULL,
  description text,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (owner_subject, slug)
);

CREATE TABLE IF NOT EXISTS datapass.notebooks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES datapass.workspaces(id) ON DELETE CASCADE,
  title text NOT NULL,
  kind text NOT NULL DEFAULT 'notebook',
  document jsonb NOT NULL DEFAULT '{"cells":[]}'::jsonb,
  revision bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (kind IN ('notebook','sql_arena','pipeline','diagram','lesson'))
);

CREATE INDEX IF NOT EXISTS notebooks_workspace_updated_idx
  ON datapass.notebooks (workspace_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS datapass.catalog_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES datapass.workspaces(id) ON DELETE CASCADE,
  logical_name text NOT NULL,
  asset_kind text NOT NULL,
  engine text NOT NULL,
  locator text NOT NULL,
  schema_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  stats jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, logical_name),
  CHECK (asset_kind IN ('table','view','file','ducklake_table','motherduck_table','external')),
  CHECK (engine IN ('duckdb','ducklake','motherduck','spark_sim','postgres','external'))
);

CREATE TABLE IF NOT EXISTS datapass.runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES datapass.workspaces(id) ON DELETE CASCADE,
  notebook_id uuid REFERENCES datapass.notebooks(id) ON DELETE SET NULL,
  cell_id text,
  engine text NOT NULL,
  status text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  duration_ms integer,
  row_count bigint,
  output_preview jsonb,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_summary text,
  artifact_uri text,
  CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
  CHECK (engine IN ('python','sql','duckdb','ducklake','motherduck','spark_sim','polars','postgres'))
);

CREATE INDEX IF NOT EXISTS runs_workspace_started_idx
  ON datapass.runs (workspace_id, started_at DESC);

CREATE INDEX IF NOT EXISTS runs_notebook_started_idx
  ON datapass.runs (notebook_id, started_at DESC)
  WHERE notebook_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS datapass.learning_progress (
  workspace_id uuid NOT NULL REFERENCES datapass.workspaces(id) ON DELETE CASCADE,
  subject text NOT NULL,
  item_key text NOT NULL,
  state text NOT NULL DEFAULT 'new',
  score numeric(6,3),
  attempts integer NOT NULL DEFAULT 0,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, subject, item_key),
  CHECK (state IN ('new','in_progress','review','mastered'))
);

CREATE TABLE IF NOT EXISTS datapass.artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES datapass.workspaces(id) ON DELETE CASCADE,
  run_id uuid REFERENCES datapass.runs(id) ON DELETE SET NULL,
  kind text NOT NULL,
  uri text NOT NULL,
  content_type text,
  size_bytes bigint,
  sha256 text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (kind IN ('dataset','chart','export','checkpoint','attachment','log'))
);

CREATE INDEX IF NOT EXISTS artifacts_workspace_created_idx
  ON datapass.artifacts (workspace_id, created_at DESC);

CREATE OR REPLACE FUNCTION datapass.touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS workspaces_touch_updated_at ON datapass.workspaces;
CREATE TRIGGER workspaces_touch_updated_at
BEFORE UPDATE ON datapass.workspaces
FOR EACH ROW EXECUTE FUNCTION datapass.touch_updated_at();

DROP TRIGGER IF EXISTS notebooks_touch_updated_at ON datapass.notebooks;
CREATE TRIGGER notebooks_touch_updated_at
BEFORE UPDATE ON datapass.notebooks
FOR EACH ROW EXECUTE FUNCTION datapass.touch_updated_at();

DROP TRIGGER IF EXISTS catalog_assets_touch_updated_at ON datapass.catalog_assets;
CREATE TRIGGER catalog_assets_touch_updated_at
BEFORE UPDATE ON datapass.catalog_assets
FOR EACH ROW EXECUTE FUNCTION datapass.touch_updated_at();
