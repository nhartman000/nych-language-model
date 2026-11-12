# NYCH Language Model V1

A small, inspectable NYCH language-model proof of concept. The repository separates deterministic natural-language/NYCH preprocessing from the neural model and from training/evaluation.

## Package layout

```text
src/nych_language_model/
  pipeline/   ingest, tokenization, trace, domain, GST lookup/context, symbolization
  model/      embeddings, attention, transformer block, output head, decoder
  training/   corpus manifests, training, evaluation, packaging
tests/        focused unit, invariant, and comparison checks
docs/         module contracts, decision register, and build status
```

## Module flow

B1–B4 provide ingest, tokenization, trace identity, and deterministic domain resolution. B5 looks up existing action/domain records and assembles request-scoped `.gst`. B6 makes the first symbol-selection call with GST and the full prompt as separate inputs; missing entries are resolved dynamically during that call under invariant TOTE and modality constraints. B7–B10 form the decoder-only causal language model. B11 owns reproducible corpus training and evaluation.

## Current status

B1 strict UTF-8 ingress and B3 trace identity candidates are present. B5 GST context implementation is present. B7–B10 now have a candidate neural core with learned token embeddings, rotary positions, causal attention, pre-RMSNorm/SwiGLU blocks, tied output projection, and cross-entropy loss. The model configuration is 128-wide, two layers, four heads with width 32, SwiGLU width 512, 1,024-token context, float32, and training dropout 0.1.

Run the synthetic neural-core smoke:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m nych_language_model.model.smoke
```

The smoke performs a forward pass, computes next-token cross-entropy, runs one AdamW update on synthetic token IDs, verifies tensor shape and parameter count, and prints a JSON PASS record. It is an architecture execution check; it is not trained NYCH text generation.

B2 tokenizer/vocabulary, B4 domain resolution, B6 symbolization, the corpus builder/training loop, and trained weights remain unfinished. No GST database, corpus weights, or trained model weights are bundled. Raw prompts remain request-memory-only and are excluded from QSON.

Builders submit modules independently and separate Inspectors review exact candidate digests. A candidate does not become integrated until its Inspector and trusted host gate pass.
