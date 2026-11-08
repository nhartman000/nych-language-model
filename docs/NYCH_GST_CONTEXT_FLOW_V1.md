# NYCH GST Context, Lookup, and Symbolization Flow — V1

## Status

Owner-approved architecture: GST assembly and symbol selection are separate modules; the first symbol-selection call receives both request-scoped GST and the complete natural-language prompt. A deterministic database lookup occurs as domain/action information is identified. If there is no matching record, the first symbol-selection call resolves the missing entry dynamically under invariant constraints.

The source schema is identified at `nhartman000/T.O.T.E-loops/schema.sql`; the owner approved extending this same SQLite database additively. A private draft proposal is at `docs/GST_TAXONOMY_SCHEMA_PROPOSAL_V1.md`; it is not an applied migration. It defines `modality_operators`, `gestalts`, `tote_loops`, `tote_steps`, and `loop_gestalts`; `src/build_db.py` generates SQLite `data/tote_loops.sqlite3` and deterministic `data/tote_loops.json`. This NYCH repo has not implemented the GST adapter. The runtime adapter/endpoint, match rule, GST wire schema, hierarchy mapping/extension, evidence format, symbol-selection wire schema, and database write/verification policy remain open.

## Processing model

1. B1 ingests the exact prompt; B2 supplies token boundaries and source spans; B3 supplies trace identity; B4 resolves domain evidence using its approved local lexicon and no LLM calls.
2. Once B4 identifies a domain, B5 checks existing TOTE records deterministically. The current schema exposes `tote_loops.domain`; action text is represented in `tote_steps.plain_text`/`nych_text`, with modality/proposition/provenance fields on steps. Existing matching records are assembled into request-scoped global `.gst`.
3. B5 enriches the identified domain hierarchy through Google search for applicable subdomains, sub-subdomains, functions, and techniques, retaining source provenance. The current SQLite schema has no dedicated hierarchy/action/actor/object fields, so search-derived taxonomy is tracked separately until the approved additive schema extension is implemented.
4. Techniques may be extracted from how-to texts into loop candidates. A human validates these candidates before canonical admission. Existing TOTE records remain deterministic; if no record exists for the action under that domain, the first B6 symbol-selection call resolves the missing context/gestalt dynamically under invariant TOTE and modality rules.
5. Database coverage grows as reviewed material and human contributions are admitted. A future web interface will let contributors select domain/subdomain/sub-subdomain/function/technique from dropdowns, choose modality operators from a dropdown, and type action descriptions. Contributions are human-authored and then automatically verified against schema constraints and NYCH/TOTE invariants before admission. Exact matching rules, schema extensions, verifier suite, persistence, conflict handling, and versioning remain open.

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

## Future loop-authoring interface

The planned web interface is a human contribution path, not a replacement for the how-to extraction/review path. It looks up the selected domain hierarchy and techniques, then accepts modality operators from a dropdown and action text from the contributor. The system automatically verifies submitted records for structural completeness, registered modality operators, proposition/provenance consistency, valid TOTE transitions and exit conditions, and database integrity. Human authorship and automated verification status are recorded separately. These checks establish structural/invariant conformance, not factual correctness of every action description.\n\n## Module boundaries

- B2 supplies source spans and token boundaries; it does not choose gestalts.
- B3 creates trace identity; it does not infer meaning.
- B4 resolves domain evidence locally without LLM calls.
- B5 owns deterministic lookup against current TOTE records, Google-search taxonomy enrichment with source provenance, and request-scoped GST assembly. The trusted runtime recomputes the canonical loop digest on every hit; status alone never licenses a hit. It routes how-to-derived loop candidates for human validation and supports the future auto-verified human contribution workflow.
- B6 owns the first symbol-selection call, using B5 context and the separate prompt; it handles missing entries dynamically under the invariants.
- New database-entry approval, validation, persistence, conflict resolution, and versioning must be defined before write-back is enabled.

Raw prompt and GST are request-scoped. Never persist raw prompts or write them to QSON. Do not persist GST unless separately approved.

## Open interface decisions

- exact `.gst` schema, fields, versioning, and serialization;
- current schema source: `T.O.T.E-loops/schema.sql`; runtime adapter/endpoint and versioning;
- cache-miss and unknown representation;
- trusted lookup/write boundary: never accept `admission_status` alone; recompute a versioned canonical digest at lookup and compare with the latest PASS validation and any required human review;
- database write-back, validation, conflict, and approval policy;
- exact invariant TOTE and modality catalogs and representation;
- evidence/confidence rules and distinction between database result and model inference;
- symbol-selection request/response schema, word alignment, and abstention;
- complete canonical emoji inventory/aliases; and
- runtime ownership/calling interface for the first symbol-selection LLM call.
