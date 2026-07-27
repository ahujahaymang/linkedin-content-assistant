"""Delivery style palette for varied, non-monotonous drafting.

The drafting agent used to tie every post back to the author's work in the same
formulaic way. This module introduces variety along two independent axes:

1. Connection mode - HOW the post relates to the author. Sometimes a concrete
   work example, sometimes an experience-based opinion, sometimes a purely
   observational take with no personal tie, sometimes an analogy-led piece.
2. Emotional register - the FEEL of the writing (witty, warm, provocative, ...).

A style is picked per draft (and varied across regeneration attempts) so the
feed reads like a real person with range, not a template. Simplicity and
memorable real-world analogies are emphasised on every style, since that is the
house voice regardless of treatment.
"""

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# Connection mode -> (label, prompt directive). Weights control how often each
# is chosen. Note the deliberate spread away from "always about my work".
CONNECTION_MODES: Dict[str, Dict[str, str]] = {
    "work_example": {
        "label": "Work example",
        "directive": (
            "Ground the post in a SPECIFIC example from the author's own work "
            "history - a real situation, decision, bug, project, or trade-off. "
            "Use concrete detail (what happened, what was at stake, what changed)."
        ),
    },
    "experience_lens": {
        "label": "Experience-based take",
        "directive": (
            "Explain the topic through the lens of the author's accumulated "
            "experience and opinion - no single anecdote required. It reads like "
            "a seasoned practitioner giving their honest read, not a case study."
        ),
    },
    "pure_insight": {
        "label": "Observational insight",
        "directive": (
            "Do NOT tie this to the author's personal work. Explain the topic on "
            "its own merits with a sharp, non-obvious observation the author "
            "believes is true. The value is the clarity of the idea itself."
        ),
    },
    "analogy_led": {
        "label": "Analogy-led explanation",
        "directive": (
            "Lead with a vivid everyday analogy (cooking, traffic, sports, "
            "repairs, nature) that makes the technical idea click instantly. "
            "Personal tie is optional; the analogy carries the post."
        ),
    },
}

CONNECTION_WEIGHTS: Dict[str, float] = {
    "work_example": 0.30,
    "experience_lens": 0.30,
    "pure_insight": 0.22,
    "analogy_led": 0.18,
}


# Emotional register -> (label, prompt directive).
EMOTIONAL_REGISTERS: Dict[str, Dict[str, str]] = {
    "witty": {
        "label": "Witty",
        "directive": "Be playful and a little witty. A dry joke or clever turn of phrase is welcome - never forced or cringe.",
    },
    "warm": {
        "label": "Warm",
        "directive": "Be warm and encouraging. Speak human-to-human, with empathy for the reader's struggle.",
    },
    "provocative": {
        "label": "Provocative",
        "directive": "Take a confident, mildly contrarian stance. Challenge a common assumption - but back it up and stay respectful.",
    },
    "reflective": {
        "label": "Reflective",
        "directive": "Be reflective and a touch philosophical. Slow down and draw out the deeper lesson.",
    },
    "matter_of_fact": {
        "label": "Matter-of-fact",
        "directive": "Be direct and pragmatic. No fluff, no hype - just a clear, useful point stated plainly.",
    },
    "inspiring": {
        "label": "Inspiring",
        "directive": "Be quietly inspiring. Leave the reader a little more motivated, without slipping into empty motivation-speak.",
    },
    "curious": {
        "label": "Curious",
        "directive": "Lead with genuine curiosity. Open a question, explore it, and invite the reader to think alongside you.",
    },
}

REGISTER_WEIGHTS: Dict[str, float] = {
    "witty": 0.18,
    "warm": 0.14,
    "provocative": 0.15,
    "reflective": 0.16,
    "matter_of_fact": 0.15,
    "inspiring": 0.10,
    "curious": 0.12,
}


@dataclass
class DeliveryStyle:
    """A chosen combination of connection mode and emotional register."""
    connection_mode: str
    emotional_register: str

    @property
    def signature(self) -> str:
        return f"{self.connection_mode}:{self.emotional_register}"

    @property
    def ties_to_personal_work(self) -> bool:
        """Whether this treatment expects a personal-work connection."""
        return self.connection_mode in ("work_example", "experience_lens")

    def to_prompt_directives(self) -> str:
        conn = CONNECTION_MODES.get(self.connection_mode, {})
        reg = EMOTIONAL_REGISTERS.get(self.emotional_register, {})
        return (
            "DELIVERY STYLE FOR THIS POST (vary from your usual - commit to it):\n"
            f"- Connection mode ({conn.get('label', self.connection_mode)}): {conn.get('directive', '')}\n"
            f"- Emotional register ({reg.get('label', self.emotional_register)}): {reg.get('directive', '')}"
        )

    def describe(self) -> str:
        conn = CONNECTION_MODES.get(self.connection_mode, {}).get("label", self.connection_mode)
        reg = EMOTIONAL_REGISTERS.get(self.emotional_register, {}).get("label", self.emotional_register)
        return f"{conn} / {reg}"


def _weighted_choice(weights: Dict[str, float], rng: random.Random) -> str:
    keys = list(weights.keys())
    values = [weights[k] for k in keys]
    return rng.choices(keys, weights=values, k=1)[0]


def select_delivery_style(
    avoid_signature: Optional[str] = None,
    rng: Optional[random.Random] = None,
    max_tries: int = 6,
) -> DeliveryStyle:
    """Pick a delivery style, optionally differing from a previous one.

    Args:
        avoid_signature: A prior style ``signature`` to avoid repeating (e.g. on
            a regeneration or retry) so consecutive drafts feel different.
        rng: Optional Random instance for deterministic testing.
        max_tries: How many times to resample to avoid ``avoid_signature``.

    Returns:
        A ``DeliveryStyle``.
    """
    rng = rng or random.Random()
    style = DeliveryStyle(
        connection_mode=_weighted_choice(CONNECTION_WEIGHTS, rng),
        emotional_register=_weighted_choice(REGISTER_WEIGHTS, rng),
    )
    tries = 0
    while avoid_signature and style.signature == avoid_signature and tries < max_tries:
        style = DeliveryStyle(
            connection_mode=_weighted_choice(CONNECTION_WEIGHTS, rng),
            emotional_register=_weighted_choice(REGISTER_WEIGHTS, rng),
        )
        tries += 1
    return style
