# Implementation Guide: Network Automation Registry on Supabase

---

## Part 1 — Supabase Account & Project

### Step 1 — Create a Supabase account

Go to [supabase.com](https://supabase.com) and click **Start your project**. Sign up with GitHub (easiest) or email. No credit card required for the free tier.

### Step 2 — Create a new project

1. From your dashboard, click **New project**
2. Fill in:
   - **Name:** `network-automation-registry` (or anything you like)
   - **Database password:** Generate a strong password — **save this somewhere safe, you'll need it**
   - **Region:** Pick the one closest to you
3. Click **Create new project**
4. Wait about 2 minutes while it provisions

https://supabase.com/dashboard/project/pyerkodxqgooqiaelvyt

Network Automation Tool.ing Personal Access Token
sbp_9d3a••••••••••••••••••••••••••••••••0fc5

> **Free tier note:** Projects pause automatically after 1 week of inactivity. You can unpause from the dashboard. Upgrade to Pro if you need it always-on.

### Step 3 — Get your connection string

1. In your project, click the **Settings** gear icon in the left sidebar
2. Click **Database**
3. Scroll down to **Connection string**
4. Select the **URI** tab
5. Copy the string — it looks like:
   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
6. Replace `[YOUR-PASSWORD]` with the database password you set in Step 2

> **Note:** Supabase shows two connection strings — "Transaction" (port 6543) and "Session" (port 5432). Use **Transaction** (port 6543) — it works with IPv4 on all networks.

---

## Part 2 — Local Project Setup

### Step 4 — Create your `.env` file

In the project root, create a file named `.env`:

```
# Supabase PostgreSQL connection
DATABASE_URL=postgresql://postgres.[project-ref]:[your-password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Admin API key — fill in after Step 11
NART_ADMIN_KEY=
```

### Step 5 — Add `.env` to `.gitignore`

Create a `.gitignore` file in the project root:

```
.env
.DS_Store
__pycache__/
*.pyc
.python-version
```

### Step 6 — Install dependencies

```bash
uv add psycopg2-binary python-dotenv
```

- `psycopg2-binary` — PostgreSQL driver
- `python-dotenv` — loads your `.env` file

You will add `fastapi` and `uvicorn` later when building the REST API.

---

## Part 3 — Run the Schema in Supabase

Open your Supabase project and click **SQL Editor** in the left sidebar.

**DDL** (Data Definition Language) is the SQL that creates the database structure — enum types, tables, indexes, and triggers. Nothing is stored in the database until you run it.

Run the DDL from `automation_tools_schema_spec.md` in three passes. Each pass is a separate query tab in the Supabase SQL Editor — click **Run** after pasting each one.

### Step 7 — Run: Enum types (§3.1)

Open `automation_tools_schema_spec.md` and copy the entire SQL code block under `### 3.1 Enum Types`. Paste it into the SQL Editor and click **Run**.

Expected result: `Success. No rows returned.`

### Step 8 — Run: Tables (§3.2 through §3.13)

For each section below, copy its SQL code block from the spec and run it. Go in order — some tables have foreign keys that reference earlier ones.

| Section | Table |
|---------|-------|
| §3.2 | `tools` — also creates the `set_updated_at()` trigger function |
| §3.3 | `tool_categories` |
| §3.4 | `tool_category_map` |
| §3.5 | `tool_capabilities` |
| §3.6 | `tool_dependencies` |
| §3.7 | `environments` |
| §3.8 | `tool_environment_support` |
| §3.9 | `contacts` |
| §3.10 | `tool_contact_map` |
| §3.11 | `data_sources` |
| §3.12 | `tool_source_map` |
| §3.13 | `api_keys` |

Each should return `Success. No rows returned.`

### Step 9 — Run: Seed data (§6)

In `automation_tools_schema_spec.md`, find `## 6. Seed Data Examples` and copy the entire SQL block. Run it in the SQL Editor.

This inserts: 8 tools (with `naf_functions` and `business_model` inline), seed categories, seed environments, example capabilities, example dependencies, example contacts, data sources, and source provenance records.

---

## Part 4 — Bootstrap Admin Key

### Step 10 — Update `main.py`

Replace the contents of `main.py` with:

```python
import argparse
import hashlib
import os
import secrets

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def create_admin_key(name: str, expires_at: str | None = None):
    raw_key = "nart_" + secrets.token_urlsafe(32)
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_keys (name, key_prefix, key_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
                """,
                (name, key_prefix, key_hash, expires_at),
            )
            row = cur.fetchone()
            conn.commit()

        print("\nAdmin key created successfully!")
        print(f"  ID:         {row[0]}")
        print(f"  Name:       {name}")
        print(f"  Prefix:     {key_prefix}")
        print(f"  Created at: {row[1]}")
        print("\n  Raw key (save this — it will NOT be shown again):")
        print(f"  {raw_key}")
        print("\nAdd to your .env file:")
        print(f"  NART_ADMIN_KEY={raw_key}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Network Automation Registry Tool")
    subparsers = parser.add_subparsers(dest="command")

    key_parser = subparsers.add_parser("create-admin-key", help="Create an admin API key")
    key_parser.add_argument("--name", required=True, help="Label for this key")
    key_parser.add_argument("--expires-at", help="Expiry datetime in ISO 8601 (optional)")

    args = parser.parse_args()

    if args.command == "create-admin-key":
        create_admin_key(args.name, getattr(args, "expires_at", None))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

### Step 11 — Run the bootstrap command

```bash
uv run python main.py create-admin-key --name "local dev"
```

You will see output like:

```
Admin key created successfully!
  ID:         a1b2c3d4-...
  Name:       local dev
  Prefix:     nart_abc1defg
  Created at: 2026-05-31 ...

  Raw key (save this — it will NOT be shown again):
  nart_abc1defghij...

Add to your .env file:
  NART_ADMIN_KEY=nart_abc1defghij...
```

Copy the `NART_ADMIN_KEY=...` line into your `.env` file. **This is the only time you will see the raw key.**

---

## Part 5 — Verify

### Step 12 — Confirm the key is in the database

In the Supabase SQL Editor, run:

```sql
SELECT id, name, key_prefix, is_active, created_at FROM api_keys;
```

You should see one row with your key's name and prefix.

### Step 13 — Confirm the seed data loaded

```sql
SELECT slug, tool_type, status FROM tools ORDER BY name;
```

You should see 8 rows: Ansible, containerlab, Infrahub, Jinja2, Netmiko, Network Automation MCP Server, Nornir, SuzieQ.

---

## What's Next

You now have:
- A live PostgreSQL database on Supabase with the full schema
- An admin API key stored securely in `.env`
- The `create-admin-key` CLI command for minting additional keys
- A full REST API — see Part 7 below

---

## Part 7 — REST API

The REST API is implemented in `api.py` using FastAPI. All routes are under `/api/v1`.

### Step 17 — Start the server

```bash
uv run python main.py serve
```

The server starts on `http://127.0.0.1:8000`. Hot-reload is enabled by default.

### Step 18 — Explore the interactive docs

Open `http://127.0.0.1:8000/docs` in your browser. You'll see every endpoint, its request/response schema, and a **Try it out** button.

To authorize write requests in the docs UI: click **Authorize** at the top right and enter your `NART_ADMIN_KEY` as the Bearer token.

### Step 19 — Create a tool via the API

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/tools \
  -H "Authorization: Bearer <your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Batfish",
    "slug": "batfish",
    "tool_type": "platform",
    "description": "Network configuration analysis and verification",
    "repo_url": "https://github.com/batfish/batfish",
    "status": "active",
    "naf_functions": ["observability"],
    "business_model": "full-open-source",
    "sources": ["manual"]
  }'
