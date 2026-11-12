"""Synthetic forward/backward smoke run; no natural-language prompt is used."""

from __future__ import annotations

import json

import torch

from .config import DecoderConfig
from .decoder import NYCHDecoder


def main() -> None:
    torch.manual_seed(7)
    config = DecoderConfig(vocab_size=32)
    model = NYCHDecoder(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    # Synthetic IDs exercise the neural graph without claiming a trained
    # tokenizer, corpus, or NYCH semantic mapping.
    input_ids = torch.tensor(
        [[1, 5, 3, 8, 2, 7, 4, 6], [2, 4, 1, 9, 5, 3, 7, 8]],
        dtype=torch.long,
    )
    labels = torch.roll(input_ids, shifts=-1, dims=1)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    logits, loss = model(input_ids, labels)
    if loss is None or not torch.isfinite(loss):
        raise RuntimeError("smoke loss is missing or non-finite")
    loss.backward()
    optimizer.step()

    expected = config.vocab_size * config.d_model + config.expected_non_embedding_parameters
    actual = model.parameter_count()
    if actual != expected:
        raise RuntimeError(f"parameter count mismatch: expected {expected}, got {actual}")

    model.eval()
    with torch.no_grad():
        eval_logits, _ = model(input_ids)
    print(json.dumps({
        "status": "PASS",
        "scope": "synthetic neural-core smoke; not tokenizer or corpus training",
        "logits_shape": list(eval_logits.shape),
        "loss_before_update": float(loss.detach()),
        "trainable_parameters": actual,
        "non_embedding_parameters": config.expected_non_embedding_parameters,
        "context_limit": config.max_seq_len,
        "layers": config.n_layers,
        "heads": config.n_heads,
        "head_width": config.head_dim,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
