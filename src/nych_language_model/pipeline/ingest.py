"""Module 1: deterministic raw-text ingress for the NYCH LM project.

This is deliberately separate from ``nych.ingest`` in the existing NYCH
encoder. It captures and validates text input only; it does not normalize,
tokenize, identify domains, or perform symbolic encoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import re
from typing import Literal


@dataclass(frozen=True, slots=True)
class IngestPolicy:
    """Explicit input limits. The default maximum is the owner-approved practical ceiling for V1."""

    max_bytes: int = 65_536
    allow_empty: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.max_bytes, int) or isinstance(self.max_bytes, bool):
            raise TypeError("max_bytes must be an integer")
        if self.max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        if not isinstance(self.allow_empty, bool):
            raise TypeError("allow_empty must be a boolean")


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Digest-bound result for one received input payload.

    ``text`` is populated only for accepted input. The original-byte digest
    and byte count are recorded for accepted and rejected payloads. Callers
    should not place raw prompt text in QSON or ordinary logs.
    """

    status: Literal["ACCEPTED", "REJECTED"]
    request_id: str
    received_at: str
    encoding: Literal["utf-8"]
    byte_length: int
    raw_sha256: str
    ingest_version: str
    text: str | None
    error_code: str | None = None


def ingest_bytes(
    raw: bytes,
    *,
    request_id: str,
    received_at: str,
    policy: IngestPolicy = IngestPolicy(),
    ingest_version: str = "1.0.0",
) -> IngestResult:
    """Validate UTF-8 bytes and return exact decoded text without rewriting.

    ``request_id`` and ``received_at`` must come from the trusted caller so
    this function does not invent audit identity or time. The hash is always
    calculated over the original bytes before any decoding attempt.
    """

    if not isinstance(raw, bytes):
        raise TypeError("raw must be bytes")
    if not isinstance(policy, IngestPolicy):
        raise TypeError("policy must be an IngestPolicy")
    if not isinstance(request_id, str) or not request_id or request_id != request_id.strip():
        raise ValueError("request_id must be non-empty and have no surrounding whitespace")
    if not _valid_rfc3339_timestamp(received_at):
        raise ValueError("received_at must be an RFC 3339 timestamp with a timezone")
    if not isinstance(ingest_version, str) or not ingest_version or ingest_version != ingest_version.strip():
        raise ValueError("ingest_version must be non-empty and have no surrounding whitespace")

    byte_length = len(raw)
    digest = sha256(raw).hexdigest()

    def rejected(code: str) -> IngestResult:
        return IngestResult(
            status="REJECTED",
            request_id=request_id,
            received_at=received_at,
            encoding="utf-8",
            byte_length=byte_length,
            raw_sha256=digest,
            ingest_version=ingest_version,
            text=None,
            error_code=code,
        )

    if byte_length > policy.max_bytes:
        return rejected("INPUT_TOO_LARGE")
    if byte_length == 0 and not policy.allow_empty:
        return rejected("EMPTY_INPUT")

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return rejected("INVALID_UTF8")

    return IngestResult(
        status="ACCEPTED",
        request_id=request_id,
        received_at=received_at,
        encoding="utf-8",
        byte_length=byte_length,
        raw_sha256=digest,
        ingest_version=ingest_version,
        text=text,
    )


_RFC3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _valid_rfc3339_timestamp(value: object) -> bool:
    if not isinstance(value, str) or _RFC3339_TIMESTAMP.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None