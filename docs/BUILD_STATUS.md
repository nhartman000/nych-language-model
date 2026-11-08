# Build status

- B1 Ingest: candidate source added; owner policy approved; independent inspection pending.
- B3 Trace identity: bounded implementation PASS; Inspector 3 independently verified 14/14 focused tests; integration checks remain.
- B2 and B4–B11: implementation/inspection remain gated by module contracts.
- New module separation approved: B5 GST Context Assembly and deterministic action/domain lookup; B6 NYCH symbolization; downstream modules renumbered through B11 Training/Evaluation.
- GST architecture: TOTE schema source is identified at `nhartman000/T.O.T.E-loops/schema.sql`; it defines five tables and a SQLite/JSON build path. Current schema lacks normalized hierarchy/action/actor/object fields. Approved architecture adds Google-search hierarchy enrichment with provenance, human validation for how-to-derived loops, and future human authoring with automatic invariant checks. Existing matching records are looked up deterministically; cache misses resolve during the first symbol-selection call. Runtime adapter, matching rule, schema mapping/extension, verifier suite, and write policy remain open.
- No new module implementation, database, corpus weights, or neural weights are claimed by this restructuring.
- Integration and GitSON wiring require independent Inspector PASS evidence and digest-bound host validation.
- Prompt privacy: raw text is memory-only; QSON and reports may record digest and metadata but never the prompt.
