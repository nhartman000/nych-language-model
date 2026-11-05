# NYCH Language Model V1

A small, inspectable NYCH language-model proof of concept. The repository separates deterministic natural-language/NYCH preprocessing from the neural model and from training/evaluation.

## Package layout

```text
src/nych_language_model/
  pipeline/   deterministic input, token, trace, domain, and NYCH transforms
  model/      embeddings, attention, transformer block, output head
  training/   corpus manifests, training, evaluation, packaging
tests/        focused unit, invariant, and comparison checks
docs/         module contracts, decision register, and build status
```

Modules are submitted independently by the MG8 Model Builder workers and reviewed by separate Inspectors. Builders may prototype in parallel against frozen contracts. Integration is gated by interface versions, review evidence, and artifact digests.

## Current status

Module 1 Ingest candidate is present. Its owner-approved policy accepts strict UTF-8 bytes up to 65,536 bytes, rejects malformed/empty/oversized input, and performs no normalization or truncation. Raw prompts remain in request memory only and must never be persisted or included in QSON. The candidate still requires independent inspection before integration.

Modules 2–10 are pending owner decisions and are not yet implemented. No corpus training, neural weights, or model capability claim is included in this repository yet. Weight pruning is deferred to Builder Pro V2.
