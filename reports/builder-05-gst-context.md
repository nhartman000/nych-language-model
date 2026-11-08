# Builder 5 GST Context — V2 Candidate

Status: candidate for independent inspection on branch `builder-05/gst-context-v2`. The TOTE schema migration remains a draft on this branch; the T.O.T.E-loops repository change is being handled separately.

## Approved contract implemented

- Schema version is read from SQLite `PRAGMA user_version`; B5 accepts version 2 only and includes the integer in the canonical digest payload. Draft migration 002 sets `PRAGMA user_version = 2`.
- Lookup accepts a canonical taxonomy `domain_id` and exact `action_key`, matching `loop_taxonomy.node_id` and `tote_loop_elements.normalized_key`; ambiguous results fail as cache misses.
- GST emits versioned JSON matching `schemas/gst-context-v1.schema.json`: request keys, taxonomy, TOTE data, upstream narrative envelope, provenance spans, digest integrity and miss reason.
- Narrative values are passed through from upstream; B5 does not infer them. The input validator only accepts the declared fields and structured provenance with digest-bound half-open UTF-8 byte spans. It rejects raw-prompt fields.
- Search remains a provider interface that returns sourced, unapproved candidates. No live search/network call or credentials are used.

The previously reviewed integrity boundary remains: only exact canonical payload tables; read snapshot; recomputed digest; `ADMITTED`; latest matching PASS; `HUMAN_AUTHORED` requires structural/invariant validation; `HOW_TO_EXTRACTED` additionally requires latest matching human approval; other origins fail closed. Raw prompts are not persisted.

## Validation

- `PYTHONPATH=src python -m unittest discover -s tests -v` — 36 tests passed.
- `python -m json.tool schemas/gst-context-v1.schema.json` — valid JSON.
- `git diff --check` — clean.

## Remaining boundaries

- Migration 002 remains unapplied to T.O.T.E-loops in this branch; the production TOTE database remains legacy and B5 fails closed until its versioned migration is integrated.
- The caller/upstream B4 must produce canonical domain IDs, action keys, narrative fields and provenance spans.
- Live Google integration, search ranking/acceptance, taxonomy extraction/admission, and end-to-end B4→B5→B6 wiring are not implemented.
- GST version is V1; contract changes require a new schema version.

## Artifact SHA-256

- `gst_context.py`: `e4c48d7b22c1ab4faff3db7fe0168a4a8f571150142ee4cceaff520c3507ff06`
- `test_gst_context.py`: `2662b530d5d8fea724b821bec3ac1af9c1945dba0cb734b19c3d6f998b6eaab2`
- `gst-context-v1.schema.json`: `9de859f71fae8cf72a97a811de85e974f554cc053e70e7266f044026f55fad4e`
