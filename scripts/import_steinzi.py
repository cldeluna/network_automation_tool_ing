#!/usr/bin/env python3
"""
Import tools from the Steinzi network-automation-landscape YAML into the spec database.

Usage:
    python scripts/import_steinzi.py [--force]

Environment variables:
    SUPABASE_URL   - Supabase project URL
    SUPABASE_KEY   - Supabase service-role key
    DATABASE_URL   - Direct PostgreSQL URL (alternative to Supabase client)

The script is idempotent: re-running updates existing tool records and refreshes
tool_source_map.last_synced_at without duplicating rows.
"""

import os
import re
import sys
import argparse
from datetime import datetime, timezone

import requests
import yaml

LANDSCAPE_URL = (
    "https://raw.githubusercontent.com/steinzi/network-automation-landscape/main/data.yml"
)
SOURCE_SLUG = "steinzi-landscape"

# Map Steinzi 'project' values to license_model_type enum values
LICENSE_MODEL_MAP = {
    "open-source": "full-open-source",
    "enterprise": "enterprise",
    "saas": "saas",
    "hybrid": "hybrid",
    "freemium": "freemium",
    "closed-core": "closed-core",
    "commercial": "commercial-only",
    "free-restrictive": "free-restrictive",
}

# Map Steinzi category names to spec slugs (extend as needed)
CATEGORY_SLUG_MAP = {
    "Configuration Management": "configuration-management",
    "Source of Truth": "dcim-ipam",
    "Observability": "observability",
    "Automation & Orchestration": "automation-orchestration",
    "Templating": "templating",
    "Data Modeling": "data-modeling",
    "Network Simulation": "network-simulation",
    "AI Agent": "ai-agent",
    "Testing & Validation": "testing-validation",
}


def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def fetch_landscape() -> dict:
    resp = requests.get(LANDSCAPE_URL, timeout=30)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def extract_tools(data: dict) -> list[dict]:
    tools = []
    for category in data.get("landscape", []):
        cat_name = category.get("name", "")
        for subcategory in category.get("subcategories", []):
            for item in subcategory.get("items", []):
                tools.append({"_category": cat_name, **item})
    return tools


def upsert_tool(client, tool: dict, source_id: str, force: bool) -> None:
    name = tool.get("name", "").strip()
    if not name:
        return

    slug = slugify(name)
    homepage_url = tool.get("homepage_url") or tool.get("url")
    repo_url = tool.get("repo_url")
    description = (tool.get("extra") or {}).get("summary") or tool.get("description")
    license_spdx = tool.get("license")
    license_model_raw = tool.get("project")
    license_model = LICENSE_MODEL_MAP.get(license_model_raw)

    contributed_fields = []
    if homepage_url:
        contributed_fields.append("homepage_url")
    if repo_url:
        contributed_fields.append("repo_url")
    if license_spdx:
        contributed_fields.append("license")
    if description:
        contributed_fields.append("description")
    if license_model:
        contributed_fields.append("license_model")

    tool_payload = {
        "name": name,
        "slug": slug,
        "tool_type": "platform",  # default; refine with tag inspection if needed
        "status": "active",
    }
    if homepage_url:
        tool_payload["homepage_url"] = homepage_url
    if repo_url:
        tool_payload["repo_url"] = repo_url
    if description:
        tool_payload["description"] = description
    if license_spdx:
        tool_payload["license"] = license_spdx
    if license_model:
        tool_payload["license_model"] = license_model

    response = (
        client.table("tools")
        .upsert(tool_payload, on_conflict="slug", ignore_duplicates=not force)
        .execute()
    )

    if not response.data:
        print(f"  SKIP (existing, no --force): {slug}", file=sys.stderr)
        return

    tool_id = response.data[0]["id"]

    # Record provenance
    now = datetime.now(timezone.utc).isoformat()
    client.table("tool_source_map").upsert(
        {
            "tool_id": tool_id,
            "source_id": source_id,
            "source_tool_key": slug,
            "contributed_fields": contributed_fields,
            "last_synced_at": now,
        },
        on_conflict="tool_id,source_id",
    ).execute()

    # Map category
    cat_name = tool.get("_category", "")
    cat_slug = CATEGORY_SLUG_MAP.get(cat_name)
    if cat_slug:
        cat_resp = client.table("tool_categories").select("id").eq("slug", cat_slug).execute()
        if cat_resp.data:
            cat_id = cat_resp.data[0]["id"]
            client.table("tool_category_map").upsert(
                {"tool_id": tool_id, "category_id": cat_id},
                on_conflict="tool_id,category_id",
                ignore_duplicates=True,
            ).execute()

    print(f"  OK: {slug}")


def get_source_id(client) -> str:
    resp = client.table("data_sources").select("id").eq("slug", SOURCE_SLUG).execute()
    if not resp.data:
        raise RuntimeError(f"data_sources row '{SOURCE_SLUG}' not found — run seed inserts first")
    return resp.data[0]["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Steinzi landscape into spec DB")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing tool records with Steinzi data",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY", file=sys.stderr)
        sys.exit(1)

    from supabase import create_client

    client = create_client(supabase_url, supabase_key)

    print(f"Fetching landscape from {LANDSCAPE_URL} ...")
    data = fetch_landscape()
    tools = extract_tools(data)
    print(f"Found {len(tools)} tools")

    source_id = get_source_id(client)

    for tool in tools:
        upsert_tool(client, tool, source_id, args.force)

    # Update last_synced_at on the data_sources row
    client.table("data_sources").update(
        {"last_synced_at": datetime.now(timezone.utc).isoformat()}
    ).eq("slug", SOURCE_SLUG).execute()

    print("Done.")


if __name__ == "__main__":
    main()
