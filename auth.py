import hashlib

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import get_conn

_bearer = HTTPBearer()


def require_admin(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> str:
    raw_key = credentials.credentials
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM api_keys
                WHERE key_hash = %s
                  AND is_active = TRUE
                  AND (expires_at IS NULL OR expires_at > NOW())
                """,
                (key_hash,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return str(row[0])
