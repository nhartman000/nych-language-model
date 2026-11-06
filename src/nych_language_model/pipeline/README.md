# Deterministic NYCH pipeline modules

- `ingest.py` — Builder 1 candidate; strict UTF-8 ingress, digest and provenance.
- `tokenization.py` — Builder 2; pending D2 tokenizer/vocabulary choice. English-only V1 is approved.
- `trace_identity.py` — Builder 3 draft; derives an accent-folded English consonant suffix and inventory-validated emoji display. It does not assemble the final trace ID; SHA inputs, occurrence identity, separators, and domain binding remain open.
- `domain_resolution.py` — Builder 4; pending associative lexicon policy; no LLM calls.
- `nych_symbolization.py` — Builder 5; pending canonical symbol/operator contract.

The source text and token offsets are preserved. Accent folding is limited to the derived trace suffix.
