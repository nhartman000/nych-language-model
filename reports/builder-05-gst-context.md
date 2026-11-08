# Builder 5 Candidate Build Report — GST Context

Status: implementation candidate; awaiting independent Inspector review. No self-approval.

## Delivered

- `src/nych_language_model/pipeline/gst_context.py`: read-only SQLite adapter, literal exact domain/action lookup, request-scoped GST payload, canonical `NYCH-TOTE-LOOP-DIGEST-V1` recomputation, latest PASS validation and required latest human-review checks, explicit B6 cache-miss handoff, Google search provider protocol with provenance-bearing candidates, and a how-to loop wrapper that remains `PENDING_HUMAN_REVIEW`.
- `_verified_hit()` requires `ADMITTED` plus matching stored digest/version, and also checks the latest PASS validation and any required latest human review against a freshly recomputed digest.
- Lookup selection, digest recomputation, verification, and returned GST payload assembly run inside one SQLite savepoint/read snapshot.
- Canonical digest assembly requires every base and proposal payload table; any missing canonical table fails closed.
- Origin policy follows the approved admission design: `HUMAN_AUTHORED` requires matching admission and latest PASS validation, with no separate review; `HOW_TO_EXTRACTED` additionally requires latest matching APPROVED human review. `SEED`, `OTHER`, and unknown origins fail closed until their policy is approved.
- `tests/test_gst_context.py`: thirteen focused `unittest` checks including each missing canonical table, supported/unsupported origin review gates, stale admission digest/version, rejected latest review, ambiguous matches, partial migration, digest and UTF-8 decode failures.

Raw prompts are not accepted or stored. The module performs no database writes and does not make a live search request. Search results and extracted loops remain in-memory candidates.

## Checks

`PYTHONPATH=src python -m unittest tests.test_gst_context -v` — 13 focused tests passed.

`PYTHONPATH=src python -m unittest discover -s tests -v` — 33 tests passed (13 Builder 5 plus 20 existing tests).

## Contract boundaries and blockers

- The reviewed draft does not define a database schema-version source. The trusted caller must supply `schema_version` into the canonical payload; this candidate fails closed on an empty value.
- Deterministic action matching is still an owner-open decision. The candidate uses literal equality on `tote_loop_elements.element_text` and `tote_loops.domain`, with ambiguity returning a cache miss; it performs no normalization or fuzzy correction.
- GST wire schema, search-result acceptance/ranking, query generation, taxonomy extraction, and candidate presentation remain open. The adapter exposes provenance-bearing search candidates but does not infer or admit taxonomy nodes.
- The current base TOTE schema lacks validation/review and action-element tables. Without the reviewed additive migration and its linked records, entries are cache misses. Migration is not applied and the T.O.T.E-Loops repository/schema is untouched.

## Artifact digests

Generated after implementation; SHA-256 covers exact UTF-8 file bytes.

- `src/nych_language_model/pipeline/gst_context.py`: `c5901c00aa06d6d798f1f5e685702edc633584c404eef4105e7c2a2c7e74c229`
- `tests/test_gst_context.py`: `175c4a7450f950b62244163b6e8989bc6aa24806a45dac358da0ade9755c7b0e`
