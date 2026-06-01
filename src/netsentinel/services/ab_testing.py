"""Simple deterministic A/B routing for model comparisons."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256


@dataclass
class ABRoute:
    variant: str
    model_id: str
    traffic_percentage: float

    def to_dict(self) -> dict:
        return asdict(self)


class ABTestingService:
    """Route traffic between two model IDs with sticky hashing."""

    def __init__(self, model_a: str, model_b: str, model_b_percentage: float = 0.1) -> None:
        if not 0 <= model_b_percentage <= 1:
            raise ValueError("model_b_percentage must be between 0 and 1.")
        self.model_a = model_a
        self.model_b = model_b
        self.model_b_percentage = model_b_percentage

    def route(self, entity_id: str) -> ABRoute:
        digest = sha256(entity_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) / 0xFFFFFFFF
        if bucket < self.model_b_percentage:
            return ABRoute("B", self.model_b, self.model_b_percentage)
        return ABRoute("A", self.model_a, 1 - self.model_b_percentage)
