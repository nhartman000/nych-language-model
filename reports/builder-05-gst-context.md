# Builder 5 GST Context — V2 Candidate

Status: awaiting independent inspection on branch `builder-05/gst-context-v2`. The separate TOTE migration draft sets `PRAGMA user_version = 2`; no edits were made to the T.O.T.E-loops repo by this candidate.

## Approved contract implemented

- Schema version is read from SQLite `PRAGMA user_version`; B5 accepts version 2 only and includes the integer in the canonical digest payload.
- Lookup accepts a canonical taxonomy `domain_id` and exact `action_key`, matching `loop_taxonomy.node_id` and `tote_loop_elements.normalized_key`; ambiguous results fail as cache misses.
- GST emits versioned JSON matching `schemas/gst-context-v1.schema.json`: request keys, taxonomy, TOTE data, upstream narrative envelope, provenance spans, digest integrity and miss reason.
- Narrative values are passed through from upstream; B5 does not infer them. Runtime validation requires the declared fields and interval shape. Provenance fields require source digest and half-open byte offsets; offsets are carried metadata only, not verified against source bytes because those bytes are not present.
- Search remains a provider interface that returns sourced, unapproved candidates. No live search/network call or credentials are used.

Integrity gates remain: required canonical payload tables; one read snapshot; recomputed digest; `ADMITTED`; latest matching PASS; `HUMAN_AUTHORED` requires structural/invariant validation; `HOW_TO_EXTRACTED` additionally requires latest matching human approval; other origins fail closed. Raw prompts are not persisted.

## Validation

- `PYTHONPATH=src python -m unittest discover -s tests -v` — 36 tests passed.
- `python -m json.tool schemas/gst-context-v1.schema.json` — valid JSON.
- Focused schema validator in tests checks the actual emitted GST object against the declared schema subset; no runtime validation dependency added.
- `git diff --check` — clean.

## Remaining boundaries

- Migration 002 is still unapplied to T.O.T.E-loops in this branch; the current production database remains legacy and B5 fails closed until version 2 is integrated.
- Upstream B4 must supply canonical domain IDs, action keys, narrative fields and provenance records.
- Live Google integration, search ranking/acceptance, taxonomy extraction/admission, and end-to-end B4→B5→B6 wiring are not implemented.
- Byte offsets are validated structurally but cannot be checked against the source text here.
- GST version is V1; contract changes require a new schema version.

## Artifact SHA-256

- `gst_context.py`: `d538a4d8633e46d87ecf4af556d872226803ab7d393a2575b763000fb37a3119`
- `test_gst_context.py`: `0597d84c9a44fe637435f63a98035c3e37f4cebf2775218bb3b17518fe47a622`
- `gst-context-v1.schema.json`: `07d95d2f639c54ba3b1337903c49f8eba252dd7c3a1e8101d3ed52375b4f5662`
