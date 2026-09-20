"""Supabase-backed document persistence for SAHAYA state.

The domain models stay in Python; Supabase stores JSONB snapshots keyed by
their stable IDs. This keeps Pydantic migrations safe while ensuring a Render
restart does not discard operational records.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseStateStore:
    TABLES = (
        "incidents",
        "resources",
        "people",
        "evaluation_batches",
        "group_evaluation_batches",
        "route_observations",
        "route_evaluations",
        "audit_logs",
    )

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "").strip()
        # Supabase now issues server-only keys as sb_secret_... values. Keep
        # the legacy variable as a fallback for existing deployments.
        key = (
            os.getenv("SUPABASE_SECRET_KEY", "").strip()
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        )
        if not url or not key or "your_" in url or "your_" in key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SECRET_KEY are required for "
                "STORE_BACKEND=supabase."
            )
        self.client: Client = create_client(url, key)

    def load_all(self, table: str) -> dict[str, dict[str, Any]]:
        rows = self.client.table(table).select("id,data").execute().data or []
        return {row["id"]: row["data"] for row in rows}

    def upsert(self, table: str, key: str, data: Any) -> None:
        self.client.table(table).upsert(
            {
                "id": key,
                "data": data,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="id",
        ).execute()

    def delete(self, table: str, key: str) -> None:
        self.client.table(table).delete().eq("id", key).execute()


def configured_store() -> SupabaseStateStore | None:
    """Return a configured store only when explicitly enabled."""
    if os.getenv("STORE_BACKEND", "memory").lower() != "supabase":
        return None
    store = SupabaseStateStore()
    logger.info("SAHAYA persistence: Supabase enabled.")
    return store
