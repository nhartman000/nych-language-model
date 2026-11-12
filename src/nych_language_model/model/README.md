# Neural model modules

The V1 neural core is a float32 decoder-only causal transformer. B7–B10 are wired by `NYCHDecoder`:

- learned token embeddings with rotary positions;
- two causal decoder blocks, four attention heads, model width 128;
- pre-RMSNorm, residuals, SwiGLU width 512, training dropout 0.1;
- final RMSNorm and logits tied to the input embedding weights.

Run the synthetic architecture smoke after installing the package:

```bash
python -m nych_language_model.model.smoke
```

The smoke uses synthetic token IDs, executes one forward/backward optimizer step, checks finite loss and the approved non-embedding parameter count, then emits a JSON result. It demonstrates neural graph execution only. B2 tokenization/vocabulary, B4 domain resolution, B6 symbolization, licensed-corpus training, and trained weights are not implemented by this smoke.