```

Returns `201 Created` with the full tool object. The `sources` field is required and must contain at least one known source slug — the API rejects tools with no provenance.

### Step 20 — Update a tool's status

Status transitions are enforced by the API layer:

| From | Allowed transitions |
|------|---------------------|
| `active` | `deprecated`, `archived`, `experimental` |
| `experimental` | `active`, `archived` |
| `deprecated` | `archived` |
| `archived` | *(terminal — no transitions)* |

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/tools/batfish \
  -H "Authorization: Bearer <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"status": "deprecated"}'
```

Returns `409 Conflict` if the transition is invalid.

### Write endpoint summary

All non-`GET` endpoints require `Authorization: Bearer <key>`.

| Resource | Create | Update | Delete |
|----------|--------|--------|--------|
| Tools | `POST /api/v1/tools` | `PATCH /api/v1/tools/{slug}` | `DELETE /api/v1/tools/{slug}` |
| Capabilities | `POST /api/v1/tools/{slug}/capabilities` | — | `DELETE /api/v1/tools/{slug}/capabilities/{id}` |
| Dependencies | `POST /api/v1/tools/{slug}/dependencies` | — | `DELETE /api/v1/tools/{slug}/dependencies/{id}` |
| Env support | `POST /api/v1/tools/{slug}/environments` | — | `DELETE /api/v1/tools/{slug}/environments/{env_slug}` |
| References | `POST /api/v1/tools/{slug}/references` | — | `DELETE /api/v1/tools/{slug}/references/{contact_id}` |
| Categories | `POST /api/v1/categories` | — | `DELETE /api/v1/categories/{slug}` |
| Environments | `POST /api/v1/environments` | — | `DELETE /api/v1/environments/{slug}` |
| Contacts | `POST /api/v1/contacts` | `PATCH /api/v1/contacts/{id}` | `DELETE /api/v1/contacts/{id}` |
| Sources | `POST /api/v1/sources` | — | `DELETE /api/v1/sources/{slug}` |
| Admin keys | `POST /api/v1/admin/keys` | — | `DELETE /api/v1/admin/keys/{id}` (soft revoke) |

