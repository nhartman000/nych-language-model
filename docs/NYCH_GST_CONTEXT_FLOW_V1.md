# NYCH GST Context and Symbolization Flow — V1

## Status

Owner-provided architecture direction recorded. This document states the intended flow and module boundaries; it does not freeze the detailed GST schema, extraction algorithms, prompt wire format, or full emoji inventory.

## Purpose

NYCH derives structured context from the user's natural-language prompt before symbol selection. A request-scoped global gestalt context artifact, called the global `.gst`, carries the inferred structure and meaning into the first symbol-selection LLM call. The LLM receives that context together with the separate, complete natural-language prompt.

The GST guides the selection of canonical emoji gestalts for words. Lexical databases, n-gram statistics, and proper-name records may provide spelling or candidate evidence; they do not replace GST-based contextual interpretation or decide emoji meaning by themselves.

## Required GST content

The global `.gst` represents the hierarchy:

`domain → subdomain → sub-subdomain → function → technique → TOTE loop`

A TOTE loop means Test–Operate–Test–Exit. Each loop contains at least:

- one actor;
- one action;
- one object or tool; and
- one modality operator.

The modality operator identifies the relevant sensory or mental perspective, including internal or external sensing and mental actions such as remembering or imagining.

The GST also carries, where supported by the prompt:

- narrative perspective and tense;
- subject–predicate and related grammatical/semantic roles;
- temporal intervals; and
- relationships among the extracted structures.

Missing or unsupported information remains unknown; the extractor must not invent it.

## First symbol-selection call

The first symbol-selection LLM call receives both:

1. the request's global `.gst` context; and
2. the separate, complete natural-language prompt.

Using both sources, it selects the best canonical emoji gestalt for each word that can be represented faithfully in context. If no faithful emoji gestalt exists, preserve the word literally. The output must follow the versioned symbol-selection interface and emoji inventory; it must not add arbitrary text or unregistered emoji.

## Trace identity

B3 owns the deterministic trace ID. The trace includes the approved SHA-256 identity and the derived word suffix formed by accent-folding to the approved English V1 form, removing vowels, and collapsing adjacent repeated consonants. Add the suffix only if it has not already been included; repeated processing must not append it twice. Trace identity remains separate from model vocabulary token IDs and from the selected emoji gestalt.

## Boundaries and data handling

- B2 preserves source text and byte spans and supplies token boundaries; it does not choose emoji gestalts.
- B3 generates the trace identity and derived suffix; it does not infer a word's meaning.
- B4 performs local domain resolution under its separate approved contract; the GST hierarchy does not turn B4 into an LLM-based domain resolver.
- B5 consumes approved GST and token interfaces for context-guided symbolization.
- Raw prompt text remains request-memory-only and must not be persisted or written to QSON. Treat the GST as request-scoped derived context under the same data-handling boundary unless a separate persistence policy is approved.
- The GST context and full natural-language prompt remain distinct inputs in the symbol-selection call.

## Open interface decisions

The following remain subject to separate owner approval before implementation is considered complete:

- exact `.gst` schema, field names, versioning, and serialization;
- GST-producing module ownership and the interface relationship among GST construction, B4 domain resolution, and B5 symbolization.
- deterministic extraction rules and evidence/unknown representation;
- canonical modality operator inventory and how sensory/mental perspective is encoded;
- symbol-selection request/response schema, including word alignment and abstention;
- complete canonical emoji inventory and alias rules; and
- runtime ownership and calling interface for the first symbol-selection LLM call.
