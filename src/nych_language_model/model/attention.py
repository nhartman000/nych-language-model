"""Causal multi-head self-attention with rotary positions."""

from __future__ import annotations

import math

import torch
from torch import nn

from .config import DecoderConfig
from .embeddings import RotaryPositionEncoding


class CausalSelfAttention(nn.Module):
    def __init__(self, config: DecoderConfig) -> None:
        super().__init__()
        self.config = config
        self.qkv = nn.Linear(config.d_model, 3 * config.d_model, bias=False)
        self.output = nn.Linear(config.d_model, config.d_model, bias=False)
        self.attention_dropout = config.dropout
        self.rope = RotaryPositionEncoding(config.head_dim, config.max_seq_len, config.rope_theta)

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        batch, length, width = hidden.shape
        if length > self.config.max_seq_len:
            raise ValueError("sequence exceeds configured context length")
        qkv = self.qkv(hidden).view(
            batch, length, 3, self.config.n_heads, self.config.head_dim
        ).permute(2, 0, 3, 1, 4)
        query, key, value = qkv.unbind(0)
        query, key = self.rope(query, key)

        scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(self.config.head_dim)
        future = torch.ones(length, length, dtype=torch.bool, device=hidden.device).triu(1)
        scores = scores.masked_fill(future, torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores.float(), dim=-1).to(dtype=scores.dtype)
        weights = torch.nn.functional.dropout(
            weights, p=self.attention_dropout, training=self.training
        )
        attended = torch.matmul(weights, value)
        attended = attended.transpose(1, 2).contiguous().view(batch, length, width)
        return self.output(attended)
