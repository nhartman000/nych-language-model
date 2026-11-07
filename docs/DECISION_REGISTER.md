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
| D1 | Language/context | English-only V1; 1,024 model tokens per window; split longer accepted inputs into ordered windows. | Language approved; context pending |
| D2 / B2 | Tokenizer | Owner direction: whitespace-delimited English surface-word spans with exact byte offsets; recognized emoji graphemes are single atomic tokens from a versioned canonical inventory; approved non-meaning-changing aliases fold to inventory defaults via explicit rules, while source text remains unchanged. Scientific terms, proper names, and other words without a faithful emoji mapping remain literal text; no forced emoji substitution. Use a versioned local statistical compendium first, ranking candidates from the prior two or three words and context; check top candidates against keyboard-layout maps second. Preserve original spelling and byte spans; if the original is valid/coherent or no candidate is clear, leave it literal and unresolved. | Whitespace word spans, canonical emoji, and punctuation policy approved; whitespace-token representation approved; corpus source selected: complete English Wikipedia dump `enwiki-20261001` for general statistical weights, with separate technical/name lexicons and no prompt logs. Record snapshot/page provenance and honor applicable attribution/share-alike terms; keep derived artifacts private pending license review. Keyboard layout registry approved (US/UK QWERTY, AZERTY, QWERTZ; consensus required if layout unknown); automatic typo interpretation must achieve at least 99% precision on held-out cases; OOV encoding remains pending |
| D3 / B3 | Word trace | English V1; accent-fold only the derived suffix and preserve original source bytes/text; remove a/e/i/o/u, retain y, collapse adjacent repeated consonants. Reject residual non-English letters that do not accent-fold to ASCII. Empty structured suffix is `""`; display it as `∅`. Domain is a separate B4 field. Hash payload: version tag `NYCH-WORD-ID\\0v1\\0`, B1 exact-input SHA-256 digest bytes, zero-based occurrence index, and source-relative start-inclusive/end-exclusive byte offsets; encode integers as unsigned 64-bit big-endian and use full lowercase SHA-256 hex. Canonical ID display: `sha256:<64-lowercase-hex>_<suffix-or-∅>`; B4 `domain_id` stays separate. | Hash payload, occurrence identity, suffix policy, and ID serialization approved; B4 domain lexicon/assignment policy remains pending under D4 |
| D4 / B4 | Domain resolver | Versioned local associative lexicon only, no LLM calls; ranked evidence, multi-label ambiguity, UNKNOWN fallback. Owner approves seed lexicon and thresholds; if no faithful canonical symbol applies, preserve text and return UNKNOWN/no symbol rather than substituting emoji. |
| D5 / B5 | NYCH semantics | Canonical NYCH operators; preserve negation, modality, quantifiers, roles, and observation/belief/intention/action distinctions. Preserve scientific names, proper names, and spans without a faithful emoji as literal text; emoji mapping is optional and never forced. |
| D6 / B6 | Embeddings/position | d_model 128, learned embeddings, RoPE, 1,024 context, float32 reference build. |
| D7 / B7 | Attention | Two causal layers total, four heads, width 32 per head, no KV cache in V1 reference build. |
| D8 / B8 | Block | Pre-RMSNorm, residual, SwiGLU, hidden width 512, dropout 0.1 only during training. |
| D9 / B9 | Output | Tied embeddings, full-vocabulary logits, stable softmax, next-token cross-entropy; no hard constraints until tested. |
| D10 / B10 | Corpus/training | Owner-approved, license-cleared English corpus; exclude prompts; deduplicate and fix split; record source hashes/config/seed/hardware; same-data baseline. |
| D11 | Inspector bar | Separate inspector; scope/contract, edge and adversarial tests, reproducibility, digest, reference comparison; missing evidence is INTERMEDIATE. |
| D12 | GitSON | One <500,000-byte wiring declaration per boundary, with module IDs, interface versions, digests, upstream PASS evidence, and trusted host validation. |

Agents do not invent choices marked pending. Role files and responsibility boundaries are defined; module implementations are launched only when their decision dependencies are frozen.
