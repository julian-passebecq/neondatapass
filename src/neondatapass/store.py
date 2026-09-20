from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool


class NeonStore:
    """Async persistence adapter for the Datapass control plane.

    Use Neon's pooled DATABASE_URL for normal application traffic.
    Schema migrations should use DATABASE_URL_UNPOOLED instead.
    """

    def __init__(
        self,
        database_url: str | None = None,
        *,
        min_size: int = 0,
        max_size: int = 4,
    ) -> None:
        self.database_url = database_url or os.environ["DATABASE_URL"]
        self.pool = AsyncConnectionPool(
            conninfo=self.database_url,
            min_size=min_size,
            max_size=max_size,
            open=False,
            kwargs={"row_factory": dict_row},
        )

    async def open(self) -> None:
        await self.pool.open()

    async def close(self) -> None:
        await self.pool.close()

    async def create_workspace(
        self,
        *,
        owner_subject: str,
        name: str,
        slug: str,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                INSERT INTO datapass.workspaces
                    (owner_subject, name, slug, description, settings)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (owner_subject, name, slug, description, Jsonb(settings or {})),
            )
            row = await cur.fetchone()
            assert row is not None
            return row

    async def list_workspaces(self, owner_subject: str) -> list[dict[str, Any]]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT *
                FROM datapass.workspaces
                WHERE owner_subject = %s
                ORDER BY updated_at DESC
                """,
                (owner_subject,),
            )
            return list(await cur.fetchall())

    async def save_notebook(
        self,
        *,
        notebook_id: UUID,
        document: dict[str, Any],
        expected_revision: int,
    ) -> dict[str, Any] | None:
        """Optimistic-concurrency update; returns None on revision conflict."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                UPDATE datapass.notebooks
                SET document = %s,
                    revision = revision + 1
                WHERE id = %s
                  AND revision = %s
                RETURNING *
                """,
                (Jsonb(document), notebook_id, expected_revision),
            )
            return await cur.fetchone()

    async def record_run_summary(
        self,
        *,
        workspace_id: UUID,
        engine: str,
        status: str,
        notebook_id: UUID | None = None,
        cell_id: str | None = None,
        duration_ms: int | None = None,
        row_count: int | None = None,
        output_preview: Any = None,
        metrics: dict[str, Any] | None = None,
        error_summary: str | None = None,
        artifact_uri: str | None = None,
    ) -> dict[str, Any]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                """
                INSERT INTO datapass.runs
                    (workspace_id, notebook_id, cell_id, engine, status,
                     finished_at, duration_ms, row_count, output_preview,
                     metrics, error_summary, artifact_uri)
                VALUES
                    (%s, %s, %s, %s, %s,
                     CASE WHEN %s IN ('succeeded','failed','cancelled') THEN now() ELSE NULL END,
                     %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    workspace_id,
                    notebook_id,
                    cell_id,
                    engine,
                    status,
                    status,
                    duration_ms,
                    row_count,
                    Jsonb(output_preview) if output_preview is not None else None,
                    Jsonb(metrics or {}),
                    error_summary,
                    artifact_uri,
                ),
            )
            row = await cur.fetchone()
            assert row is not None
            return row
