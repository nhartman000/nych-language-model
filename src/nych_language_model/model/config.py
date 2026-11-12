"""Frozen V1 decoder dimensions for the NYCH language-model proof of concept."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecoderConfig:
    vocab_size: int
    d_model: int = 128
    n_layers: int = 2
    n_heads: int = 4
    ffn_width: int = 512
    max_seq_len: int = 1024
    dropout: float = 0.1
    rope_theta: float = 10000.0

    def __post_init__(self) -> None:
        for name in ("vocab_size", "d_model", "n_layers", "n_heads", "ffn_width", "max_seq_len"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.vocab_size < 2:
            raise ValueError("vocab_size must be at least 2")
        if self.d_model % self.n_heads:
            raise ValueError("d_model must be divisible by n_heads")
        if (self.d_model // self.n_heads) % 2:
            raise ValueError("rotary attention head width must be even")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if self.rope_theta <= 0:
            raise ValueError("rope_theta must be positive")

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads

    @property
    def expected_non_embedding_parameters(self) -> int:
        """Parameter count for the approved no-bias, pre-RMSNorm shape."""
        attention = 4 * self.d_model * self.d_model
        swiglu = 3 * self.d_model * self.ffn_width
        norms = 2 * self.d_model
        return self.n_layers * (attention + swiglu + norms) + self.d_model
