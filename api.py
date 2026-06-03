import hashlib
import secrets

import psycopg2
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from auth import require_admin
from db import get_conn

app = FastAPI(title="Network Automation Registry", version="1.0.0")

NAF_DESCRIPTIONS = {
    "presentation": "User-facing interfaces: dashboards, CLIs, chat bots",
    "intent": "Intent capture and translation: NLP, policy engines",
    "observability": "Telemetry, monitoring, and analytics",
    "collector": "Data collection agents and scrapers",
    "orchestration": "Workflow engines and pipeline coordinators",
    "executor": "Low-level device interaction: SSH, NETCONF, gNMI clients",
    "infrastructure": "Lab and emulation platforms: containerlab, GNS3, EVE-NG",
}

VALID_TRANSITIONS: dict[str, set[str]] = {
    "active": {"deprecated", "archived", "experimental"},
    "experimental": {"active", "archived"},
    "deprecated": {"archived"},
    "archived": set(),
}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ToolCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    tool_type: str
    homepage_url: str | None = None
    repo_url: str | None = None
    license: str | None = None
    status: str = "active"
    naf_functions: list[str] = []
    business_model: str | None = None
    sources: list[str] = Field(..., min_length=1)


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    homepage_url: str | None = None
    repo_url: str | None = None
    license: str | None = None
    status: str | None = None
    naf_functions: list[str] | None = None
    business_model: str | None = None


class CapabilityCreate(BaseModel):
    capability: str
    protocol_support: list[str] = []
    os_support: list[str] = []
    notes: str | None = None


class DependencyCreate(BaseModel):
    depends_on_tool_slug: str
    dependency_type: str = "runtime"
    version_constraint: str | None = None
    notes: str | None = None


class EnvironmentSupportCreate(BaseModel):
    environment_slug: str
    install_method: str
    install_command: str | None = None
    notes: str | None = None


class ReferenceCreate(BaseModel):
    contact_id: str
    use_case: str | None = None


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None


class EnvironmentCreate(BaseModel):
    name: str
    slug: str
    platform: str
    notes: str | None = None


class ContactCreate(BaseModel):
    name: str
    org: str | None = None
    role: str | None = None
    contact_url: str | None = None
    is_public: bool = True
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    org: str | None = None
    role: str | None = None
    contact_url: str | None = None
    is_public: bool | None = None
    notes: str | None = None


class SourceCreate(BaseModel):
    name: str
    slug: str
    url: str | None = None
    description: str | None = None


class AdminKeyCreate(BaseModel):
    name: str
    expires_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def envelope(data, total=None, page=1, per_page=20):
    meta = {}
    if total is not None:
        meta = {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-total // per_page)),
        }
    return {"data": data, "meta": meta, "errors": []}


def paginate(cur, base_query, count_query, params, page, per_page):
    cur.execute(count_query, params)
    total = cur.fetchone()["count"]
    offset = (page - 1) * per_page
    cur.execute(base_query + " LIMIT %s OFFSET %s", list(params) + [per_page, offset])
    return cur.fetchall(), total


