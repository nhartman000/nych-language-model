# NYCH Language Model V1

A small, inspectable NYCH language-model proof of concept. The repository separates deterministic natural-language/NYCH preprocessing from the neural model and from training/evaluation.

## Package layout

```text
src/nych_language_model/
  pipeline/   ingest, tokenization, trace, domain, GST lookup/context, symbolization
  model/      embeddings, attention, transformer block, output head
  training/   corpus manifests, training, evaluation, packaging
tests/        focused unit, invariant, and comparison checks
docs/         module contracts, decision register, and build status
```

## Module flow

B1–B4 provide ingest, tokenization, trace identity, and deterministic domain resolution. B5 looks up existing action/domain records and assembles request-scoped `.gst`. B6 makes the first symbol-selection LLM call with GST and the full prompt as separate inputs; missing entries are resolved dynamically during that call under invariant TOTE and modality constraints. Database write-back and verification policy remain open. B7–B11 cover embeddings through training/evaluation.

Builders submit modules independently and separate Inspectors review exact candidate digests. Candidates may be developed in parallel against frozen contracts; integration is gated by dependencies, interface versions, review evidence, and artifact digests.

## Current status

B1 Ingest candidate is present. Its approved policy accepts strict UTF-8 bytes up to 65,536 bytes, rejects malformed, empty, and oversized input, and performs no normalization or truncation. Raw prompts remain request-memory-only and must never be persisted or included in QSON. Independent inspection is pending.

No GST database, new module implementation, corpus training, or neural weights are claimed by the architecture update. Weight pruning is deferred to Builder Pro V2.
