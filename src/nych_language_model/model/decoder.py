"""Small decoder-only causal language model."""

from __future__ import annotations

import torch
from torch import nn

from .config import DecoderConfig
from .embeddings import TokenEmbeddings
from .output_head import TiedOutputHead
from .transformer_block import RMSNorm, TransformerBlock


class NYCHDecoder(nn.Module):
    """V1 reference decoder; token IDs are supplied by the separate B2 tokenizer."""

    def __init__(self, config: DecoderConfig) -> None:
        super().__init__()
        self.config = config
        self.token_embeddings = TokenEmbeddings(config.vocab_size, config.d_model)
        self.blocks = nn.ModuleList(TransformerBlock(config) for _ in range(config.n_layers))
        self.final_norm = RMSNorm(config.d_model)
        self.output_head = TiedOutputHead()

    def forward(
        self, input_ids: torch.Tensor, labels: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        if input_ids.ndim != 2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        if input_ids.dtype != torch.long:
            raise TypeError("input_ids must use torch.long")
        if input_ids.shape[1] == 0 or input_ids.shape[1] > self.config.max_seq_len:
            raise ValueError("input sequence length is outside the configured range")
        hidden = self.token_embeddings(input_ids)
        for block in self.blocks:
            hidden = block(hidden)
        logits = self.output_head(self.final_norm(hidden), self.token_embeddings.weight)
        loss = None
        if labels is not None:
            if labels.shape != input_ids.shape:
                raise ValueError("labels must have the same shape as input_ids")
            if labels.dtype != torch.long:
                raise TypeError("labels must use torch.long")
            loss = torch.nn.functional.cross_entropy(
                logits.float().reshape(-1, self.config.vocab_size),
                labels.reshape(-1),
            )
        return logits, loss

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters() if parameter.requires_grad)
