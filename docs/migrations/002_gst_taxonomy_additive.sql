-- DRAFT additive migration for GST taxonomy and contribution records.
-- Not applied to the T.O.T.E-loops database. Requires review and build_db.py integration.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS taxonomy_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL CHECK (node_type IN ('DOMAIN','SUBDOMAIN','SUB_SUBDOMAIN','FUNCTION','TECHNIQUE')),
    canonical_label TEXT NOT NULL CHECK (length(trim(canonical_label)) > 0),
    normalized_label TEXT NOT NULL CHECK (length(trim(normalized_label)) > 0),
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'CANDIDATE' CHECK (status IN ('CANDIDATE','ACTIVE','RETIRED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_type_label ON taxonomy_nodes(node_type, normalized_label);

CREATE TABLE IF NOT EXISTS taxonomy_edges (
    parent_node_id TEXT NOT NULL REFERENCES taxonomy_nodes(node_id) ON DELETE CASCADE,
    child_node_id TEXT NOT NULL REFERENCES taxonomy_nodes(node_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('CONTAINS','COMMONALITY')),
    source_id TEXT REFERENCES taxonomy_sources(source_id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (parent_node_id, child_node_id, relation_type),
    CHECK (parent_node_id <> child_node_id)
);
CREATE INDEX IF NOT EXISTS idx_taxonomy_edges_child ON taxonomy_edges(child_node_id, relation_type);

CREATE TABLE IF NOT EXISTS taxonomy_sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN ('GOOGLE_RESULT','HOW_TO','HUMAN_SUBMISSION','SEED_DATASET','OTHER')),
    source_url TEXT,
    title TEXT NOT NULL DEFAULT '',
    search_query TEXT NOT NULL DEFAULT '',
    retrieved_at TEXT,
    content_sha256 TEXT CHECK (content_sha256 IS NULL OR (length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*')),
    rights_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_taxonomy_sources_type ON taxonomy_sources(source_type);

CREATE TABLE IF NOT EXISTS taxonomy_node_sources (
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(node_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES taxonomy_sources(source_id) ON DELETE RESTRICT,
    evidence_note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (node_id, source_id)
);

CREATE TABLE IF NOT EXISTS loop_taxonomy (
    loop_id TEXT NOT NULL REFERENCES tote_loops(loop_id) ON DELETE CASCADE,
    node_id TEXT NOT NULL REFERENCES taxonomy_nodes(node_id) ON DELETE RESTRICT,
    relationship_role TEXT NOT NULL CHECK (relationship_role IN ('DOMAIN','SUBDOMAIN','SUB_SUBDOMAIN','FUNCTION','TECHNIQUE')),
    PRIMARY KEY (loop_id, node_id, relationship_role)
);
CREATE INDEX IF NOT EXISTS idx_loop_taxonomy_node ON loop_taxonomy(node_id, relationship_role);

CREATE TABLE IF NOT EXISTS tote_loop_elements (
    loop_id TEXT NOT NULL REFERENCES tote_loops(loop_id) ON DELETE CASCADE,
    element_role TEXT NOT NULL CHECK (element_role IN ('ACTOR','ACTION','OBJECT','TOOL')),
    element_index INTEGER NOT NULL CHECK (element_index >= 0),
    element_text TEXT NOT NULL CHECK (length(trim(element_text)) > 0),
    normalized_key TEXT,
    step_index INTEGER,
    source_id TEXT REFERENCES taxonomy_sources(source_id) ON DELETE RESTRICT,
    PRIMARY KEY (loop_id, element_role, element_index),
    FOREIGN KEY (loop_id, step_index) REFERENCES tote_steps(loop_id, step_index) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_loop_elements_match ON tote_loop_elements(element_role, normalized_key, loop_id);

CREATE TABLE IF NOT EXISTS loop_sources (
    loop_id TEXT NOT NULL REFERENCES tote_loops(loop_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES taxonomy_sources(source_id) ON DELETE RESTRICT,
    source_role TEXT NOT NULL CHECK (source_role IN ('HOW_TO_BASIS','HUMAN_SUBMISSION','TAXONOMY_EVIDENCE','SEED_PROVENANCE','OTHER')),
    PRIMARY KEY (loop_id, source_id, source_role)
);

CREATE TABLE IF NOT EXISTS loop_admission (
    loop_id TEXT PRIMARY KEY REFERENCES tote_loops(loop_id) ON DELETE CASCADE,
    origin TEXT NOT NULL CHECK (origin IN ('SEED','HOW_TO_EXTRACTED','HUMAN_AUTHORED','OTHER')),
    human_review_status TEXT NOT NULL DEFAULT 'NOT_REQUIRED' CHECK (human_review_status IN ('NOT_REQUIRED','PENDING','APPROVED','REJECTED')),
    admission_status TEXT NOT NULL DEFAULT 'CANDIDATE' CHECK (admission_status IN ('CANDIDATE','ADMITTED','REJECTED','RETIRED')),
    contributor_ref TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loop_human_reviews (
    review_id TEXT PRIMARY KEY,
    loop_id TEXT NOT NULL REFERENCES tote_loops(loop_id) ON DELETE CASCADE,
    source_id TEXT REFERENCES taxonomy_sources(source_id) ON DELETE RESTRICT,
    reviewer_ref TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('APPROVED','REJECTED')),
    review_note TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_loop_human_reviews_loop ON loop_human_reviews(loop_id, reviewed_at);

CREATE TABLE IF NOT EXISTS loop_validation_runs (
    validation_id TEXT PRIMARY KEY,
    loop_id TEXT NOT NULL REFERENCES tote_loops(loop_id) ON DELETE CASCADE,
    validator_version TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('PASS','FAIL','ERROR')),
    checks_json TEXT NOT NULL,
    loop_sha256 TEXT NOT NULL CHECK (length(loop_sha256) = 64 AND loop_sha256 NOT GLOB '*[^0-9a-f]*'),
    validated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_loop_validation_latest ON loop_validation_runs(loop_id, validated_at);

-- Enforce valid immediate hierarchy transitions and prevent containment cycles.
CREATE TRIGGER IF NOT EXISTS trg_taxonomy_edges_validate_insert
BEFORE INSERT ON taxonomy_edges
BEGIN
    SELECT CASE WHEN NEW.relation_type = 'CONTAINS' AND NOT EXISTS (
        SELECT 1
        FROM taxonomy_nodes p JOIN taxonomy_nodes c
        WHERE p.node_id = NEW.parent_node_id AND c.node_id = NEW.child_node_id
          AND ((p.node_type = 'DOMAIN' AND c.node_type = 'SUBDOMAIN')
            OR (p.node_type = 'SUBDOMAIN' AND c.node_type = 'SUB_SUBDOMAIN')
            OR (p.node_type = 'SUB_SUBDOMAIN' AND c.node_type = 'FUNCTION')
            OR (p.node_type = 'FUNCTION' AND c.node_type = 'TECHNIQUE'))
    ) THEN RAISE(ABORT, 'invalid taxonomy hierarchy level transition') END;
    SELECT CASE WHEN NEW.relation_type = 'CONTAINS' AND EXISTS (
        WITH RECURSIVE descendants(node_id) AS (
            SELECT child_node_id FROM taxonomy_edges
            WHERE parent_node_id = NEW.child_node_id AND relation_type = 'CONTAINS'
            UNION
            SELECT e.child_node_id FROM taxonomy_edges e
            JOIN descendants d ON e.parent_node_id = d.node_id
            WHERE e.relation_type = 'CONTAINS'
        )
        SELECT 1 FROM descendants WHERE node_id = NEW.parent_node_id
    ) THEN RAISE(ABORT, 'taxonomy containment cycle') END;
END;

-- Require loop taxonomy roles to match node types.
CREATE TRIGGER IF NOT EXISTS trg_loop_taxonomy_role_insert
BEFORE INSERT ON loop_taxonomy
WHEN NOT EXISTS (SELECT 1 FROM taxonomy_nodes n WHERE n.node_id = NEW.node_id AND n.node_type = NEW.relationship_role)
BEGIN
    SELECT RAISE(ABORT, 'loop taxonomy role does not match taxonomy node type');
END;

-- Admission requires a passing automatic validation record; how-to-derived loops also require human review.
CREATE TRIGGER IF NOT EXISTS trg_loop_admission_validate_insert
BEFORE INSERT ON loop_admission
WHEN NEW.admission_status = 'ADMITTED' AND (
    NOT EXISTS (SELECT 1 FROM loop_validation_runs v WHERE v.loop_id = NEW.loop_id AND v.result = 'PASS')
    OR (NEW.origin = 'HOW_TO_EXTRACTED' AND NEW.human_review_status <> 'APPROVED')
)
BEGIN
    SELECT RAISE(ABORT, 'admission requires passing automatic validation and required human review');
END;

CREATE TRIGGER IF NOT EXISTS trg_loop_admission_validate_update
BEFORE UPDATE OF admission_status, origin, human_review_status ON loop_admission
WHEN NEW.admission_status = 'ADMITTED' AND (
    NOT EXISTS (SELECT 1 FROM loop_validation_runs v WHERE v.loop_id = NEW.loop_id AND v.result = 'PASS')
    OR (NEW.origin = 'HOW_TO_EXTRACTED' AND NEW.human_review_status <> 'APPROVED')
)
BEGIN
    SELECT RAISE(ABORT, 'admission requires passing automatic validation and required human review');
END;

-- The application validator must recompute the loop digest before each admission.
CREATE VIEW IF NOT EXISTS gst_loop_invariant_summary AS
SELECT
    l.loop_id,
    EXISTS (SELECT 1 FROM tote_loop_elements e WHERE e.loop_id = l.loop_id AND e.element_role = 'ACTOR') AS has_actor,
    EXISTS (SELECT 1 FROM tote_loop_elements e WHERE e.loop_id = l.loop_id AND e.element_role = 'ACTION') AS has_action,
    (EXISTS (SELECT 1 FROM tote_loop_elements e WHERE e.loop_id = l.loop_id AND e.element_role = 'OBJECT')
      OR EXISTS (SELECT 1 FROM tote_loop_elements e WHERE e.loop_id = l.loop_id AND e.element_role = 'TOOL')) AS has_object_or_tool,
    EXISTS (SELECT 1 FROM tote_steps s WHERE s.loop_id = l.loop_id AND s.operator_id IS NOT NULL) AS has_modality,
    EXISTS (SELECT 1 FROM tote_steps s WHERE s.loop_id = l.loop_id AND s.phase = 'EXIT') AS has_exit_step,
    l.max_iterations
FROM tote_loops l;
