#!/usr/bin/env python3
"""
Load capability entries from capabilities_payload.py into tool_capabilities.
Idempotent — safe to re-run; existing (tool_id, capability) pairs are skipped.
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

# Allow running from repo root or from scripts/
sys.path.insert(0, os.path.dirname(__file__))
from capabilities_payload import CAPABILITIES

load_dotenv()


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT slug, id FROM tools")
            tool_ids = {row[0]: row[1] for row in cur.fetchall()}

        inserted = 0
        skipped = 0
        unknown_tools = []

        for block in CAPABILITIES:
            slug = block["tool_slug"]
            if slug not in tool_ids:
                print(f"  WARN  {slug}: not found in tools table — skipping")
                unknown_tools.append(slug)
                continue

            tool_id = tool_ids[slug]

            with conn.cursor() as cur:
                for entry in block["entries"]:
                    capability = entry["capability"]
                    protocol_support = entry.get("protocol_support", [])
                    os_support = entry.get("os_support", [])
                    notes = entry.get("notes")

                    cur.execute(
                        """
                        INSERT INTO tool_capabilities
                            (tool_id, capability, protocol_support, os_support, notes)
                        SELECT %s, %s, %s::protocol_support[], %s, %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM tool_capabilities
                            WHERE tool_id = %s AND capability = %s
                        )
                        """,
                        (
                            tool_id, capability, protocol_support, os_support, notes,
                            tool_id, capability,
                        ),
                    )

                    if cur.rowcount:
                        inserted += 1
                        print(f"  +     {slug}  /  {capability}")
                    else:
                        skipped += 1
                        print(f"  skip  {slug}  /  {capability}")

            conn.commit()

        print(f"\nDone: {inserted} inserted, {skipped} skipped")
        if unknown_tools:
            print(f"Unknown tools ({len(unknown_tools)}): {', '.join(unknown_tools)}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
