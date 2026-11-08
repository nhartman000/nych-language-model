| B1 | Ingest | `src/nych_language_model/pipeline/ingest.py` | Candidate present; owner policy approved; independent Inspector 1 review pending |
| B2 | Tokenization | `src/nych_language_model/pipeline/tokenization.py` | Whitespace-delimited spans, canonical atomic emoji, layered statistical/name lexicons, keyboard/context typo hypotheses; approved corpus and candidate-source decisions recorded; source/license import, score calibration, and measured validation remain pending |
| B3 | Trace identity | `src/nych_language_model/pipeline/trace_identity.py` | Bounded B3 module PASS; Inspector 3 independently verified 14/14 focused tests. Integration must verify exact B1 digest provenance and B2 zero-based indices/half-open UTF-8 byte spans. B4 domain assignment is separate |
| B4 | Domain resolution | `src/nych_language_model/pipeline/domain_resolution.py` | Versioned local associative lexicon only; no LLM calls. Supplies domain evidence to B5. Seed lexicon/threshold decisions remain under D4 |
| B5 | GST context assembly and domain/action lookup | `src/nych_language_model/pipeline/gst_context.py` | V2 independently inspected and merged; 36 tests passed. Reads SQLite `user_version=2`; exact canonical domain ID/action key match, ambiguity misses; versioned GST JSON schema. TOTE migration 002 merged to T.O.T.E-loops main; applying to existing DB and conformance tests deferred. Live search and B4→B5 end-to-end integration remain pending |
| B6 | NYCH symbolization | `src/nych_language_model/pipeline/nych_symbolization.py` | First symbol-selection LLM call receives B5 GST plus separate full prompt; uses available TOTE records and dynamically resolves cache misses under invariant constraints; preserves literal text when no faithful gestalt applies. Call contract and database write policy remain pending |
| B7 | Embeddings and position | `src/nych_language_model/model/embeddings.py` | Awaiting D0, D1, D2, D7, D8 |
| B8 | Causal attention | `src/nych_language_model/model/attention.py` | Awaiting D0, D7, D8 |
| B9 | Transformer block | `src/nych_language_model/model/transformer_block.py` | Awaiting D7–D9 |
| B10 | Output projection/softmax | `src/nych_language_model/model/output_head.py` | Awaiting D0, D2, D7, D10 |
| B11 | Training/evaluation | `src/nych_language_model/training/` | Awaiting D0, D11, D12 |

Builders can produce independent candidate implementations in parallel once the shared contracts are frozen. A candidate does not become integrated until its Inspector and host gate pass.
