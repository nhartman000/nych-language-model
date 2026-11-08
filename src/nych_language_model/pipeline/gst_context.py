"""Builder 5 candidate: deterministic TOTE lookup and request-scoped GST.

This module is read-only. It never stores a prompt, candidate taxonomy, or a
new loop. A candidate hit is accepted only after recomputing the versioned
content digest and matching the latest validation and any required review.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import sqlite3
from typing import Any, Literal, Mapping, Protocol, Sequence


DIGEST_VERSION = "NYCH-TOTE-LOOP-DIGEST-V1"
DIGEST_PREFIX = b"NYCH-TOTE-LOOP-DIGEST\x00v1\x00"


class GSTContractError(RuntimeError):
    """The database does not satisfy the candidate GST read contract."""


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A search result with provenance, suitable only as an enrichment candidate."""

    url: str
    title: str
    snippet: str
    query: str
    retrieved_at: str
    content_sha256: str | None = None
    rights_note: str = ""
    provider: str = "google"


@dataclass(frozen=True, slots=True)
class TaxonomyEnrichmentCandidate:
    """Unaccepted taxonomy suggestion carrying its source metadata."""

    domain: str
    query: str
    result: SearchResult
    status: Literal["CANDIDATE_HUMAN_REVIEW"] = "CANDIDATE_HUMAN_REVIEW"


class GoogleSearchProvider(Protocol):
    """Adapter boundary; implementations may call Google outside this module."""

    def search(self, query: str) -> Sequence[SearchResult]:
        """Return sourced results. This interface performs no network access itself."""


@dataclass(frozen=True, slots=True)
class LoopCandidate:
    """Non-canonical extracted loop; admission always requires human review."""

    domain: str
    technique: str | None
    candidate: Mapping[str, Any]
    sources: tuple[SearchResult, ...]
    review_status: Literal["PENDING_HUMAN_REVIEW"] = "PENDING_HUMAN_REVIEW"


@dataclass(frozen=True, slots=True)
class GSTContext:
    """Request-scoped context; no prompt text is retained or included."""

    status: Literal["HIT", "CACHE_MISS"]
    domain: str
    action: str
    loop: Mapping[str, Any] | None
    digest: str | None
    digest_version: str
    miss_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "gst_version": "NYCH-GST-CONTEXT-V1",
            "status": self.status,
            "domain": self.domain,
            "action": self.action,
            "loop": self.loop,
            "digest": self.digest,
            "digest_version": self.digest_version,
            "miss_reason": self.miss_reason,
        }


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _dict_rows(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(sql, params)]


def _source_rows(conn: sqlite3.Connection, source_ids: set[str]) -> list[dict[str, Any]]:
    if not source_ids:
        return []
    placeholders = ",".join("?" for _ in source_ids)
    # created_at is generated database metadata and is deliberately excluded.
    return _dict_rows(
        conn,
        "SELECT source_id,source_type,source_url,title,search_query,retrieved_at,content_sha256,rights_note "
        f"FROM taxonomy_sources WHERE source_id IN ({placeholders}) ORDER BY source_id",
        tuple(sorted(source_ids)),
    )


