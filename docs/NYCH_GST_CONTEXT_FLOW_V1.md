# NYCH GST Context, Lookup, and Symbolization Flow — V1

## Status

Owner-approved architecture: GST assembly and symbol selection are separate modules; the first symbol-selection call receives request-scoped GST and the complete natural-language prompt. B5 V2 now performs deterministic lookup with exact canonical domain/action keys, recomputes the loop digest, and emits a versioned GST JSON object. The TOTE schema expansion and migration 002 are merged in `nhartman000/T.O.T.E-loops`; migration of an existing SQLite file and conformance testing are deferred to the later test pass. The B5 candidate passed independent inspection and its NYCH suite passed 36 tests.

The migration records `PRAGMA user_version=2`; the B5 digest includes that integer. Existing TOTE seed records and JSON export fields are unchanged. The guarded runner is `migrations/apply_002.py`. Live search, query/ranking policy, upstream B4→B5 interface, and database write/admission endpoint remain open.

## Processing model

1. B1 ingests the exact prompt; B2 supplies token boundaries and source spans; B3 supplies trace identity; B4 resolves domain evidence using its approved local lexicon and no LLM calls.
2. B5 reads `PRAGMA user_version` and requires version 2. It matches B4's canonical `domain_id` and `action_key` exactly against TOTE taxonomy/action keys; ambiguous matches are cache misses. Verified loop context is assembled into request-scoped `.gst`.
3. A provider interface can return sourced candidates for missing hierarchy nodes. Candidates retain provenance and remain unapproved until human review; live Google calls, credentials, and ranking/acceptance rules are not yet implemented.
4. Techniques may be extracted from how-to texts into loop candidates. A human validates these candidates before canonical admission. Existing TOTE records remain deterministic; if no record exists for the action under that domain, the first B6 symbol-selection call resolves the missing context/gestalt dynamically under invariant TOTE and modality rules.
5. Database coverage grows as reviewed material and human contributions are admitted. A future web interface will let contributors select domain/subdomain/sub-subdomain/function/technique from dropdowns, choose modality operators from a dropdown, and type action descriptions. Contributions are human-authored and then automatically verified against schema constraints and NYCH/TOTE invariants before admission. Exact matching rules, schema extensions, verifier suite, persistence, conflict handling, and versioning remain open.

Known records are looked up before the call; missing records are handled during it. B4 remains a deterministic, no-LLM domain resolver.

## GST structure and invariants

The versioned GST JSON V1 contract represents:

`domain → subdomain → sub-subdomain → function → technique → TOTE loop`

The emitted context includes lookup state, taxonomy, TOTE elements/steps, linked gestalts and modality operators, upstream narrative/provenance envelopes, and digest integrity. Narrative is passed through from upstream; B5 does not infer it. The contract is defined in `schemas/gst-context-v1.schema.json`.

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
- B5 owns exact canonical domain/action lookup, versioned GST assembly, digest verification, and provenance-aware provider candidate interfaces. It does not make live search calls or infer narrative fields. The trusted runtime recomputes the canonical loop digest on every hit; status alone never licenses a hit. How-to-derived loops require matching human approval; human-authored entries require automatic structural/invariant validation.
- B6 owns the first symbol-selection call, using B5 context and the separate prompt; it handles missing entries dynamically under the invariants.
- New database-entry approval, validation, persistence, conflict resolution, and versioning must be defined before write-back is enabled.

Raw prompt and GST are request-scoped. Never persist raw prompts or write them to QSON. Do not persist GST unless separately approved.

## Open interface decisions

- upstream B4→B5 interface for canonical IDs, action keys, narrative fields, and provenance;
- live Google provider credentials, query generation, source ranking, and candidate acceptance;
- runtime write endpoint and database admission permissions;
- cache-miss and unknown representation;
- trusted lookup/write boundary: never accept `admission_status` alone; recompute `NYCH-TOTE-LOOP-DIGEST-V1` at lookup and compare the digest and version with the latest PASS validation and any required human review;
- database write-back, validation, conflict, and approval policy;
- exact invariant TOTE and modality catalogs and representation;
- evidence/confidence rules and distinction between database result and model inference;
- symbol-selection request/response schema, word alignment, and abstention;
- complete canonical emoji inventory/aliases; and
- runtime ownership/calling interface for the first symbol-selection LLM call.
