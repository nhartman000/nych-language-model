# NYCH GST Context, Lookup, and Symbolization Flow — V1

## Status

Owner-approved architecture: GST assembly and symbol selection are separate modules; the first symbol-selection call receives both request-scoped GST and the complete natural-language prompt. A deterministic database lookup occurs as domain/action information is identified. If there is no matching record, the first symbol-selection call resolves the missing entry dynamically under invariant constraints.

The source schema is now identified at `nhartman000/T.O.T.E-loops/schema.sql`. It defines `modality_operators`, `gestalts`, `tote_loops`, `tote_steps`, and `loop_gestalts`; `src/build_db.py` generates SQLite `data/tote_loops.sqlite3` and deterministic `data/tote_loops.json`. This NYCH repo has not implemented the GST adapter. The runtime adapter/endpoint, match rule, GST wire schema, hierarchy mapping/extension, evidence format, symbol-selection wire schema, and database write/verification policy remain open.

## Processing model

1. B1 ingests the exact prompt; B2 supplies token boundaries and source spans; B3 supplies trace identity; B4 resolves domain evidence using its approved local lexicon and no LLM calls.
2. As domains/actions are identified, B5 checks the TOTE database deterministically. The current schema exposes `tote_loops.domain`; action text is represented in `tote_steps.plain_text` and `tote_steps.nych_text`, with modality/proposition/provenance fields on steps. Existing matching records are assembled into request-scoped global `.gst`.
3. B5 records whether information came from a database entry, explicit evidence, or remains unknown. The existing schema has no dedicated action key, nor separate subdomain/function/technique, actor, or object/tool tables. B5 must not manufacture those fields; preserve unavailable values as unresolved unless another approved source provides them.
4. The first B6 symbol-selection LLM call receives the assembled `.gst` and separate complete prompt. It uses existing entries; if an action/domain record is absent, it resolves the missing context/gestalt dynamically during the call, constrained by invariant TOTE and modality rules.
5. The intended database coverage grows over time so deterministic lookup can serve more domain/action combinations. The current schema's exact matching rule and schema extensions for normalized action keys and full GST hierarchy remain undecided. Validation, approval, persistence, conflict handling, and versioning of new entries are also open.

Known records are looked up before the call; missing records are handled during it. B4 remains a deterministic, no-LLM domain resolver.

## GST structure and invariants

The global `.gst` represents:

`domain → subdomain → sub-subdomain → function → technique → TOTE loop`

A TOTE loop means Test–Operate–Test–Exit and has at least one actor, one action, one object or tool, and one modality operator. These are invariants, not optional fields to guess or omit.

The modality operator comes from the fixed NYCH inventory and expresses supported sensory or mental perspective, including internal/external sensing and mental actions such as remembering or imagining. Exact catalog and serialization remain to be specified.

Other supported context includes narrative perspective and tense, subject–predicate and related semantic roles, temporal intervals, and relationships. Distinguish sourced facts, deterministic database results, dynamic call results, and unknowns. Never promote unsupported inference to fact.

## Symbol selection

The first symbol-selection call has two separate inputs:

- request-scoped global `.gst`, including database matches and explicit unknown/cache-miss markers; and
- the separate complete natural-language prompt.

The call uses domain/action context to select canonical emoji gestalts only where the mapping is faithful. Words without a faithful mapping remain literal. Preserve NYCH operators, negation, modality, quantifiers, roles, and observation/belief/intention/action distinctions. Follow the versioned inventory and interface; do not add arbitrary or unregistered emoji.

B3 trace identity remains separate from vocabulary token IDs and selected emoji. Apply its approved SHA-256 identity and derived suffix idempotently.

## Module boundaries

- B2 supplies source spans and token boundaries; it does not choose gestalts.
- B3 creates trace identity; it does not infer meaning.
- B4 resolves domain evidence locally without LLM calls.
- B5 owns deterministic lookup against the current TOTE SQLite/JSON schema and request-scoped GST assembly. It records provenance and cache misses; absent schema fields remain unresolved.
- B6 owns the first symbol-selection call, using B5 context and the separate prompt; it handles missing entries dynamically under the invariants.
- New database-entry approval, validation, persistence, conflict resolution, and versioning must be defined before write-back is enabled.

Raw prompt and GST are request-scoped. Never persist raw prompts or write them to QSON. Do not persist GST unless separately approved.

## Open interface decisions

- exact `.gst` schema, fields, versioning, and serialization;
- current schema source: `T.O.T.E-loops/schema.sql`; runtime adapter/endpoint and versioning;
- cache-miss and unknown representation;
- database write-back, validation, conflict, and approval policy;
- exact invariant TOTE and modality catalogs and representation;
- evidence/confidence rules and distinction between database result and model inference;
- symbol-selection request/response schema, word alignment, and abstention;
- complete canonical emoji inventory/aliases; and
- runtime ownership/calling interface for the first symbol-selection LLM call.
