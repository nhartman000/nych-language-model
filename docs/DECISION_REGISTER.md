# NYCH Language Model V1 — Decision Register

Canonical worker instructions and Inspector cards are in the private [MG8 Model Builder repository](https://github.com/nhartman000/mg8-model-builder/tree/main/icm/MG8PK).

## Approved

- Module 1 accepts strict UTF-8 input up to 65,536 bytes; empty, malformed, and oversized inputs are rejected. No normalization or truncation.
- Raw prompt is request-memory-only. Do not persist it or include it in QSON. QSON may record digest and metadata.
- Candidate builds and independent inspections run concurrently against frozen contracts; integration is dependency-gated.
- Weight pruning is deferred to Builder Pro V2.
- This repository is private.

## Pending owner choices

| ID | Decision | Recommendation |
|---|---|---|
| D0 | Model objective | Deterministic NYCH encoder plus tiny decoder-only causal LM predicting next NYCH token/symbol sequence; keep assurance representation separate from probabilistic output. |
| D1 | Language/context | English V1; 1,024 model tokens per window; split longer accepted inputs into ordered windows. |
| D2 / B2 | Tokenizer | Byte-level BPE, 8,192 vocabulary, no normalization, byte offsets, explicit special-token registry. |
| D3 / B3 | Word trace | SHA-256 per word occurrence followed by consonant skeleton; decide exact vowel set, case, repeated-consonant handling, delimiters, and occurrence identity. Domain stays a separate B4 field. |
| D4 / B4 | Domain resolver | Versioned local associative lexicon only, no LLM calls; ranked evidence, multi-label ambiguity, UNKNOWN fallback. Owner approves seed lexicon and thresholds. |
| D5 / B5 | NYCH semantics | Canonical NYCH operators; preserve negation, modality, quantifiers, roles, and observation/belief/intention/action distinctions. |
| D6 / B6 | Embeddings/position | d_model 128, learned embeddings, RoPE, 1,024 context, float32 reference build. |
| D7 / B7 | Attention | Two causal layers total, four heads, width 32 per head, no KV cache in V1 reference build. |
| D8 / B8 | Block | Pre-RMSNorm, residual, SwiGLU, hidden width 512, dropout 0.1 only during training. |
| D9 / B9 | Output | Tied embeddings, full-vocabulary logits, stable softmax, next-token cross-entropy; no hard constraints until tested. |
| D10 / B10 | Corpus/training | Owner-approved, license-cleared English corpus; exclude prompts; deduplicate and fix split; record source hashes/config/seed/hardware; same-data baseline. |
| D11 | Inspector bar | Separate inspector; scope/contract, edge and adversarial tests, reproducibility, digest, reference comparison; missing evidence is INTERMEDIATE. |
| D12 | GitSON | One <500,000-byte wiring declaration per boundary, with module IDs, interface versions, digests, upstream PASS evidence, and trusted host validation. |

Agents do not invent choices marked pending. Role files and responsibility boundaries are defined; module implementations are launched only when their decision dependencies are frozen.