def canonical_loop_payload(
    conn: sqlite3.Connection,
    loop_id: str,
    *,
    schema_version: str,
) -> dict[str, Any]:
    """Build the contract's canonical payload, including all documented links.

    ``schema_version`` is supplied by the trusted database adapter because the
    draft schema has not settled on a schema-version source. The function does
    not infer one from table presence or ``PRAGMA user_version``.
    """
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("schema_version must be supplied by the trusted adapter")
    tables = _tables(conn)
    required = {"tote_loops", "tote_steps", "loop_gestalts", "gestalts", "modality_operators"}
    missing = required - tables
    if missing:
        raise GSTContractError(f"database is missing required TOTE tables: {', '.join(sorted(missing))}")

    loop_rows = _dict_rows(conn, "SELECT * FROM tote_loops WHERE loop_id=?", (loop_id,))
    if not loop_rows:
        raise KeyError(loop_id)
    if len(loop_rows) != 1:
        raise GSTContractError("loop_id did not resolve to exactly one tote_loops row")

    steps = _dict_rows(conn, "SELECT * FROM tote_steps WHERE loop_id=? ORDER BY step_index", (loop_id,))
    elements = (
        _dict_rows(conn, "SELECT * FROM tote_loop_elements WHERE loop_id=? ORDER BY element_role,element_index", (loop_id,))
        if "tote_loop_elements" in tables else []
    )
    loop_taxonomy = (
        _dict_rows(conn, "SELECT * FROM loop_taxonomy WHERE loop_id=? ORDER BY relationship_role,node_id", (loop_id,))
        if "loop_taxonomy" in tables else []
    )

    # Find every linked taxonomy node and its full CONTAINS ancestor closure.
    linked_ids = {row["node_id"] for row in loop_taxonomy}
    node_ids = set(linked_ids)
    edges: list[dict[str, Any]] = []
    if linked_ids and {"taxonomy_nodes", "taxonomy_edges"} <= tables:
        frontier = set(linked_ids)
        while frontier:
            marks = ",".join("?" for _ in frontier)
            parent_edges = _dict_rows(
                conn,
                "SELECT parent_node_id,child_node_id,relation_type,source_id FROM taxonomy_edges "
                f"WHERE relation_type='CONTAINS' AND child_node_id IN ({marks}) ORDER BY parent_node_id,child_node_id",
                tuple(sorted(frontier)),
            )
            new_edges = [e for e in parent_edges if (e["parent_node_id"], e["child_node_id"]) not in {
                (x["parent_node_id"], x["child_node_id"]) for x in edges
            }]
            if not new_edges:
                break
            edges.extend(new_edges)
            new_nodes = {e["parent_node_id"] for e in new_edges} - node_ids
            node_ids.update(new_nodes)
            frontier = new_nodes

        # Include explicit cross-branch commonality touching the linked closure.
        marks = ",".join("?" for _ in node_ids)
        if node_ids:
            common = _dict_rows(
                conn,
                "SELECT parent_node_id,child_node_id,relation_type,source_id FROM taxonomy_edges "
                f"WHERE relation_type='COMMONALITY' AND (parent_node_id IN ({marks}) OR child_node_id IN ({marks})) "
                "ORDER BY parent_node_id,child_node_id,relation_type",
                tuple(sorted(node_ids)) * 2,
            )
            edges.extend(common)
        edges.sort(key=lambda e: (e["parent_node_id"], e["child_node_id"], e["relation_type"]))

    nodes: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    if node_ids and "taxonomy_nodes" in tables:
        marks = ",".join("?" for _ in node_ids)
        # Generated created_at/updated_at values do not contribute to semantic identity.
        nodes = _dict_rows(
            conn,
            "SELECT node_id,node_type,canonical_label,normalized_label,description,status "
            f"FROM taxonomy_nodes WHERE node_id IN ({marks}) ORDER BY node_id",
            tuple(sorted(node_ids)),
        )
        if "taxonomy_node_sources" in tables:
            node_sources = _dict_rows(
                conn,
                "SELECT node_id,source_id,evidence_note FROM taxonomy_node_sources "
                f"WHERE node_id IN ({marks}) ORDER BY node_id,source_id",
                tuple(sorted(node_ids)),
            )

    loop_sources = (
        _dict_rows(conn, "SELECT loop_id,source_id,source_role FROM loop_sources WHERE loop_id=? ORDER BY source_id,source_role", (loop_id,))
        if "loop_sources" in tables else []
    )
    loop_gestalts = _dict_rows(
        conn,
        "SELECT loop_id,gestalt_id,role FROM loop_gestalts WHERE loop_id=? ORDER BY gestalt_id,role",
        (loop_id,),
    )
    gestalt_ids = {row["gestalt_id"] for row in loop_gestalts}
    gestalts: list[dict[str, Any]] = []
    if gestalt_ids:
        marks = ",".join("?" for _ in gestalt_ids)
        gestalts = _dict_rows(
            conn,
            f"SELECT * FROM gestalts WHERE gestalt_id IN ({marks}) ORDER BY gestalt_id",
            tuple(sorted(gestalt_ids)),
        )
    operator_ids = {row["operator_id"] for row in steps if row.get("operator_id") is not None}
    operators: list[dict[str, Any]] = []
    if operator_ids:
        marks = ",".join("?" for _ in operator_ids)
        operators = _dict_rows(
            conn,
            f"SELECT * FROM modality_operators WHERE operator_id IN ({marks}) ORDER BY operator_id",
            tuple(sorted(operator_ids)),
        )

    source_ids = {r["source_id"] for r in loop_sources}
    source_ids.update(r["source_id"] for r in node_sources)
    source_ids.update(r["source_id"] for r in edges if r.get("source_id") is not None)
    source_ids.update(r["source_id"] for r in elements if r.get("source_id") is not None)
    sources = _source_rows(conn, source_ids) if "taxonomy_sources" in tables else []

    return {
        "schema_version": schema_version,
        "loop": loop_rows[0],
        "steps": steps,
        "elements": elements,
        "taxonomy": {
            "loop_taxonomy": loop_taxonomy,
            "nodes": nodes,
            "edges": edges,
            "node_sources": node_sources,
        },
        "sources": {"loop_sources": loop_sources, "records": sources},
        "loop_gestalts": loop_gestalts,
        "gestalts": gestalts,
        "modality_operators": operators,
    }


