import sqlite3
import unittest


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


SCHEMA_VERSION = "fixture-schema-v1"


def database(*, origin="SEED", review=True, admission_status="ADMITTED", verified_digest=None, verified_version=DIGEST_VERSION):
    conn = sqlite3.connect(":memory:")
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
    digest = loop_digest(conn, "l1", schema_version=SCHEMA_VERSION)
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
        initial = loop_digest(conn, "l1", schema_version=SCHEMA_VERSION)
        self.assertEqual(initial, loop_digest(conn, "l1", schema_version=SCHEMA_VERSION))
        conn.execute("UPDATE tote_steps SET plain_text='repair different widget' WHERE loop_id='l1' AND step_index=1")
        self.assertNotEqual(loop_digest(conn, "l1", schema_version=SCHEMA_VERSION), initial)


    def test_lookup_requires_latest_matching_validation_not_admission_status(self):
        conn = database()
        ctx = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
        self.assertEqual(ctx.status, "HIT")
        self.assertEqual(ctx.loop["steps"][0]["step_index"], 0)

        conn.execute("UPDATE tote_steps SET plain_text='changed' WHERE loop_id='l1' AND step_index=1")
        new_digest = loop_digest(conn, "l1", schema_version=SCHEMA_VERSION)
        conn.execute("UPDATE loop_admission SET verified_loop_sha256=? WHERE loop_id='l1'", (new_digest,))
        stale = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
        self.assertEqual(stale.status, "CACHE_MISS")
        self.assertEqual(stale.miss_reason, "LATEST_VALIDATION_DOES_NOT_MATCH")

    def test_candidate_and_rejected_admission_states_fail_closed(self):
        for state in ("CANDIDATE", "REJECTED"):
            with self.subTest(state=state):
                conn = database(admission_status=state)
                result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "NOT_ADMITTED")

    def test_stale_admission_digest_or_version_fails_closed(self):
        cases = (("00" * 32, DIGEST_VERSION), (None, "NYCH-TOTE-LOOP-DIGEST-V0"))
        for digest, version in cases:
            with self.subTest(version=version, digest=bool(digest)):
                conn = database(verified_digest=digest, verified_version=version)
                result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "ADMISSION_DIGEST_DOES_NOT_MATCH")


    def test_latest_approved_review_is_required_for_every_origin(self):
        for origin in ("SEED", "HOW_TO_EXTRACTED", "OTHER", "UNKNOWN_ORIGIN"):
            with self.subTest(origin=origin):
                conn = database(origin=origin, review=False)
                result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH")

        # Changing origin cannot bypass a missing review.
        conn = database(origin="HOW_TO_EXTRACTED", review=False)
        conn.execute("UPDATE loop_admission SET origin='SEED' WHERE loop_id='l1'")
        conn.commit()
        self.assertEqual(
            lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION).miss_reason,
            "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH",
        )

    def test_latest_rejected_human_review_invalidates_earlier_approval(self):
        for origin in ("HOW_TO_EXTRACTED", "OTHER", "UNKNOWN_ORIGIN"):
            with self.subTest(origin=origin):
                conn = database(origin=origin)
                digest = loop_digest(conn, "l1", schema_version=SCHEMA_VERSION)
                conn.execute(
                    "INSERT INTO loop_human_reviews VALUES ('r2','l1','reviewer',?,?, 'REJECTED','2026-02-01T00:00:00Z')",
                    (digest, DIGEST_VERSION),
                )
                result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "LATEST_HUMAN_REVIEW_DOES_NOT_MATCH")

    def test_ambiguous_exact_match_fails_closed(self):
        conn = database()
        conn.execute("INSERT INTO tote_loops VALUES ('l2','Repair 2','Maintenance','repair object','is broken','works',2,'CANONICAL')")
        conn.execute("INSERT INTO tote_loop_elements VALUES ('l2','ACTION',0,'repair widget','repair widget',1,NULL)")
        result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
        self.assertEqual(result.status, "CACHE_MISS")
        self.assertEqual(result.miss_reason, "AMBIGUOUS_EXACT_MATCH")

    def test_partial_migration_fails_closed(self):
        conn = database()
        conn.execute("DROP TABLE loop_human_reviews")
        result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
        self.assertEqual(result.status, "CACHE_MISS")
        self.assertEqual(result.miss_reason, "VALIDATION_SCHEMA_UNAVAILABLE")

    def test_each_canonical_payload_table_is_required(self):
        for table in sorted(REQUIRED_PAYLOAD_TABLES):
            with self.subTest(table=table):
                conn = database()
                conn.execute(f'DROP TABLE "{table}"')
                result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
                self.assertEqual(result.status, "CACHE_MISS")

    def test_digest_and_utf8_decode_failures_fail_closed(self):
        for mutation in (
            "UPDATE tote_loops SET objective=X'FF' WHERE loop_id='l1'",
            "UPDATE tote_loops SET objective=CAST(X'80' AS TEXT) WHERE loop_id='l1'",
        ):
            with self.subTest(mutation=mutation):
                conn = database()
                conn.execute(mutation)
                result = lookup_loop(conn, domain="Maintenance", action="repair widget", schema_version=SCHEMA_VERSION)
                self.assertEqual(result.status, "CACHE_MISS")
                self.assertEqual(result.miss_reason, "DIGEST_RECOMPUTATION_FAILED")


    def test_cache_miss_handoff_has_b6_invariants_and_no_writeback(self):
        conn = database()
        miss = lookup_loop(conn, domain="Other", action="unseen action", schema_version=SCHEMA_VERSION)
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


    def test_schema_version_must_be_explicit(self):
        conn = database()
        with self.assertRaises(ValueError):
            loop_digest(conn, "l1", schema_version=" ")