def _get_tool_id(cur, slug: str) -> str:
    cur.execute("SELECT id FROM tools WHERE slug = %s", (slug,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return str(row["id"])


def _fetch_tool(cur, tool_id: str) -> dict:
    cur.execute(
        """
        SELECT id, name, slug, description, tool_type::text, status::text,
               homepage_url, repo_url, license, business_model::text,
               naf_functions::text[], created_at, updated_at
        FROM tools WHERE id = %s
        """,
        (tool_id,),
    )
    tool = dict(cur.fetchone())
    cur.execute(
        """
        SELECT tc.slug FROM tool_category_map m
        JOIN tool_categories tc ON tc.id = m.category_id
        WHERE m.tool_id = %s
        """,
        (tool_id,),
    )
    tool["categories"] = [r["slug"] for r in cur.fetchall()]
    cur.execute(
        """
        SELECT capability, protocol_support::text[], os_support, notes
        FROM tool_capabilities WHERE tool_id = %s
        """,
        (tool_id,),
    )
    tool["capabilities"] = [dict(r) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT ds.slug, ds.name, ds.url, tsm.notes
        FROM tool_source_map tsm
        JOIN data_sources ds ON ds.id = tsm.source_id
        WHERE tsm.tool_id = %s
        """,
        (tool_id,),
    )
    tool["sources"] = [dict(r) for r in cur.fetchall()]
    return tool


# ---------------------------------------------------------------------------
# Tools — read
# ---------------------------------------------------------------------------

@app.get("/api/v1/tools")
def list_tools(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    type: str | None = None,
    category: str | None = None,
    protocol: str | None = None,
    environment: str | None = None,
    naf_function: str | None = None,
    business_model: str | None = None,
    source: str | None = None,
    sort: str = Query("name", pattern="^(name|updated_at|created_at)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    filters = []
    params: list = []

    if q:
        filters.append("(t.name ILIKE %s OR t.description ILIKE %s)")
        params += [f"%{q}%", f"%{q}%"]
    if status:
        statuses = status.split(",")
        placeholders = ",".join(["%s"] * len(statuses))
        filters.append(f"t.status::text = ANY(ARRAY[{placeholders}])")
        params += statuses
    if type:
        types = type.split(",")
        placeholders = ",".join(["%s"] * len(types))
        filters.append(f"t.tool_type::text = ANY(ARRAY[{placeholders}])")
        params += types
    if business_model:
        models = business_model.split(",")
        placeholders = ",".join(["%s"] * len(models))
        filters.append(f"t.business_model::text = ANY(ARRAY[{placeholders}])")
        params += models
    if naf_function:
        naf_functions = naf_function.split(",")
        placeholders = ",".join(["%s"] * len(naf_functions))
        filters.append(f"EXISTS (SELECT 1 FROM unnest(t.naf_functions) nf WHERE nf::text = ANY(ARRAY[{placeholders}]))")
        params += naf_functions
    if category:
        filters.append(
            "t.id IN (SELECT tool_id FROM tool_category_map m JOIN tool_categories c ON c.id = m.category_id WHERE c.slug = ANY(%s))"
        )
        params.append(category.split(","))
    if protocol:
        protocols = protocol.split(",")
        placeholders = ",".join(["%s"] * len(protocols))
        filters.append(
            f"t.id IN (SELECT tool_id FROM tool_capabilities WHERE protocol_support && ARRAY[{placeholders}]::protocol_support[])"
        )
        params += protocols
    if environment:
        filters.append(
            "t.id IN (SELECT tool_id FROM tool_environment_support tes JOIN environments e ON e.id = tes.environment_id WHERE e.slug = ANY(%s))"
        )
        params.append(environment.split(","))
    if source:
        filters.append(
            "t.id IN (SELECT tool_id FROM tool_source_map sm JOIN data_sources ds ON ds.id = sm.source_id WHERE ds.slug = ANY(%s))"
        )
        params.append(source.split(","))

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    sort_col = {"name": "t.name", "updated_at": "t.updated_at", "created_at": "t.created_at"}[sort]

    base_query = f"""
        SELECT t.id, t.name, t.slug, t.description, t.tool_type::text, t.status::text,
               t.homepage_url, t.repo_url, t.license, t.business_model::text,
               t.naf_functions::text[], t.created_at, t.updated_at,
               COALESCE(
                 array_agg(DISTINCT tc.slug) FILTER (WHERE tc.slug IS NOT NULL), ARRAY[]::text[]
               ) AS categories
        FROM tools t
        LEFT JOIN tool_category_map m ON m.tool_id = t.id
        LEFT JOIN tool_categories tc ON tc.id = m.category_id
        {where}
        GROUP BY t.id
        ORDER BY {sort_col} {order}
    """
    count_query = f"SELECT COUNT(DISTINCT t.id) FROM tools t {where}"

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            rows, total = paginate(cur, base_query, count_query, params, page, per_page)

    return envelope([dict(r) for r in rows], total=total, page=page, per_page=per_page)


@app.get("/api/v1/tools/{slug}")
def get_tool(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM tools WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Tool not found")
            tool = _fetch_tool(cur, str(row["id"]))
    return envelope(tool)


@app.get("/api/v1/tools/{slug}/capabilities")
def get_tool_capabilities(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                """
                SELECT id, capability, protocol_support::text[], os_support, notes
                FROM tool_capabilities WHERE tool_id = %s
                """,
                (tool_id,),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.get("/api/v1/tools/{slug}/dependencies")
def get_tool_dependencies(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                """
                SELECT d.name, d.slug, td.id, td.dependency_type::text, td.version_constraint, td.notes
                FROM tool_dependencies td
                JOIN tools d ON d.id = td.depends_on_tool_id
                WHERE td.tool_id = %s
                """,
                (tool_id,),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.get("/api/v1/tools/{slug}/environments")
def get_tool_environments(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                """
                SELECT e.slug, e.name, e.platform::text,
                       tes.install_method::text, tes.install_command, tes.notes
                FROM tool_environment_support tes
                JOIN environments e ON e.id = tes.environment_id
                WHERE tes.tool_id = %s
                """,
                (tool_id,),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.get("/api/v1/tools/{slug}/references")
def get_tool_references(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                """
                SELECT c.id, c.name, c.org, c.role, c.contact_url, tcm.use_case
                FROM tool_contact_map tcm
                JOIN contacts c ON c.id = tcm.contact_id
                WHERE tcm.tool_id = %s AND c.is_public = TRUE
                """,
                (tool_id,),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Tools — write
# ---------------------------------------------------------------------------

@app.post("/api/v1/tools", status_code=201)
def create_tool(body: ToolCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT slug FROM data_sources WHERE slug = ANY(%s)",
                (body.sources,),
            )
            found = {r["slug"] for r in cur.fetchall()}
            missing = [s for s in body.sources if s not in found]
            if missing:
                raise HTTPException(status_code=400, detail=f"Unknown source slugs: {missing}")

            try:
                cur.execute(
                    """
                    INSERT INTO tools
                        (name, slug, description, tool_type, homepage_url, repo_url,
                         license, status, naf_functions, business_model)
                    VALUES (%s, %s, %s, %s::tool_type, %s, %s, %s, %s::tool_status,
                            %s::naf_function[], %s::business_model)
                    RETURNING id
                    """,
                    (
                        body.name, body.slug, body.description, body.tool_type,
                        body.homepage_url, body.repo_url, body.license, body.status,
                        body.naf_functions, body.business_model,
                    ),
                )
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Slug already exists")

            tool_id = str(cur.fetchone()["id"])

            for source_slug in body.sources:
                cur.execute(
                    """
                    INSERT INTO tool_source_map (tool_id, source_id)
                    SELECT %s, id FROM data_sources WHERE slug = %s
                    """,
                    (tool_id, source_slug),
                )

            conn.commit()
            tool = _fetch_tool(cur, tool_id)

    return envelope(tool)


@app.patch("/api/v1/tools/{slug}")
def update_tool(slug: str, body: ToolUpdate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, status::text FROM tools WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Tool not found")
            tool_id = str(row["id"])
            current_status = row["status"]

            if "status" in body.model_fields_set and body.status != current_status:
                allowed = VALID_TRANSITIONS.get(current_status, set())
                if body.status not in allowed:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Invalid status transition: {current_status} → {body.status}",
                    )

            set_parts: list[str] = []
            params: list = []

            _SIMPLE = ("name", "description", "homepage_url", "repo_url", "license")
            for field in _SIMPLE:
                if field in body.model_fields_set:
                    set_parts.append(f"{field} = %s")
                    params.append(getattr(body, field))
            if "status" in body.model_fields_set:
                set_parts.append("status = %s::tool_status")
                params.append(body.status)
            if "naf_functions" in body.model_fields_set:
                set_parts.append("naf_functions = %s::naf_function[]")
                params.append(body.naf_functions)
            if "business_model" in body.model_fields_set:
                set_parts.append("business_model = %s::business_model")
                params.append(body.business_model)

            if set_parts:
                params.append(tool_id)
                cur.execute(
                    f"UPDATE tools SET {', '.join(set_parts)} WHERE id = %s",
                    params,
                )
                conn.commit()

            tool = _fetch_tool(cur, tool_id)

    return envelope(tool)


@app.delete("/api/v1/tools/{slug}", status_code=204)
def delete_tool(slug: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tools WHERE slug = %s", (slug,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Tool not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Tool capabilities — write
# ---------------------------------------------------------------------------

@app.post("/api/v1/tools/{slug}/capabilities", status_code=201)
def add_capability(slug: str, body: CapabilityCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                """
                INSERT INTO tool_capabilities (tool_id, capability, protocol_support, os_support, notes)
                VALUES (%s, %s, %s::protocol_support[], %s::text[], %s)
                RETURNING id, capability, protocol_support::text[], os_support, notes
                """,
                (tool_id, body.capability, body.protocol_support, body.os_support, body.notes),
            )
            row = dict(cur.fetchone())
            conn.commit()
    return envelope(row)


@app.delete("/api/v1/tools/{slug}/capabilities/{cap_id}", status_code=204)
def delete_capability(slug: str, cap_id: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                "DELETE FROM tool_capabilities WHERE id = %s AND tool_id = %s",
                (cap_id, tool_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Capability not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Tool dependencies — write
# ---------------------------------------------------------------------------

@app.post("/api/v1/tools/{slug}/dependencies", status_code=201)
def add_dependency(slug: str, body: DependencyCreate, _: str = Depends(require_admin)):
    if slug == body.depends_on_tool_slug:
        raise HTTPException(status_code=400, detail="A tool cannot depend on itself")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute("SELECT id FROM tools WHERE slug = %s", (body.depends_on_tool_slug,))
            dep_row = cur.fetchone()
            if dep_row is None:
                raise HTTPException(status_code=404, detail=f"Dependency tool '{body.depends_on_tool_slug}' not found")
            depends_on_id = str(dep_row["id"])

            try:
                cur.execute(
                    """
                    INSERT INTO tool_dependencies
                        (tool_id, depends_on_tool_id, dependency_type, version_constraint, notes)
                    VALUES (%s, %s, %s::dependency_type, %s, %s)
                    RETURNING id, dependency_type::text, version_constraint, notes
                    """,
                    (tool_id, depends_on_id, body.dependency_type, body.version_constraint, body.notes),
                )
                row = dict(cur.fetchone())
                conn.commit()
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Dependency edge already exists")

    return envelope(row)


@app.delete("/api/v1/tools/{slug}/dependencies/{dep_id}", status_code=204)
def delete_dependency(slug: str, dep_id: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                "DELETE FROM tool_dependencies WHERE id = %s AND tool_id = %s",
                (dep_id, tool_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Dependency not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Tool environment support — write
# ---------------------------------------------------------------------------

@app.post("/api/v1/tools/{slug}/environments", status_code=201)
def add_environment_support(slug: str, body: EnvironmentSupportCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute("SELECT id FROM environments WHERE slug = %s", (body.environment_slug,))
            env_row = cur.fetchone()
            if env_row is None:
                raise HTTPException(status_code=404, detail=f"Environment '{body.environment_slug}' not found")
            env_id = str(env_row["id"])

            try:
                cur.execute(
                    """
                    INSERT INTO tool_environment_support
                        (tool_id, environment_id, install_method, install_command, notes)
                    VALUES (%s, %s, %s::install_method, %s, %s)
                    RETURNING install_method::text, install_command, notes
                    """,
                    (tool_id, env_id, body.install_method, body.install_command, body.notes),
                )
                row = dict(cur.fetchone())
                row["environment_slug"] = body.environment_slug
                conn.commit()
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Environment support already exists for this tool/environment pair")

    return envelope(row)


@app.delete("/api/v1/tools/{slug}/environments/{env_slug}", status_code=204)
def delete_environment_support(slug: str, env_slug: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                """
                DELETE FROM tool_environment_support
                WHERE tool_id = %s
                  AND environment_id = (SELECT id FROM environments WHERE slug = %s)
                """,
                (tool_id, env_slug),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Environment support not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Tool contact references — write
# ---------------------------------------------------------------------------

@app.post("/api/v1/tools/{slug}/references", status_code=201)
def add_reference(slug: str, body: ReferenceCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute("SELECT id, name FROM contacts WHERE id = %s", (body.contact_id,))
            contact_row = cur.fetchone()
            if contact_row is None:
                raise HTTPException(status_code=404, detail="Contact not found")

            try:
                cur.execute(
                    """
                    INSERT INTO tool_contact_map (tool_id, contact_id, use_case)
                    VALUES (%s, %s, %s)
                    RETURNING use_case, created_at
                    """,
                    (tool_id, body.contact_id, body.use_case),
                )
                row = dict(cur.fetchone())
                row["contact_id"] = body.contact_id
                row["contact_name"] = contact_row["name"]
                conn.commit()
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Reference already exists")

    return envelope(row)


@app.delete("/api/v1/tools/{slug}/references/{contact_id}", status_code=204)
def delete_reference(slug: str, contact_id: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            tool_id = _get_tool_id(cur, slug)
            cur.execute(
                "DELETE FROM tool_contact_map WHERE tool_id = %s AND contact_id = %s",
                (tool_id, contact_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Reference not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.get("/api/v1/categories")
def list_categories():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tool_categories ORDER BY name")
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.get("/api/v1/categories/{slug}/tools")
def list_tools_by_category(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM tool_categories WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Category not found")
            cur.execute(
                """
                SELECT t.id, t.name, t.slug, t.tool_type::text, t.status::text, t.description
                FROM tools t
                JOIN tool_category_map m ON m.tool_id = t.id
                WHERE m.category_id = %s
                ORDER BY t.name
                """,
                (row["id"],),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.post("/api/v1/categories", status_code=201)
def create_category(body: CategoryCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO tool_categories (name, slug, description)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (body.name, body.slug, body.description),
                )
                row = dict(cur.fetchone())
                conn.commit()
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Slug already exists")
    return envelope(row)


@app.delete("/api/v1/categories/{slug}", status_code=204)
def delete_category(slug: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tool_categories WHERE slug = %s", (slug,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Category not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------

@app.get("/api/v1/environments")
def list_environments():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, slug, platform::text, notes, created_at FROM environments ORDER BY name")
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.get("/api/v1/environments/{slug}/tools")
def list_tools_by_environment(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM environments WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Environment not found")
            cur.execute(
                """
                SELECT t.id, t.name, t.slug, t.tool_type::text, t.status::text,
                       tes.install_method::text, tes.install_command
                FROM tools t
                JOIN tool_environment_support tes ON tes.tool_id = t.id
                WHERE tes.environment_id = %s
                ORDER BY t.name
                """,
                (row["id"],),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.post("/api/v1/environments", status_code=201)
def create_environment(body: EnvironmentCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO environments (name, slug, platform, notes)
                    VALUES (%s, %s, %s::platform_type, %s)
                    RETURNING id, name, slug, platform::text, notes, created_at
                    """,
                    (body.name, body.slug, body.platform, body.notes),
                )
                row = dict(cur.fetchone())
                conn.commit()
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Slug already exists")
    return envelope(row)


@app.delete("/api/v1/environments/{slug}", status_code=204)
def delete_environment(slug: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM environments WHERE slug = %s", (slug,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Environment not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Capabilities search
# ---------------------------------------------------------------------------

@app.get("/api/v1/capabilities")
def list_capabilities(
    protocol: str | None = None,
    os: str | None = None,
):
    filters = []
    params: list = []

    if protocol:
        protocols = protocol.split(",")
        placeholders = ",".join(["%s"] * len(protocols))
        filters.append(f"tc.protocol_support && ARRAY[{placeholders}]::protocol_support[]")
        params += protocols
    if os:
        filters.append("tc.os_support && %s::text[]")
        params.append(os.split(","))

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    query = f"""
        SELECT t.name AS tool_name, t.slug AS tool_slug,
               tc.capability, tc.protocol_support::text[], tc.os_support, tc.notes
        FROM tool_capabilities tc
        JOIN tools t ON t.id = tc.tool_id
        {where}
        ORDER BY t.name, tc.capability
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# NAF Functions
# ---------------------------------------------------------------------------

@app.get("/api/v1/naf-functions")
def list_naf_functions():
    data = [{"function": k, "description": v} for k, v in NAF_DESCRIPTIONS.items()]
    return envelope(data)


@app.get("/api/v1/naf-functions/{function}/tools")
def list_tools_by_naf_function(function: str):
    if function not in NAF_DESCRIPTIONS:
        raise HTTPException(status_code=404, detail="NAF function not found")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, slug, tool_type::text, status::text, description, naf_functions::text[]
                FROM tools
                WHERE %s::naf_function = ANY(naf_functions)
                ORDER BY name
                """,
                (function,),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Contacts (admin-gated full CRUD)
# ---------------------------------------------------------------------------

@app.get("/api/v1/contacts")
def list_contacts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _: str = Depends(require_admin),
):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            rows, total = paginate(
                cur,
                "SELECT id, name, org, role, contact_url, is_public, notes, created_at, updated_at FROM contacts ORDER BY name",
                "SELECT COUNT(*) FROM contacts",
                [],
                page,
                per_page,
            )
    return envelope([dict(r) for r in rows], total=total, page=page, per_page=per_page)


@app.post("/api/v1/contacts", status_code=201)
def create_contact(body: ContactCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO contacts (name, org, role, contact_url, is_public, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (body.name, body.org, body.role, body.contact_url, body.is_public, body.notes),
            )
            row = dict(cur.fetchone())
            conn.commit()
    return envelope(row)


@app.patch("/api/v1/contacts/{contact_id}")
def update_contact(contact_id: str, body: ContactUpdate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM contacts WHERE id = %s", (contact_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Contact not found")

            set_parts: list[str] = []
            params: list = []
            for field in ("name", "org", "role", "contact_url", "is_public", "notes"):
                if field in body.model_fields_set:
                    set_parts.append(f"{field} = %s")
                    params.append(getattr(body, field))

            if not set_parts:
                cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
                return envelope(dict(cur.fetchone()))

            params.append(contact_id)
            cur.execute(
                f"UPDATE contacts SET {', '.join(set_parts)} WHERE id = %s RETURNING *",
                params,
            )
            row = dict(cur.fetchone())
            conn.commit()
    return envelope(row)


@app.delete("/api/v1/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Contact not found")
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------

@app.get("/api/v1/sources")
def list_sources():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM data_sources ORDER BY name")
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.get("/api/v1/sources/{slug}/tools")
def list_tools_by_source(slug: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM data_sources WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Source not found")
            cur.execute(
                """
                SELECT t.id, t.name, t.slug, t.tool_type::text, t.status::text, tsm.notes
                FROM tools t
                JOIN tool_source_map tsm ON tsm.tool_id = t.id
                WHERE tsm.source_id = %s
                ORDER BY t.name
                """,
                (row["id"],),
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.post("/api/v1/sources", status_code=201)
def create_source(body: SourceCreate, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO data_sources (name, slug, url, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (body.name, body.slug, body.url, body.description),
                )
                row = dict(cur.fetchone())
                conn.commit()
            except psycopg2.IntegrityError:
                raise HTTPException(status_code=409, detail="Slug already exists")
    return envelope(row)


@app.delete("/api/v1/sources/{slug}", status_code=204)
def delete_source(slug: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM data_sources WHERE slug = %s", (slug,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Source not found")
            source_id = row["id"]

            cur.execute("SELECT COUNT(*) FROM tool_source_map WHERE source_id = %s", (source_id,))
            count = cur.fetchone()["count"]
            if count > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete source: {count} tool(s) reference it. Reassign tools first.",
                )

            cur.execute("DELETE FROM data_sources WHERE id = %s", (source_id,))
            conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Admin — API key management
# ---------------------------------------------------------------------------

@app.get("/api/v1/admin/keys")
def list_admin_keys(_: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, key_prefix, is_active, created_at, last_used_at, expires_at
                FROM api_keys ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
    return envelope([dict(r) for r in rows])


@app.post("/api/v1/admin/keys", status_code=201)
def create_admin_key(body: AdminKeyCreate, _: str = Depends(require_admin)):
    raw_key = "nart_" + secrets.token_urlsafe(32)
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO api_keys (name, key_prefix, key_hash, expires_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, key_prefix, is_active, created_at, expires_at
                """,
                (body.name, key_prefix, key_hash, body.expires_at),
            )
            row = dict(cur.fetchone())
            conn.commit()

    row["raw_key"] = raw_key
    return envelope(row)


@app.delete("/api/v1/admin/keys/{key_id}", status_code=204)
def revoke_admin_key(key_id: str, _: str = Depends(require_admin)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE api_keys SET is_active = FALSE WHERE id = %s", (key_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="API key not found")
            conn.commit()
    return Response(status_code=204)
