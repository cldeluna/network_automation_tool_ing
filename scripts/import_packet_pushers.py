#!/usr/bin/env python3
"""
Import tools from a Packet Pushers open-source networking CSV export into the spec database.

The Packet Pushers post (https://packetpushers.net/blog/open-source-networking-projects/)
is an HTML page. Export it to CSV manually (copy table to spreadsheet, save as CSV) before
running this script.

Expected CSV columns (header row required):
    name, category, description, url

Usage:
    python scripts/import_packet_pushers.py --csv data/packet_pushers_export.csv [--force]

Environment variables:
    SUPABASE_URL   - Supabase project URL
    SUPABASE_KEY   - Supabase service-role key

The script is idempotent: re-running updates existing records and refreshes
tool_source_map.last_synced_at without duplicating rows.
"""

import csv
import os
import re
import sys
import argparse
from datetime import datetime, timezone

SOURCE_SLUG = "packet-pushers-open-source"

# Map Packet Pushers category names to spec slugs
CATEGORY_SLUG_MAP = {
    "BGP Daemons": "bgp-daemons",
    "BGP Looking Glass": "bgp-looking-glass",
    "RPKI": "rpki",
    "BGP Session Monitoring": "bgp-session-monitoring",
    "Configuration Management": "configuration-management",
    "DCIM / IPAM": "dcim-ipam",
    "Network Management Systems": "network-management-systems",
    "Automation & Orchestration": "automation-orchestration",
    "Flow Collectors": "flow-collectors",
    "Log Management": "log-management",
    "Observability": "observability",
    "DDoS Mitigation": "ddos-mitigation",
    "Firewalls & Filtering": "firewalls-filtering",
    "IDS / IPS": "ids-ips",
    "Network Scanning": "network-scanning",
    "VPN": "vpn",
    "CLI Utilities": "cli-utilities",
    "Packet Capture": "packet-capture",
    "Traffic Generators": "traffic-generators",
    "Cloud Native Networking": "cloud-native-networking",
    "Developer Tools": "developer-tools",
    "Network Simulation": "network-simulation",
    "Network Services": "network-services",
    "Network Operating Systems": "operating-systems",
    "Routing & Overlay": "routing-overlay",
    "Testing & Validation": "testing-validation",
}


def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def upsert_tool(client, row: dict, source_id: str, force: bool) -> None:
    name = (row.get("name") or "").strip()
    if not name:
        return

    slug = slugify(name)
    homepage_url = (row.get("url") or "").strip() or None
    description = (row.get("description") or "").strip() or None
    cat_name = (row.get("category") or "").strip()

    contributed_fields = []
    if homepage_url:
        contributed_fields.append("homepage_url")
    if description:
        contributed_fields.append("description")

    tool_payload = {
        "name": name,
        "slug": slug,
        "tool_type": "platform",
        "status": "active",
    }
    if homepage_url:
        tool_payload["homepage_url"] = homepage_url
    if description:
        tool_payload["description"] = description

    response = (
        client.table("tools")
        .upsert(tool_payload, on_conflict="slug", ignore_duplicates=not force)
        .execute()
    )

    if not response.data:
        print(f"  SKIP (existing, no --force): {slug}", file=sys.stderr)
        return

    tool_id = response.data[0]["id"]

    now = datetime.now(timezone.utc).isoformat()
    client.table("tool_source_map").upsert(
        {
            "tool_id": tool_id,
            "source_id": source_id,
            "source_tool_key": name,
            "contributed_fields": contributed_fields,
            "last_synced_at": now,
        },
        on_conflict="tool_id,source_id",
    ).execute()

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
    elif cat_name:
        print(f"  WARN: no slug mapping for category '{cat_name}' (tool: {slug})", file=sys.stderr)

    print(f"  OK: {slug}")


def get_source_id(client) -> str:
    resp = client.table("data_sources").select("id").eq("slug", SOURCE_SLUG).execute()
    if not resp.data:
        raise RuntimeError(f"data_sources row '{SOURCE_SLUG}' not found — run seed inserts first")
    return resp.data[0]["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Packet Pushers CSV into spec DB")
    parser.add_argument("--csv", required=True, help="Path to exported CSV file")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing tool records with Packet Pushers data",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        print("ERROR: Set SUPABASE_URL and SUPABASE_KEY", file=sys.stderr)
        sys.exit(1)

    from supabase import create_client

    client = create_client(supabase_url, supabase_key)

    rows = load_csv(args.csv)
    print(f"Loaded {len(rows)} rows from {args.csv}")

    source_id = get_source_id(client)

    for row in rows:
        upsert_tool(client, row, source_id, args.force)

    client.table("data_sources").update(
        {"last_synced_at": datetime.now(timezone.utc).isoformat()}
    ).eq("slug", SOURCE_SLUG).execute()

    print("Done.")


if __name__ == "__main__":
    main()