> **Slug immutability:** Slugs on tools, categories, environments, and data sources are stable external identifiers and cannot be changed after creation.

> **Source deletion:** `DELETE /api/v1/sources/{slug}` returns `409` if any tools still reference that source. Reassign or delete those tools first.

---

## Part 6 — Supabase MCP Server (Optional but Recommended)

The Supabase MCP server lets Claude interact with your database directly — running SQL, inspecting tables, applying schema changes — without leaving the conversation. This is useful for running the DDL and seed steps above, and for debugging queries later.

### Prerequisites

- Node.js installed (check: `node --version`)
- A Supabase **Personal Access Token**
- Your Supabase **Project ID**

### Step 14 — Get your Personal Access Token

1. Go to [supabase.com](https://supabase.com) and log in
2. Click your avatar (top right) → **Account**
3. Click **Access Tokens** in the left sidebar
4. Click **Generate new token**
5. Give it a name (e.g., `claude-code`) and click **Generate**
6. Copy the token — it starts with `sbp_`

You will paste this token directly into `.mcp.json` in Step 16. Do **not** add it to `.env` — `.mcp.json` is already in `.gitignore` and is the right place for it.

### Step 15 — Get your Project ID

Your project ID is visible in the URL when you are in your Supabase project dashboard:

```
https://supabase.com/dashboard/project/[YOUR-PROJECT-ID]
```

Copy the `[YOUR-PROJECT-ID]` portion (it looks like `abcdefghijklmnop`).

### Step 16 — Configure the MCP server in Claude Code

MCP servers are configured in a `.mcp.json` file at the project root (not in `.claude/settings.json`). A template has already been created in this project. Open `.mcp.json` and replace the two placeholder values:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--project-ref",
        "YOUR-PROJECT-ID"          ← replace with value from Step 15
      ],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "sbp_YOUR-TOKEN-HERE"   ← replace with token from Step 14
      }
    }
  }
}
```

> **Important:** `.mcp.json` is listed in `.gitignore` — it contains your personal access token and must not be committed. Each developer fills in their own copy.

After saving, restart Claude Code. You should see Supabase tools available (run SQL, list tables, etc.).
