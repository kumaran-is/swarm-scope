"""Seeded random and reproducibility helpers."""

import random


def make_random_gen(seed: int) -> random.Random:
    """Create a deterministic random generator from a seed."""
    return random.Random(seed)


def seeded_choice(items: list, rng: random.Random):
    """Pick a random item using the seeded generator."""
    if not items:
        raise ValueError("Cannot pick from empty list")
    return items[rng.randint(0, len(items) - 1)]