def loop_digest(conn: sqlite3.Connection, loop_id: str, *, schema_version: str) -> str:
    """Return lowercase SHA-256 over the approved prefix and canonical JSON."""
    payload = canonical_loop_payload(conn, loop_id, schema_version=schema_version)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(DIGEST_PREFIX + encoded).hexdigest()


def _latest_validation(conn: sqlite3.Connection, loop_id: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT result,loop_sha256,digest_version FROM loop_validation_runs "
        "WHERE loop_id=? ORDER BY validated_at DESC,validation_id DESC LIMIT 1",
        (loop_id,),
    ).fetchone()


def _latest_review(conn: sqlite3.Connection, loop_id: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT outcome,loop_sha256,digest_version FROM loop_human_reviews "
        "WHERE loop_id=? ORDER BY reviewed_at DESC,review_id DESC LIMIT 1",
        (loop_id,),
    ).fetchone()


def _verified_hit(conn: sqlite3.Connection, loop_id: str, *, schema_version: str) -> tuple[bool, str, str]:
    digest = loop_digest(conn, loop_id, schema_version=schema_version)
    tables = _tables(conn)
    if not {"loop_admission", "loop_validation_runs", "loop_human_reviews"} <= tables:
        return False, digest, "VALIDATION_SCHEMA_UNAVAILABLE"
    admission = conn.execute(
        "SELECT origin FROM loop_admission WHERE loop_id=?", (loop_id,)
    ).fetchone()
    validation = _latest_validation(conn, loop_id)
    if admission is None or validation is None:
        return False, digest, "NO_ADMISSION_OR_VALIDATION"
    if validation["result"] != "PASS" or validation["loop_sha256"] != digest or validation["digest_version"] != DIGEST_VERSION:
        return False, digest, "LATEST_VALIDATION_DOES_NOT_MATCH"
    if admission[0] == "HOW_TO_EXTRACTED":
        review = _latest_review(conn, loop_id)
        if review is None or review["outcome"] != "APPROVED" or review["loop_sha256"] != digest or review["digest_version"] != DIGEST_VERSION:
            return False, digest, "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH"
    return True, digest, ""


