"""Builder 5 candidate: deterministic TOTE lookup and request-scoped GST.

This module is read-only. It never stores a prompt, candidate taxonomy, or a
new loop. A candidate hit is accepted only after recomputing the versioned
content digest and matching the latest validation and any required review.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from hashlib import sha256
import json
import sqlite3
from typing import Any, Literal, Mapping, Protocol, Sequence


DIGEST_VERSION = "NYCH-TOTE-LOOP-DIGEST-V1"
DIGEST_PREFIX = b"NYCH-TOTE-LOOP-DIGEST\x00v1\x00"
ORIGIN_POLICY = {
    "HUMAN_AUTHORED": "PASS_VALIDATION_NO_REVIEW_REQUIRED",
    "HOW_TO_EXTRACTED": "LATEST_MATCHING_APPROVED_REVIEW_REQUIRED",
}
REQUIRED_PAYLOAD_TABLES = frozenset(
    {
        "tote_loops",
        "tote_steps",
        "loop_gestalts",
        "gestalts",
        "modality_operators",
        "tote_loop_elements",
        "loop_taxonomy",
        "taxonomy_nodes",
        "taxonomy_edges",
        "taxonomy_node_sources",
        "loop_sources",
        "taxonomy_sources",
    }
)


class GSTContractError(RuntimeError):
    """The database does not satisfy the candidate GST read contract."""


def _validate_context_inputs(narrative: Mapping[str, Any] | None, provenance: Sequence[Mapping[str, Any]]) -> None:
    allowed = {"perspective", "tense", "subject", "predicate", "intervals"}
    if narrative is not None:
        if not isinstance(narrative, Mapping) or set(narrative) - allowed:
            raise ValueError("narrative must contain only structured NYCH narrative fields")
        if set(narrative) != allowed:
            raise ValueError("narrative requires perspective, tense, subject, predicate, intervals")
        if not isinstance(narrative["intervals"], list):
            raise ValueError("narrative intervals must be a list")
        for interval in narrative["intervals"]:
            required_interval = {"kind", "start", "end", "duration"}
            if not isinstance(interval, Mapping) or set(interval) != required_interval:
                raise ValueError("each interval requires kind, start, end, and duration")
            if interval["kind"] not in {"POINT", "RANGE", "DURATION"}:
                raise ValueError("interval kind must be POINT, RANGE, or DURATION")
            for key in ("start", "end", "duration"):
                if interval[key] is not None and not isinstance(interval[key], str):
                    raise ValueError(f"interval {key} must be text or null")
        for key in ("perspective", "tense", "subject", "predicate"):
            if narrative[key] is not None and not isinstance(narrative[key], str):
                raise ValueError(f"narrative {key} must be text or null")
    if not isinstance(provenance, Sequence) or isinstance(provenance, (str, bytes)):
        raise ValueError("provenance must be a sequence of structured span records")
    for item in provenance:
        if not isinstance(item, Mapping) or set(item) != {"field", "source_digest", "byte_start", "byte_end", "epistemic_status"}:
            raise ValueError("provenance records require field, source_digest, byte_start, byte_end, epistemic_status")
        if not isinstance(item["field"], str) or not item["field"]:
            raise ValueError("provenance field must be non-empty text")
        digest = item["source_digest"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("provenance source_digest must be lowercase SHA-256")
        if (not isinstance(item["byte_start"], int) or isinstance(item["byte_start"], bool)
                or not isinstance(item["byte_end"], int) or isinstance(item["byte_end"], bool)
                or not 0 <= item["byte_start"] < item["byte_end"]):
            raise ValueError("provenance requires a non-empty half-open byte span")
        if item["epistemic_status"] not in {"explicit", "inferred", "predicted"}:
            raise ValueError("invalid provenance epistemic_status")


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
    domain_id: str
    action_key: str
    loop: Mapping[str, Any] | None
    digest: str | None
    digest_version: str
    miss_reason: str | None = None
    narrative: Mapping[str, Any] | None = None
    provenance: tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "gst_version": "NYCH-GST-CONTEXT-V1",
            "status": self.status,
            "request": {"domain_id": self.domain_id, "canonical_action_key": self.action_key},
            "taxonomy": (self.loop or {}).get("taxonomy", {}),
            "tote": self.loop,
            "narrative": self.narrative or {"perspective": None, "tense": None, "subject": None, "predicate": None, "intervals": []},
            "provenance": list(self.provenance),
            "integrity": {
                "digest": self.digest,
                "digest_version": self.digest_version,
                "schema_version": (self.loop or {}).get("schema_version"),
            },
            "miss_reason": self.miss_reason,
        }


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


@contextmanager
def _read_snapshot(conn: sqlite3.Connection):
    """Keep match selection, digest verification, and GST assembly in one snapshot."""
    name = "nych_b5_read_snapshot"
    conn.execute(f"SAVEPOINT {name}")
    try:
        yield
    except BaseException:
        conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
        conn.execute(f"RELEASE SAVEPOINT {name}")
        raise
    else:
        conn.execute(f"RELEASE SAVEPOINT {name}")


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
) -> dict[str, Any]:
    """Build the contract's canonical payload, including all documented links.

    The migration-owned SQLite user_version is authoritative and part of the
    digest payload. Version 2 is required by the B5 additive schema contract.
    """
    schema_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if schema_version != 2:
        raise GSTContractError(f"unsupported TOTE schema version: {schema_version}; expected 2")
    tables = _tables(conn)
    missing = REQUIRED_PAYLOAD_TABLES - tables
    if missing:
        raise GSTContractError(f"database is missing required TOTE tables: {', '.join(sorted(missing))}")

    loop_rows = _dict_rows(conn, "SELECT * FROM tote_loops WHERE loop_id=?", (loop_id,))
    if not loop_rows:
        raise KeyError(loop_id)
    if len(loop_rows) != 1:
        raise GSTContractError("loop_id did not resolve to exactly one tote_loops row")

    steps = _dict_rows(conn, "SELECT * FROM tote_steps WHERE loop_id=? ORDER BY step_index", (loop_id,))
    elements = _dict_rows(conn, "SELECT * FROM tote_loop_elements WHERE loop_id=? ORDER BY element_role,element_index", (loop_id,))
    loop_taxonomy = _dict_rows(conn, "SELECT * FROM loop_taxonomy WHERE loop_id=? ORDER BY relationship_role,node_id", (loop_id,))

    # Find every linked taxonomy node and its full CONTAINS ancestor closure.
    linked_ids = {row["node_id"] for row in loop_taxonomy}
    node_ids = set(linked_ids)
    edges: list[dict[str, Any]] = []
    if linked_ids:
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
    if node_ids:
        marks = ",".join("?" for _ in node_ids)
        # Generated created_at/updated_at values do not contribute to semantic identity.
        nodes = _dict_rows(
            conn,
            "SELECT node_id,node_type,canonical_label,normalized_label,description,status "
            f"FROM taxonomy_nodes WHERE node_id IN ({marks}) ORDER BY node_id",
            tuple(sorted(node_ids)),
        )
        node_sources = _dict_rows(
            conn,
            "SELECT node_id,source_id,evidence_note FROM taxonomy_node_sources "
            f"WHERE node_id IN ({marks}) ORDER BY node_id,source_id",
            tuple(sorted(node_ids)),
        )

    loop_sources = _dict_rows(
        conn,
        "SELECT loop_id,source_id,source_role FROM loop_sources WHERE loop_id=? ORDER BY source_id,source_role",
        (loop_id,),
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
    sources = _source_rows(conn, source_ids)

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


def loop_digest(conn: sqlite3.Connection, loop_id: str) -> str:
    """Return lowercase SHA-256 over the approved prefix and canonical JSON."""
    payload = canonical_loop_payload(conn, loop_id)
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


def _verified_hit(conn: sqlite3.Connection, loop_id: str) -> tuple[bool, str, str]:
    digest = loop_digest(conn, loop_id)
    tables = _tables(conn)
    if not {"loop_admission", "loop_validation_runs", "loop_human_reviews"} <= tables:
        return False, digest, "VALIDATION_SCHEMA_UNAVAILABLE"
    admission = conn.execute(
        "SELECT origin,admission_status,verified_loop_sha256,verified_digest_version "
        "FROM loop_admission WHERE loop_id=?", (loop_id,)
    ).fetchone()
    validation = _latest_validation(conn, loop_id)
    if admission is None:
        return False, digest, "NO_ADMISSION"
    if admission[1] != "ADMITTED":
        return False, digest, "NOT_ADMITTED"
    if admission[2] != digest or admission[3] != DIGEST_VERSION:
        return False, digest, "ADMISSION_DIGEST_DOES_NOT_MATCH"
    if validation is None:
        return False, digest, "NO_VALIDATION"
    if validation["result"] != "PASS" or validation["loop_sha256"] != digest or validation["digest_version"] != DIGEST_VERSION:
        return False, digest, "LATEST_VALIDATION_DOES_NOT_MATCH"
    origin = admission[0]
    if origin == "HUMAN_AUTHORED":
        pass  # The approved workflow requires automatic validation, not human review.
    elif origin == "HOW_TO_EXTRACTED":
        review = _latest_review(conn, loop_id)
        if review is None or review["outcome"] != "APPROVED" or review["loop_sha256"] != digest or review["digest_version"] != DIGEST_VERSION:
            return False, digest, "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH"
    else:
        # SEED, OTHER, and future/unknown origins have no approved admission policy.
        return False, digest, "UNSUPPORTED_ORIGIN"
    return True, digest, ""


def lookup_loop(
    conn: sqlite3.Connection,
    *,
    domain_id: str,
    action_key: str,
    narrative: Mapping[str, Any] | None = None,
    provenance: Sequence[Mapping[str, Any]] = (),
) -> GSTContext:
    """Perform conservative literal domain/action lookup and build GST on hit.

    Match exact canonical taxonomy ID and exact normalized action key. No
    fuzzy matching or normalization occurs in B5; upstream owns canonicalization.
    """
    if not isinstance(domain_id, str) or not domain_id:
        raise ValueError("domain_id must be non-empty text")
    if not isinstance(action_key, str) or not action_key:
        raise ValueError("action_key must be non-empty text")
    _validate_context_inputs(narrative, provenance)
    tables = _tables(conn)
    if "tote_loop_elements" not in tables:
        return GSTContext("CACHE_MISS", domain_id, action_key, None, None, DIGEST_VERSION, "ACTION_INDEX_UNAVAILABLE", narrative, tuple(provenance))
    try:
        with _read_snapshot(conn):
            matches = _dict_rows(
                conn,
                "SELECT DISTINCT l.loop_id FROM tote_loops l "
                "JOIN tote_loop_elements e USING(loop_id) "
                "JOIN loop_taxonomy lt ON lt.loop_id=l.loop_id AND lt.relationship_role='DOMAIN' "
                "WHERE lt.node_id=? AND e.element_role='ACTION' AND e.normalized_key=? ORDER BY l.loop_id",
                (domain_id, action_key),
            )
            if not matches:
                return GSTContext("CACHE_MISS", domain_id, action_key, None, None, DIGEST_VERSION, "NO_EXACT_MATCH", narrative, tuple(provenance))
            if len(matches) != 1:
                return GSTContext("CACHE_MISS", domain_id, action_key, None, None, DIGEST_VERSION, "AMBIGUOUS_EXACT_MATCH", narrative, tuple(provenance))
            loop_id = matches[0]["loop_id"]
            valid, digest, reason = _verified_hit(conn, loop_id)
            if not valid:
                return GSTContext("CACHE_MISS", domain_id, action_key, None, digest, DIGEST_VERSION, reason, narrative, tuple(provenance))
            payload = canonical_loop_payload(conn, loop_id)
            return GSTContext("HIT", domain_id, action_key, payload, digest, DIGEST_VERSION, None, narrative, tuple(provenance))
    except (GSTContractError, KeyError, sqlite3.Error, TypeError, ValueError, OverflowError, UnicodeError):
        return GSTContext("CACHE_MISS", domain_id, action_key, None, None, DIGEST_VERSION, "DIGEST_RECOMPUTATION_FAILED", narrative, tuple(provenance))


def request_gst(
    conn: sqlite3.Connection,
    *,
    domain_id: str,
    action_key: str,
    narrative: Mapping[str, Any] | None = None,
    provenance: Sequence[Mapping[str, Any]] = (),
    search_provider: GoogleSearchProvider | None = None,
) -> GSTContext:
    """Lookup first, then optionally expose sourced taxonomy candidates on miss.

    Search enrichment is returned separately in ``GSTContext`` only in a later
    contract revision; V1 deliberately does not issue a network request here.
    The provider is accepted as an injection seam and never invoked until its
    result payload has an owner-approved GST wire schema.
    """
    del search_provider
    return lookup_loop(conn, domain_id=domain_id, action_key=action_key, narrative=narrative, provenance=provenance)


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
        "domain_id": context.domain_id,
        "canonical_action_key": context.action_key,
        "known_loop": None,
        "cache_miss": True,
        "reason": context.miss_reason,
        "required_invariants": ["actor", "action", "object_or_tool", "registered_modality_operator"],
        "persist_result": False,
    }
