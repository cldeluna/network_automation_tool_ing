# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

A queryable registry of network automation tools — their capabilities, integrations, dependencies, and environment compatibility. Serves human operators, CI/CD pipelines, and AI/MCP agents. Example queries: *"Which tools support gNMI on Alpine Linux?"*, *"What's the install command for SuzieQ on Ubuntu 22.04?"*

## Commands

```bash
# Run the application
uv run python main.py

# Install dependencies
uv sync

# Add a dependency
uv add <package>
```

Python 3.11 is required (see `.python-version`).

## Architecture

This is a **spec-driven** project. `automation_tools_schema_spec.md` is the authoritative source of truth — all schema, API contracts, and business rules are derived from it, not the reverse. Do not add schema or API behavior not traceable to the spec.

### Database Schema

Primary target: PostgreSQL. SQLite supported for local dev; DuckDB for analytics. Key portability differences (UUID generation, array types, enum types, GIN indexes) are documented in spec §8.6.

Twelve tables with strict normalization (3NF, join tables — no JSONB blobs except where explicitly marked):

| Table | Role |
|-------|------|
| `tools` | Core registry — name, slug, type, status, URLs |
| `tool_categories` | Taxonomy labels (e.g., `configuration-management`) |
| `tool_category_map` | Many-to-many: tools ↔ categories |
| `tool_versions` | Point-in-time releases; only one `is_latest=TRUE` per tool (partial unique index + app-layer transaction) |
| `tool_capabilities` | Named capabilities with `protocol_support[]` (enum array) and `os_support[]` (text array) |
| `tool_integrations` | Directed integration edges between tools (self-referential, no self-loops) |
| `tool_dependencies` | Directed dependency edges (self-referential, no self-loops) |
| `environments` | Named compute environments (OS + platform) |
| `tool_environment_support` | Install method + command per tool/environment pair |
| `tool_naf_function_map` | Many-to-many: tools ↔ NAF framework functions (presentation/intent/observability/collector/orchestration/executor) |
| `data_sources` | Catalog of discovery sources (Packet Pushers, Steinzi, manual) |
| `tool_source_map` | Many-to-many: tools ↔ data sources (provenance — required, cannot be empty) |
| `api_keys` | Hashed admin API keys for authenticating write operations; raw key stored once, never again |

All controlled vocabularies are database-level enum types: `tool_type`, `tool_status`, `integration_type`, `dependency_type`, `protocol_support`, `platform_type`, `install_method`, `naf_function`.

All mutable tables have `created_at` / `updated_at` with auto-update triggers.

### API

REST API at `/api/v1`. All responses use an envelope: `{ "data": ..., "meta": { "total", "page", "per_page", "pages" }, "errors": [] }`.

Primary resource is `/api/v1/tools` with sub-resources for versions, capabilities, integrations, dependencies, and environments. Supports filtering by status, type, category, protocol, and environment — including multi-value comma-separated filters.

### Key Business Rules (from spec §7)

- **Slug immutability**: Once published, slugs on `tools`, `tool_categories`, `environments`, and `data_sources` must not change. They are stable external identifiers.
- **Single latest version**: At most one `tool_versions` row per tool may have `is_latest = TRUE`. Enforce via partial unique index + single transaction (first clear existing, then set new).
- **No self-loops**: `tool_integrations` and `tool_dependencies` both CHECK `tool_id <> target_id`.
- **Status transitions**: `archived` is terminal. Permitted transitions: `active → deprecated|archived|experimental`, `experimental → active|archived`, `deprecated → archived`.
- **`version_string` is immutable**: Correct a bad version by delete + re-insert.
- **Source provenance required**: Every tool must have at least one `tool_source_map` entry. The `POST /api/v1/tools` endpoint must reject submissions with an empty `sources` array (app-layer validation).
- **Source deletion restricted**: Cannot delete a `data_sources` row while tools reference it (`ON DELETE RESTRICT`).
- **All writes require auth**: Every non-GET endpoint requires `Authorization: Bearer <key>`. Keys are hashed (SHA-256) in `api_keys`; raw key returned once at creation. Bootstrap via `uv run python main.py create-admin-key`. See spec §5.6.

### Design Principles

From spec §1.4 — apply these when extending the system:
1. Prefer normalized schema with explicit join tables over JSONB blobs.
2. All controlled vocabularies go in DB-level enums (or CHECK constraints for SQLite).
3. Every entity gets a `slug` for URL routing and seed data authoring.
4. `os_support` in `tool_capabilities` intentionally uses `TEXT[]` (not an enum array) to allow forward-compatible values without migrations.

### Planned MCP Integration (spec §8.4)

Future MCP server tools: `search_tools`, `get_tool`, `get_install_command`, `list_integrations`, `find_tools_by_protocol`, `get_dependency_graph`. Transport: STDIO (local) or HTTP+SSE (remote).
