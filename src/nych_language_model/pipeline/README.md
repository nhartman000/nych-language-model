# Deterministic NYCH pipeline modules

- `ingest.py` — Builder 1 candidate; strict UTF-8 ingress, digest and provenance.
- `tokenization.py` — Builder 2; pending D2 tokenizer/vocabulary choice. English-only V1 is approved.
- `trace_identity.py` — Builder 3 candidate; hashes the B1 exact-input digest plus zero-based occurrence index and source-relative half-open byte span using the versioned binary contract in the module. It accent-folds only the derived English suffix, rejects residual non-English letters it cannot fold to ASCII, and renders an empty structured suffix as `∅`. Final ID serialization and B4 domain assignment remain open.
- `domain_resolution.py` — Builder 4; pending associative lexicon policy; no LLM calls.
- `nych_symbolization.py` — Builder 5; pending canonical symbol/operator contract.

The source text and token offsets are preserved. Accent folding is limited to the derived trace suffix.
