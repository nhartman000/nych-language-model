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
| `tote_loop_elements` | Represent actor/action/object/tool elements without changing positional inserts into existing `tote_steps` | `loop_id`, `element_role`, `element_index`, `element_text`, optional `normalized_key`, optional `step_index`; modality continues to reference `modality_operators` through `tote_steps.operator_id` |
| `loop_sources` | Link loop records to source material and submissions | `loop_id`, `source_id`, `source_role` | 
| `loop_admission` | Distinguish seed, extracted, and human-authored entries and their review/verification state | `loop_id`, `origin`, `human_review_status`, `admission_status`, `contributor_ref`, `verified_loop_sha256`, `verified_digest_version` |
| `loop_human_reviews` | Human review record for how-to-derived loop candidates | `review_id`, `loop_id`, `source_id`, `reviewer_ref`, `loop_sha256`, `digest_version`, `outcome`, `review_note`, `reviewed_at` | 
| `loop_validation_runs` | Auditable automatic checks | `validation_id`, `loop_id`, `validator_version`, `result`, `checks_json`, `loop_sha256`, `digest_version`, `validated_at` |

Use foreign keys and uniqueness constraints for identifiers and relationships. Search-result metadata and hashes should be retained; full source text need not be copied into the database. Existing `tote_loops.domain` and `tote_steps` remain readable during transition.

## Population and admission flow

1. B4 provides a domain identifier. B5 checks the local taxonomy and TOTE records.
2. If taxonomy is missing, Google search supplies candidate subdomains, sub-subdomains, functions, and techniques. Store source URL, query, retrieval time, and evidence/hash. The exact source-ranking and acceptance rule remains an owner decision.
3. How-to text may yield technique and TOTE-loop candidates. Keep these as candidates until a human validates them; retain source provenance.
4. The future web form looks up the hierarchy and technique, lets the contributor choose registered modality operators and enter loop action text (plus required actor/object-or-tool details), then records the submission as human-authored.
5. Run automatic structural and invariant checks. A passing check means the record conforms to the declared schema and NYCH/TOTE invariants; it does not prove every action description is factually correct. The trusted B5 lookup/write service must recompute the versioned canonical digest on every hit and require it to match the latest PASS validation and any required human review; the status column alone is never a pass signal. Record the validator version, individual check results, and digest.
6. A known action under a known domain is served by deterministic database lookup. On a miss, B6 resolves the missing selection during the first symbol-selection call under the invariant TOTE and modality rules. Do not persist a newly resolved entry until its admission/write policy is approved.

## Canonical loop digest v1

Owner-approved B5 integrity rule: `admission_status` is advisory. The trusted runtime computes this digest again on every database hit and accepts the record only when the latest validation PASS and any required latest human approval match the current digest and digest version. A changed digest is a cache miss and requires revalidation; how-to-derived loops also require a new human approval for the changed digest.

- Digest version: `NYCH-TOTE-LOOP-DIGEST-V1`.
- Digest input prefix bytes: UTF-8 `NYCH-TOTE-LOOP-DIGEST\0v1\0`.
- Payload is a JSON object with `schema_version`, `loop`, `steps`, `elements`, `taxonomy`, `sources`, `loop_gestalts`, `gestalts`, and `modality_operators` sections.
- Include all `tote_loops` fields; all `tote_steps` fields sorted by `step_index`; all `tote_loop_elements` sorted by `(element_role, element_index)`; and all `loop_taxonomy` links sorted by `(relationship_role, node_id)`.
- Taxonomy payload includes linked taxonomy nodes, their full `CONTAINS` ancestor paths and edges, relevant `COMMONALITY` edges, and source associations/metadata. Sort rows by stable IDs and relationship keys.
- Include loop sources and their source metadata; linked `loop_gestalts` plus full referenced `gestalts` records; and all referenced `modality_operators` records. Include source URL/query/time/hash and rights metadata, never raw prompt text or copied how-to bodies.
- Exclude `loop_admission`, `loop_validation_runs`, `loop_human_reviews`, and generated timestamps unrelated to semantic source provenance.
- Serialize as UTF-8 JSON with object keys sorted lexicographically, compact separators `,` and `:`, `ensure_ascii=False`, `allow_nan=False`, no trailing newline, and no Unicode normalization. All arrays use the explicit stable ordering above.
- Compute lowercase full SHA-256 over `prefix || serialized_payload`; store both the 64-character digest and `digest_version` in validation/review/admission records.

The validator must expose the exact payload or a redacted deterministic digest report for independent reproduction. Golden fixtures must prove that reordering database rows leaves the digest unchanged and changing any included semantic/provenance field changes it.

## Automatic verification checks

- Referential integrity and valid, acyclic `CONTAINS` hierarchy edges.
- Required hierarchy node types and loop-to-technique/domain links.
- At least one actor, action, object or tool element, and valid registered modality operator for each admitted loop.
- Valid TOTE step phases and in-loop transition targets; an explicit exit predicate and bounded iteration count.
- Consistency among modality operator, proposition kind, and provenance; never promote intention/execution/prediction to observation.
- Required provenance and a stable content digest for extracted or search-derived records.
- Deterministic validation output tied to the exact loop digest.

How-to-derived candidates additionally require an approved human review record before canonical admission. Human-authored entries require a passing automatic validation record before admission; automatic verification does not masquerade as human validation. The migration's admission triggers require a PASS validation for the exact stored digest and an approved human-review record for how-to-derived loops. Content or linked-taxonomy changes invalidate prior admission. The runtime validator must recompute the loop digest before admission.

## Decisions still open

- Exact SQL migration layout and schema version strategy.
- Whether taxonomy nodes are admitted directly from search or remain candidates until an acceptance rule passes.
- Canonical normalization and deterministic action matching key.
- Whether action/role fields belong in a dedicated relation or a revised `tote_steps` interface in a later schema version.
- Contributor identity and privacy model for the web interface.
- Versioned validator rules, failure behavior, who may admit a passing entry.
- Runtime adapter/API endpoint and database write permissions.

## Compatibility requirement

Do not change `schema.sql`, `src/build_db.py`, current seed data, or exported field meanings until this proposal is reviewed, an additive migration is prepared, and compatibility behavior is specified. The existing SQLite schema remains the reference source for current records.