def lookup_loop(
    conn: sqlite3.Connection,
    *,
    domain: str,
    action: str,
    schema_version: str,
) -> GSTContext:
    """Perform conservative literal domain/action lookup and build GST on hit.

    Literal matching is intentionally limited to ``domain`` and an ACTION row
    in the draft additive table. No fuzzy match, normalization, or inferred
    action policy is applied. Because deterministic action matching is still
    owner-open, this behavior is an explicit candidate adapter contract only.
    """
    if not isinstance(domain, str) or not domain:
        raise ValueError("domain must be non-empty text")
    if not isinstance(action, str) or not action:
        raise ValueError("action must be non-empty text")
    tables = _tables(conn)
    if "tote_loop_elements" not in tables:
        return GSTContext("CACHE_MISS", domain, action, None, None, DIGEST_VERSION, "ACTION_INDEX_UNAVAILABLE")
    matches = _dict_rows(
        conn,
        "SELECT DISTINCT l.loop_id FROM tote_loops l JOIN tote_loop_elements e USING(loop_id) "
        "WHERE l.domain=? AND e.element_role='ACTION' AND e.element_text=? ORDER BY l.loop_id",
        (domain, action),
    )
    if not matches:
        return GSTContext("CACHE_MISS", domain, action, None, None, DIGEST_VERSION, "NO_EXACT_MATCH")
    if len(matches) != 1:
        return GSTContext("CACHE_MISS", domain, action, None, None, DIGEST_VERSION, "AMBIGUOUS_EXACT_MATCH")
    loop_id = matches[0]["loop_id"]
    try:
        valid, digest, reason = _verified_hit(conn, loop_id, schema_version=schema_version)
    except (GSTContractError, KeyError, sqlite3.DatabaseError):
        return GSTContext("CACHE_MISS", domain, action, None, None, DIGEST_VERSION, "DIGEST_RECOMPUTATION_FAILED")
    if not valid:
        return GSTContext("CACHE_MISS", domain, action, None, digest, DIGEST_VERSION, reason)
    payload = canonical_loop_payload(conn, loop_id, schema_version=schema_version)
    return GSTContext("HIT", domain, action, payload, digest, DIGEST_VERSION)


def request_gst(
    conn: sqlite3.Connection,
    *,
    domain: str,
    action: str,
    schema_version: str,
    search_provider: GoogleSearchProvider | None = None,
) -> GSTContext:
    """Lookup first, then optionally expose sourced taxonomy candidates on miss.

    Search enrichment is returned separately in ``GSTContext`` only in a later
    contract revision; V1 deliberately does not issue a network request here.
    The provider is accepted as an injection seam and never invoked until its
    result payload has an owner-approved GST wire schema.
    """
    del search_provider
    return lookup_loop(conn, domain=domain, action=action, schema_version=schema_version)


def search_taxonomy_candidates(
    *, domain: str, queries: Sequence[str], provider: GoogleSearchProvider
) -> tuple[TaxonomyEnrichmentCandidate, ...]:
    """Ask an injected Google adapter for sourced candidates; do no extraction/admission.

    Queries are explicit caller inputs because taxonomy query construction and
    source acceptance/ranking are still owner-open. Results retain URL, title,
    query, retrieval time, content hash, rights note, and provider metadata.
    """
    if not domain:
        raise ValueError("domain must be non-empty")
    candidates: list[TaxonomyEnrichmentCandidate] = []
    for query in queries:
        if not query:
            raise ValueError("queries must contain non-empty strings")
        for result in provider.search(query):
            if result.query != query:
                raise ValueError("search result query must match the requested query")
            if not result.url or not result.retrieved_at:
                raise ValueError("search result requires URL and retrieval timestamp provenance")
            candidates.append(TaxonomyEnrichmentCandidate(domain, query, result))
    return tuple(candidates)


def route_how_to_candidate(
    *, domain: str, technique: str | None, candidate: Mapping[str, Any], sources: Sequence[SearchResult]
) -> LoopCandidate:
    """Wrap an extracted loop for review; it is never inserted into SQLite."""
    if not domain:
        raise ValueError("domain must be non-empty")
    if not sources:
        raise ValueError("candidate requires at least one provenance source")
    return LoopCandidate(domain, technique, dict(candidate), tuple(sources))


def cache_miss_handoff(context: GSTContext) -> dict[str, Any]:
    """Create the explicit B6 handoff payload for a cache miss."""
    if context.status != "CACHE_MISS":
        raise ValueError("cache_miss_handoff requires a CACHE_MISS context")
    return {
        "target": "B6_SYMBOL_SELECTION",
        "domain": context.domain,
        "action": context.action,
        "known_loop": None,
        "cache_miss": True,
        "reason": context.miss_reason,
        "required_invariants": ["actor", "action", "object_or_tool", "registered_modality_operator"],
        "persist_result": False,
    }
