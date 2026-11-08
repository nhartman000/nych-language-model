# GST Taxonomy and Contribution Schema Proposal — V1

## Status

Draft for owner review. Storage direction is approved: extend the existing TOTE SQLite database. This is a proposed additive model, not an applied migration. Preserve the current tables and deterministic JSON export until a reviewed migration and compatibility plan are approved.

Reference source: [`nhartman000/T.O.T.E-loops/schema.sql`](https://github.com/nhartman000/T.O.T.E-loops/blob/main/schema.sql). The current schema defines `modality_operators`, `gestalts`, `tote_loops`, `tote_steps`, and `loop_gestalts`.

## Proposed additive tables

| Table | Purpose | Key fields |
|---|---|---|
| `taxonomy_nodes` | Canonical domain hierarchy | `node_id`, `node_type` (`DOMAIN`, `SUBDOMAIN`, `SUB_SUBDOMAIN`, `FUNCTION`, `TECHNIQUE`), `canonical_label`, `normalized_label`, `description`, `status` |
| `taxonomy_edges` | Parent/child hierarchy and explicit cross-branch commonality | `parent_node_id`, `child_node_id`, `relation_type`; `CONTAINS` edges must follow the approved level order; commonality edges do not change hierarchy |
| `taxonomy_sources` | Search, how-to, seed, and human-submission provenance | `source_id`, `source_type`, `source_url`, `title`, `search_query`, `retrieved_at`, `content_sha256`, `rights_note` |
| `taxonomy_node_sources` | Evidence links for taxonomy nodes | `node_id`, `source_id`, `evidence_note` |
| `loop_taxonomy` | Connect reusable TOTE loops to domain and technique nodes | `loop_id`, `node_id`, `relationship_role` |
| `tote_step_roles` | Represent the required actor/action/object-or-tool elements without changing positional inserts into existing `tote_steps` | `loop_id`, `step_index`, `actor_text`, `action_text`, `object_tool_text`; modality continues to reference `modality_operators` through `tote_steps.operator_id` |
| `loop_admission` | Distinguish seed, extracted, and human-authored entries and their review/verification state | `loop_id`, `origin`, `admission_status`, `contributor_ref`, `human_review_ref` |
| `loop_validation_runs` | Auditable automatic checks | `validation_id`, `loop_id`, `validator_version`, `result`, `checks_json`, `loop_digest`, `validated_at` |

Use foreign keys and uniqueness constraints for identifiers and relationships. Search-result metadata and hashes should be retained; full source text need not be copied into the database. Existing `tote_loops.domain` and `tote_steps` remain readable during transition.

## Population and admission flow

1. B4 provides a domain identifier. B5 checks the local taxonomy and TOTE records.
2. If taxonomy is missing, Google search supplies candidate subdomains, sub-subdomains, functions, and techniques. Store source URL, query, retrieval time, and evidence/hash. The exact source-ranking and acceptance rule remains an owner decision.
3. How-to text may yield technique and TOTE-loop candidates. Keep these as candidates until a human validates them; retain source provenance.
4. The future web form looks up the hierarchy and technique, lets the contributor choose registered modality operators and enter loop action text (plus required actor/object-or-tool details), then records the submission as human-authored.
5. Run automatic structural and invariant checks. A passing check means the record conforms to the declared schema and NYCH/TOTE invariants; it does not prove every action description is factually correct. Record the validator version, individual check results, and digest.
6. A known action under a known domain is served by deterministic database lookup. On a miss, B6 resolves the missing selection during the first symbol-selection call under the invariant TOTE and modality rules. Do not persist a newly resolved entry until its admission/write policy is approved.

## Automatic verification checks

- Referential integrity and valid, acyclic `CONTAINS` hierarchy edges.
- Required hierarchy node types and loop-to-technique/domain links.
- At least one actor, action, object or tool, and valid registered modality operator for each admitted loop.
- Valid TOTE step phases and in-loop transition targets; an explicit exit predicate and bounded iteration count.
- Consistency among modality operator, proposition kind, and provenance; never promote intention/execution/prediction to observation.
- Required provenance and a stable content digest for extracted or search-derived records.
- Deterministic validation output tied to the exact loop digest.

How-to-derived candidates additionally require a human review record before canonical admission. Human-authored entries are labeled as such; automatic verification does not masquerade as human validation.

## Decisions still open

- Exact SQL migration layout and schema version strategy.
- Whether taxonomy nodes are admitted directly from search or remain candidates until an acceptance rule passes.
- Canonical normalization and deterministic action matching key.
- Whether action/role fields belong in a dedicated relation or a revised `tote_steps` interface in a later schema version.
- Contributor identity and privacy model for the web interface.
- Versioned validator rules, failure behavior, and who may admit a passing entry.
- Runtime adapter/API endpoint and database write permissions.

## Compatibility requirement

Do not change `schema.sql`, `src/build_db.py`, current seed data, or exported field meanings until this proposal is reviewed, an additive migration is prepared, and compatibility behavior is specified. The existing SQLite schema remains the reference source for current records.
