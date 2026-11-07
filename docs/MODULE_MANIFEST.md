# Module manifest

| Builder | Module | Source location | State |
|---|---|---|---|
| B1 | Ingest | `src/nych_language_model/pipeline/ingest.py` | Candidate present; owner policy approved; independent Inspector 1 review pending |
| B2 | Tokenization | `src/nych_language_model/pipeline/tokenization.py` | English V1 approved; awaiting D0/D2 |
| B3 | Trace identity | `src/nych_language_model/pipeline/trace_identity.py` | SHA-256 occurrence payload and suffix components passed independent inspection (12/12 tests); final ID serialization remains open; exact-input digest and token-span consistency are integration checks |
| B4 | Domain resolution | `src/nych_language_model/pipeline/domain_resolution.py` | Awaiting D4 |
| B5 | NYCH symbolization | `src/nych_language_model/pipeline/nych_symbolization.py` | Awaiting D5 |
| B6 | Embeddings and position | `src/nych_language_model/model/embeddings.py` | Awaiting D0, D1, D2, D5, D6 |
| B7 | Causal attention | `src/nych_language_model/model/attention.py` | Awaiting D0, D6, D7 |
| B8 | Transformer block | `src/nych_language_model/model/transformer_block.py` | Awaiting D6–D8 |
| B9 | Output projection/softmax | `src/nych_language_model/model/output_head.py` | Awaiting D0, D2, D6, D9 |
| B10 | Training/evaluation | `src/nych_language_model/training/` | Awaiting D0, D10, D11 |

Builders can produce independent candidate implementations in parallel once the shared contracts are frozen. A candidate does not become integrated until its Inspector and host gate pass.
