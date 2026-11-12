"""Pre-RMSNorm decoder block with a SwiGLU feed-forward network."""

from __future__ import annotations

import torch
from torch import nn

from .attention import CausalSelfAttention
from .config import DecoderConfig


class RMSNorm(nn.Module):
    def __init__(self, width: int, eps: float = 1e-6) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        normalized = value * torch.rsqrt(value.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return normalized * self.weight


class SwiGLU(nn.Module):
    def __init__(self, d_model: int, hidden_width: int) -> None:
        super().__init__()
        self.gate = nn.Linear(d_model, hidden_width, bias=False)
        self.up = nn.Linear(d_model, hidden_width, bias=False)
        self.down = nn.Linear(hidden_width, d_model, bias=False)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.down(torch.nn.functional.silu(self.gate(value)) * self.up(value))


class TransformerBlock(nn.Module):
    def __init__(self, config: DecoderConfig) -> None:
        super().__init__()
        self.attention_norm = RMSNorm(config.d_model)
        self.attention = CausalSelfAttention(config)
        self.feed_forward_norm = RMSNorm(config.d_model)
        self.feed_forward = SwiGLU(config.d_model, config.ffn_width)
        self.dropout = config.dropout

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        attention = self.attention(self.attention_norm(hidden))
        hidden = hidden + torch.nn.functional.dropout(
            attention, p=self.dropout, training=self.training
        )
        feed_forward = self.feed_forward(self.feed_forward_norm(hidden))
        return hidden + torch.nn.functional.dropout(
            feed_forward, p=self.dropout, training=self.training
        )
