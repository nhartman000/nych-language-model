# Deterministic NYCH pipeline modules

- `ingest.py` — Builder 1 candidate; strict UTF-8 ingress, digest and provenance.
- `tokenization.py` — Builder 2; pending approved tokenizer contract.
- `trace_identity.py` — Builder 3; English V1 approved; accent-fold only the derived suffix, preserving the original text and offsets. Full trace-ID assembly is pending remaining D3 decisions.
- `domain_resolution.py` — Builder 4; pending associative lexicon policy; no LLM calls.
- `nych_symbolization.py` — Builder 5; pending canonical symbol/operator contract.

Each module exposes a versioned contract and preserves source offsets/provenance. No module silently normalizes or discards input.
