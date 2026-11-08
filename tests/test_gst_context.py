import sqlite3
import unittest
import json
from pathlib import Path


from nych_language_model.pipeline.gst_context import (
    DIGEST_VERSION,
    REQUIRED_PAYLOAD_TABLES,
    SearchResult,
    cache_miss_handoff,
    loop_digest,
    lookup_loop,
    route_how_to_candidate,
    search_taxonomy_candidates,
)


def assert_schema(instance, schema):
    """Focused JSON Schema subset used here; avoids a runtime dependency."""
    if "const" in schema and instance != schema["const"]:
        raise AssertionError(f"expected const {schema['const']!r}, got {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise AssertionError(f"value {instance!r} is outside enum")
    if "oneOf" in schema:
        matches = 0
        for option in schema["oneOf"]:
            try:
                assert_schema(instance, option)
                matches += 1
            except AssertionError:
                pass
        if matches != 1:
            raise AssertionError("oneOf must match exactly one branch")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        checks = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
                  "string": lambda v: isinstance(v, str), "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
                  "null": lambda v: v is None}
        if not any(checks[t](instance) for t in types):
            raise AssertionError(f"wrong type for {instance!r}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                raise AssertionError(f"missing required property {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(instance) - set(properties):
            raise AssertionError("additional properties are forbidden")
        for key, value in instance.items():
            if key in properties:
                assert_schema(value, properties[key])
    if isinstance(instance, list) and "items" in schema:
        for value in instance:
            assert_schema(value, schema["items"])
    if isinstance(instance, str):
        import re
        if len(instance) < schema.get("minLength", 0):
            raise AssertionError("string shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise AssertionError("string does not match pattern")
    if isinstance(instance, int) and not isinstance(instance, bool) and instance < schema.get("minimum", instance):
        raise AssertionError("integer below minimum")



def database(*, origin="HUMAN_AUTHORED", review=True, admission_status="ADMITTED", verified_digest=None, verified_version=DIGEST_VERSION):
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA user_version=2")
    conn.executescript(
        """
        CREATE TABLE modality_operators(operator_id TEXT PRIMARY KEY, symbol TEXT, canonical_name TEXT, definition TEXT, evidence_channel TEXT, may_assert_action INTEGER);
        CREATE TABLE gestalts(gestalt_id TEXT PRIMARY KEY, glyph TEXT, lexical_form TEXT, sense TEXT, route TEXT, recoverability_note TEXT);
        CREATE TABLE tote_loops(loop_id TEXT PRIMARY KEY, name TEXT, domain TEXT, objective TEXT, initial_test TEXT, exit_predicate TEXT, max_iterations INTEGER, epistemic_status TEXT);
        CREATE TABLE tote_steps(loop_id TEXT, step_index INTEGER, phase TEXT, operator_id TEXT, plain_text TEXT, nych_text TEXT, proposition_kind TEXT, provenance TEXT, next_on_match INTEGER, next_on_mismatch INTEGER, PRIMARY KEY(loop_id,step_index));
        CREATE TABLE loop_gestalts(loop_id TEXT, gestalt_id TEXT, role TEXT, PRIMARY KEY(loop_id,gestalt_id,role));
        CREATE TABLE taxonomy_nodes(node_id TEXT PRIMARY KEY,node_type TEXT,canonical_label TEXT,normalized_label TEXT,description TEXT,status TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE taxonomy_edges(parent_node_id TEXT,child_node_id TEXT,relation_type TEXT,source_id TEXT,created_at TEXT);
        CREATE TABLE taxonomy_sources(source_id TEXT PRIMARY KEY,source_type TEXT,source_url TEXT,title TEXT,search_query TEXT,retrieved_at TEXT,content_sha256 TEXT,rights_note TEXT,created_at TEXT);
        CREATE TABLE taxonomy_node_sources(node_id TEXT,source_id TEXT,evidence_note TEXT);
        CREATE TABLE loop_taxonomy(loop_id TEXT,node_id TEXT,relationship_role TEXT);
        CREATE TABLE tote_loop_elements(loop_id TEXT,element_role TEXT,element_index INTEGER,element_text TEXT,normalized_key TEXT,step_index INTEGER,source_id TEXT);
        CREATE TABLE loop_sources(loop_id TEXT,source_id TEXT,source_role TEXT);
        CREATE TABLE loop_admission(loop_id TEXT,origin TEXT,admission_status TEXT,verified_loop_sha256 TEXT,verified_digest_version TEXT);
        CREATE TABLE loop_validation_runs(validation_id TEXT,loop_id TEXT,validator_version TEXT,result TEXT,checks_json TEXT,loop_sha256 TEXT,digest_version TEXT,validated_at TEXT);
        CREATE TABLE loop_human_reviews(review_id TEXT,loop_id TEXT,reviewer_ref TEXT,loop_sha256 TEXT,digest_version TEXT,outcome TEXT,reviewed_at TEXT);
        """
    )
    conn.execute("INSERT INTO modality_operators VALUES ('observe','👀','observe','see evidence','external',0)")
    conn.execute("INSERT INTO gestalts VALUES ('g1','🔧','repair','repair action','G','literal')")
    conn.execute("INSERT INTO tote_loops VALUES ('l1','Repair','Maintenance','repair object','is broken','works',2,'CANONICAL')")
    # Deliberately insert steps out of order; digest ordering is by step_index.
    conn.execute("INSERT INTO tote_steps VALUES ('l1',1,'OPERATE','observe','repair widget','🔧 repair widget','EXECUTED','explicit',2,2)")
    conn.execute("INSERT INTO tote_steps VALUES ('l1',0,'TEST','observe','inspect widget','👀 inspect widget','OBSERVED','explicit',1,1)")
    conn.execute("INSERT INTO loop_gestalts VALUES ('l1','g1','action')")
    conn.executemany(
        "INSERT INTO tote_loop_elements VALUES ('l1',?,?,?,?,?,NULL)",
        [("ACTOR", 0, "technician", "technician", None),
         ("ACTION", 0, "repair widget", "repair widget", 1),
         ("OBJECT", 0, "widget", "widget", 1)],
    )
    conn.execute("INSERT INTO taxonomy_nodes VALUES ('d','DOMAIN','Maintenance','maintenance','Repairs','ACTIVE','t0','t1')")
    conn.execute("INSERT INTO loop_taxonomy VALUES ('l1','d','DOMAIN')")
    conn.commit()
    digest = loop_digest(conn, "l1", )
    conn.execute(
        "INSERT INTO loop_admission VALUES ('l1',?,?,?,?)",
        (origin, admission_status, verified_digest if verified_digest is not None else digest, verified_version),
    )
    conn.execute("INSERT INTO loop_validation_runs VALUES ('v1','l1','validator-1','PASS','{}',?,?, '2026-01-01T00:00:00Z')", (digest, DIGEST_VERSION))
    if review:
        conn.execute("INSERT INTO loop_human_reviews VALUES ('r1','l1','reviewer',?,?, 'APPROVED','2026-01-01T00:00:00Z')", (digest, DIGEST_VERSION))
    conn.commit()
    return conn


class GSTContextTests(unittest.TestCase):
    def test_digest_is_deterministic_and_sensitive_to_semantic_change(self):
        conn = database()
        initial = loop_digest(conn, "l1", )
        self.assertEqual(initial, loop_digest(conn, "l1", ))
        conn.execute("UPDATE tote_steps SET plain_text='repair different widget' WHERE loop_id='l1' AND step_index=1")
        self.assertNotEqual(loop_digest(conn, "l1", ), initial)


    def test_lookup_requires_latest_matching_validation_not_admission_status(self):
        conn = database()
        ctx = lookup_loop(conn, domain_id="d", action_key="repair widget", )
        self.assertEqual(ctx.status, "HIT")
        self.assertEqual(ctx.loop["steps"][0]["step_index"], 0)

        conn.execute("UPDATE tote_steps SET plain_text='changed' WHERE loop_id='l1' AND step_index=1")
        new_digest = loop_digest(conn, "l1", )
        conn.execute("UPDATE loop_admission SET verified_loop_sha256=? WHERE loop_id='l1'", (new_digest,))
        stale = lookup_loop(conn, domain_id="d", action_key="repair widget", )
        self.assertEqual(stale.status, "CACHE_MISS")
        self.assertEqual(stale.miss_reason, "LATEST_VALIDATION_DOES_NOT_MATCH")

    def test_candidate_and_rejected_admission_states_fail_closed(self):
        for state in ("CANDIDATE", "REJECTED"):
            with self.subTest(state=state):
                conn = database(admission_status=state)
                result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "NOT_ADMITTED")

    def test_stale_admission_digest_or_version_fails_closed(self):
        cases = (("00" * 32, DIGEST_VERSION), (None, "NYCH-TOTE-LOOP-DIGEST-V0"))
        for digest, version in cases:
            with self.subTest(version=version, digest=bool(digest)):
                conn = database(verified_digest=digest, verified_version=version)
                result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "ADMISSION_DIGEST_DOES_NOT_MATCH")


    def test_origin_specific_review_policy(self):
        human = database(origin="HUMAN_AUTHORED", review=False)
        self.assertEqual(
            lookup_loop(human, domain_id="d", action_key="repair widget", ).status,
            "HIT",
        )

        how_to_missing = database(origin="HOW_TO_EXTRACTED", review=False)
        missing_result = lookup_loop(how_to_missing, domain_id="d", action_key="repair widget", )
        self.assertEqual(missing_result.status, "CACHE_MISS")
        self.assertEqual(missing_result.miss_reason, "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH")
        how_to_approved = database(origin="HOW_TO_EXTRACTED", review=True)
        self.assertEqual(
            lookup_loop(how_to_approved, domain_id="d", action_key="repair widget", ).status,
            "HIT",
        )

        for origin in ("SEED", "OTHER", "UNKNOWN_ORIGIN"):
            for has_review in (False, True):
                with self.subTest(origin=origin, has_review=has_review):
                    conn = database(origin=origin, review=has_review)
                    result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
                    self.assertEqual(result.status, "CACHE_MISS")
                    self.assertEqual(result.miss_reason, "UNSUPPORTED_ORIGIN")

    def test_latest_rejected_human_review_invalidates_earlier_approval(self):
        for origin in ("HOW_TO_EXTRACTED",):
            with self.subTest(origin=origin):
                conn = database(origin=origin)
                digest = loop_digest(conn, "l1", )
                conn.execute(
                    "INSERT INTO loop_human_reviews VALUES ('r2','l1','reviewer',?,?, 'REJECTED','2026-02-01T00:00:00Z')",
                    (digest, DIGEST_VERSION),
                )
                result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH")

    def test_ambiguous_exact_match_fails_closed(self):
        conn = database()
        conn.execute("INSERT INTO tote_loops VALUES ('l2','Repair 2','Maintenance','repair object','is broken','works',2,'CANONICAL')")
        conn.execute("INSERT INTO tote_loop_elements VALUES ('l2','ACTION',0,'repair widget','repair widget',1,NULL)")
        conn.execute("INSERT INTO loop_taxonomy VALUES ('l2','d','DOMAIN')")
        result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
        self.assertEqual(result.status, "CACHE_MISS")
        self.assertEqual(result.miss_reason, "AMBIGUOUS_EXACT_MATCH")

    def test_partial_migration_fails_closed(self):
        conn = database()
        conn.execute("DROP TABLE loop_human_reviews")
        result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
        self.assertEqual(result.status, "CACHE_MISS")
        self.assertEqual(result.miss_reason, "VALIDATION_SCHEMA_UNAVAILABLE")

    def test_each_canonical_payload_table_is_required(self):
        for table in sorted(REQUIRED_PAYLOAD_TABLES):
            with self.subTest(table=table):
                conn = database()
                conn.execute(f'DROP TABLE "{table}"')
                result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
                self.assertEqual(result.status, "CACHE_MISS")

    def test_digest_and_utf8_decode_failures_fail_closed(self):
        for mutation in (
            "UPDATE tote_loops SET objective=X'FF' WHERE loop_id='l1'",
            "UPDATE tote_loops SET objective=CAST(X'80' AS TEXT) WHERE loop_id='l1'",
        ):
            with self.subTest(mutation=mutation):
                conn = database()
                conn.execute(mutation)
                result = lookup_loop(conn, domain_id="d", action_key="repair widget", )
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "DIGEST_RECOMPUTATION_FAILED")


    def test_cache_miss_handoff_has_b6_invariants_and_no_writeback(self):
        conn = database()
        miss = lookup_loop(conn, domain_id="missing", action_key="unseen action", )
        handoff = cache_miss_handoff(miss)
        self.assertEqual(handoff["target"], "B6_SYMBOL_SELECTION")
        self.assertIn("registered_modality_operator", handoff["required_invariants"])
        self.assertFalse(handoff["persist_result"])


    def test_taxonomy_search_results_keep_provenance_and_remain_candidates(self):
        class Provider:
            def search(self, query):
                return [SearchResult("https://example.test", "Guide", "snippet", query, "2026-01-01T00:00:00Z")]

        candidates = search_taxonomy_candidates(domain="Maintenance", queries=["maintenance repair"], provider=Provider())
        self.assertEqual(candidates[0].status, "CANDIDATE_HUMAN_REVIEW")
        self.assertEqual(candidates[0].result.url, "https://example.test")
        loop_candidate = route_how_to_candidate(
            domain="Maintenance", technique="inspection", candidate={"action": "repair"}, sources=[candidates[0].result]
        )
        self.assertEqual(loop_candidate.review_status, "PENDING_HUMAN_REVIEW")

    def test_exact_canonical_domain_and_action_key_matching(self):
        conn = database()
        self.assertEqual(lookup_loop(conn, domain_id="d", action_key="repair widget").status, "HIT")
        self.assertEqual(lookup_loop(conn, domain_id="wrong", action_key="repair widget").miss_reason, "NO_EXACT_MATCH")
        self.assertEqual(lookup_loop(conn, domain_id="d", action_key="Repair widget").miss_reason, "NO_EXACT_MATCH")

    def test_gst_json_contract_preserves_narrative_and_span_provenance(self):
        conn = database()
        narrative = {"perspective": "third", "tense": "past", "subject": "technician", "predicate": "repaired", "intervals": [{"kind": "RANGE", "start": "yesterday", "end": "today", "duration": None}]}
        provenance = ({"field": "narrative.subject", "source_digest": "a" * 64, "byte_start": 0, "byte_end": 10, "epistemic_status": "explicit"},)
        result = lookup_loop(conn, domain_id="d", action_key="repair widget", narrative=narrative, provenance=provenance).as_dict()
        schema = json.loads((Path(__file__).parents[1] / "schemas/gst-context-v1.schema.json").read_text())
        assert_schema(result, schema)
        self.assertEqual(result["narrative"], narrative)
        self.assertEqual(result["provenance"], list(provenance))
        self.assertEqual(result["integrity"]["schema_version"], 2)

    def test_malformed_narrative_and_provenance_rejected(self):
        conn = database()
        with self.assertRaises(ValueError):
            lookup_loop(conn, domain_id="d", action_key="repair widget", narrative={"prompt": "raw prompt"})
        with self.assertRaises(ValueError):
            lookup_loop(conn, domain_id="d", action_key="repair widget", provenance=({"raw_prompt": "secret"},))
        with self.assertRaises(ValueError):
            lookup_loop(conn, domain_id="d", action_key="repair widget", narrative={"perspective": None, "tense": None, "subject": None, "predicate": None, "intervals": [{"raw": "text"}]})


    def test_schema_version_comes_from_pragma_user_version(self):
        conn = database()
        conn.execute("PRAGMA user_version=1")
        with self.assertRaisesRegex(Exception, "unsupported TOTE schema version"):
            loop_digest(conn, "l1")
