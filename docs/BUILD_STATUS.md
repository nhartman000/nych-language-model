# Build status

- B1 Ingest: candidate source added; owner policy approved; independent inspection pending.
- B3 Trace identity: bounded implementation PASS; Inspector 3 independently verified 14/14 focused tests; integration checks remain.
- B5 GST context: V2 candidate/implementation is present; its documented independent review and migration boundaries still apply.
- B7–B10 neural core: candidate implementation added on branch `wire/decoder-core-smoke-v1`; synthetic forward/backward smoke and focused tests are included. Independent inspection and GitSON wiring remain pending.
- B2 tokenizer/vocabulary, B4 domain resolver, B6 symbolization, B11 corpus training/evaluation: not implemented in this candidate.
- No trained NYCH weights or corpus-derived vocabulary are claimed by the neural-core smoke.
- Integration and GitSON wiring require independent Inspector PASS evidence and digest-bound host validation.
- Prompt privacy: raw text is memory-only; QSON and reports may record digest and metadata but never the prompt.
