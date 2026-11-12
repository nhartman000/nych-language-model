"""Vocabulary projection tied directly to the input embedding matrix."""

from __future__ import annotations

import torch
from torch import nn


class TiedOutputHead(nn.Module):
    def forward(self, hidden: torch.Tensor, embedding_weight: nn.Parameter) -> torch.Tensor:
        return torch.nn.functional.linear(hidden, embedding_weight)
