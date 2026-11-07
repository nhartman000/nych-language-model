# Module manifest

| Builder | Module | Source location | State |
|---|---|---|---|
| B1 | Ingest | `src/nych_language_model/pipeline/ingest.py` | Candidate present; owner policy approved; independent Inspector 1 review pending |
| B2 | Tokenization | `src/nych_language_model/pipeline/tokenization.py` | Owner direction recorded: whitespace-delimited spans, atomic canonical emoji, layered lexicon and keyboard/context typo hypotheses; punctuation policy approved; whitespace token representation approved; general corpus selected: English Wikipedia `enwiki-20261001`; awaiting source/license import gate, lexicon sources, confidence threshold, and OOV policy before weight build |
| B3 | Trace identity | `src/nych_language_model/pipeline/trace_identity.py` | Bounded B3 module PASS; Inspector 3 independently verified 14/14 focused tests. Integration must verify exact B1 digest provenance and B2 zero-based indices/half-open UTF-8 byte spans. B4 domain assignment is separate. |
| B4 | Domain resolution | `src/nych_language_model/pipeline/domain_resolution.py` | Awaiting D4 |
| B5 | NYCH symbolization | `src/nych_language_model/pipeline/nych_symbolization.py` | Awaiting D5 |
| B6 | Embeddings and position | `src/nych_language_model/model/embeddings.py` | Awaiting D0, D1, D2, D5, D6 |
| B7 | Causal attention | `src/nych_language_model/model/attention.py` | Awaiting D0, D6, D7 |
| B8 | Transformer block | `src/nych_language_model/model/transformer_block.py` | Awaiting D6–D8 |
| B9 | Output projection/softmax | `src/nych_language_model/model/output_head.py` | Awaiting D0, D2, D6, D9 |
| B10 | Training/evaluation | `src/nych_language_model/training/` | Awaiting D0, D10, D11 |

Builders can produce independent candidate implementations in parallel once the shared contracts are frozen. A candidate does not become integrated until its Inspector and host gate pass.
