from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import dict_row


class NeonStore:
    """Small async persistence adapter for the Datapass control plane."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["DATABASE_URL"]

    async def connect(self) -> AsyncConnection:
        return await AsyncConnection.connect(self.database_url, row_factory=dict_row)

    async def create_workspace(
        self,
        *,
        owner_subject: str,
        name: str,
        slug: str,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with await self.connect() as conn:
            row = await conn.execute(
                """
                INSERT INTO datapass.workspaces
                    (owner_subject, name, slug, description, settings)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                RETURNING *
                """,
                (owner_subject, name, slug, description, settings or {}),
            )
            return await row.fetchone()

    async def list_workspaces(self, owner_subject: str) -> list[dict[str, Any]]:
        async with await self.connect() as conn:
            cur = await conn.execute(
                """
                SELECT *
                FROM datapass.workspaces
                WHERE owner_subject = %s
                ORDER BY updated_at DESC
                """,
                (owner_subject,),
            )
            return await cur.fetchall()

    async def save_notebook(
        self,
        *,
        notebook_id: UUID,
        document: dict[str, Any],
        expected_revision: int,
    ) -> dict[str, Any] | None:
        """Optimistic-concurrency update; returns None on revision conflict."""
        async with await self.connect() as conn:
            cur = await conn.execute(
                """
                UPDATE datapass.notebooks
                SET document = %s::jsonb,
                    revision = revision + 1
                WHERE id = %s
                  AND revision = %s
                RETURNING *
                """,
                (document, notebook_id, expected_revision),
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
        async with await self.connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO datapass.runs
                    (workspace_id, notebook_id, cell_id, engine, status,
                     finished_at, duration_ms, row_count, output_preview,
                     metrics, error_summary, artifact_uri)
                VALUES
                    (%s, %s, %s, %s, %s,
                     CASE WHEN %s IN ('succeeded','failed','cancelled') THEN now() ELSE NULL END,
                     %s, %s, %s::jsonb, %s::jsonb, %s, %s)
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
                    output_preview,
                    metrics or {},
                    error_summary,
                    artifact_uri,
                ),
            )
            return await cur.fetchone()
