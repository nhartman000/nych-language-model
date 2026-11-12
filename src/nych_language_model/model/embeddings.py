"""Token embeddings and non-learned rotary position encoding."""

from __future__ import annotations

import torch
from torch import nn


class TokenEmbeddings(nn.Module):
    def __init__(self, vocab_size: int, d_model: int) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)

    @property
    def weight(self) -> nn.Parameter:
        return self.embedding.weight

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        if token_ids.ndim != 2:
            raise ValueError("token_ids must have shape [batch, sequence]")
        return self.embedding(token_ids)


class RotaryPositionEncoding(nn.Module):
    """Apply RoPE to [batch, heads, sequence, head_width] query/key tensors."""

    def __init__(self, head_dim: int, max_seq_len: int, theta: float = 10000.0) -> None:
        super().__init__()
        if head_dim < 2 or head_dim % 2:
            raise ValueError("head_dim must be a positive even number")
        positions = torch.arange(max_seq_len, dtype=torch.float32)
        frequencies = torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim
        inverse = 1.0 / (theta ** frequencies)
        angles = torch.outer(positions, inverse)
        self.register_buffer("cos", angles.cos(), persistent=False)
        self.register_buffer("sin", angles.sin(), persistent=False)

    def _rotate(self, tensor: torch.Tensor) -> torch.Tensor:
        length = tensor.shape[-2]
        if length > self.cos.shape[0]:
            raise ValueError("sequence exceeds rotary position limit")
        cos = self.cos[:length].to(device=tensor.device, dtype=tensor.dtype)[None, None, :, :]
        sin = self.sin[:length].to(device=tensor.device, dtype=tensor.dtype)[None, None, :, :]
        even = tensor[..., 0::2]
        odd = tensor[..., 1::2]
        output = torch.empty_like(tensor)
        output[..., 0::2] = even * cos - odd * sin
        output[..., 1::2] = even * sin + odd * cos
        return output

    def forward(self, query: torch.Tensor, key: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if query.shape != key.shape or query.ndim != 4:
            raise ValueError("query and key must have matching [batch, heads, sequence, width] shapes")
        return self._rotate(query), self._rotate(key)
