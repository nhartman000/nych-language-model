# NYCH GST Context, Lookup, and Symbolization Flow — V1

## Status

Owner-approved architecture: GST assembly and symbol selection are separate modules; the first symbol-selection call receives both request-scoped GST and the complete natural-language prompt. A deterministic database lookup occurs as domain/action information is identified. If there is no matching record, the first symbol-selection call resolves the missing entry dynamically under invariant constraints.

The detailed GST schema, lookup endpoint/store, evidence format, symbol-selection wire schema, and database write/verification policy remain open. This records architecture; it does not claim implementation.

## Processing model

1. B1 ingests the exact prompt; B2 supplies token boundaries and source spans; B3 supplies trace identity; B4 resolves domain evidence using its approved local lexicon and no LLM calls.
2. As domains and actions are identified, B5 checks the versioned action/domain database. Existing entries are retrieved deterministically and assembled into request-scoped global `.gst`.
3. B5 records whether information came from a database entry, explicit evidence, or remains unknown. It does not invent a cache-miss record.
4. The first B6 symbol-selection LLM call receives the assembled `.gst` and separate complete prompt. It uses existing entries; if an action/domain record is absent, it resolves the missing context/gestalt dynamically during the call, constrained by invariant TOTE and modality rules.
5. The intended database coverage grows over time so deterministic lookup can serve more domain/action combinations. Validation, approval, persistence, conflict handling, and versioning of new entries are not yet decided.

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
- B5 owns deterministic action/domain lookup and request-scoped GST assembly. It records provenance and cache misses.
- B6 owns the first symbol-selection call, using B5 context and the separate prompt; it handles missing entries dynamically under the invariants.
- New database-entry approval, validation, persistence, conflict resolution, and versioning must be defined before write-back is enabled.

Raw prompt and GST are request-scoped. Never persist raw prompts or write them to QSON. Do not persist GST unless separately approved.

## Open interface decisions

- exact `.gst` schema, fields, versioning, and serialization;
- database schema, data source/provenance model, lookup endpoint, and versioning;
- cache-miss and unknown representation;
- database write-back, validation, conflict, and approval policy;
- exact invariant TOTE and modality catalogs and representation;
- evidence/confidence rules and distinction between database result and model inference;
- symbol-selection request/response schema, word alignment, and abstention;
- complete canonical emoji inventory/aliases; and
- runtime ownership/calling interface for the first symbol-selection LLM call.
