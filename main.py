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
