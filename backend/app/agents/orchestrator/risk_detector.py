import re

from pydantic import BaseModel


class RiskResult(BaseModel):
    is_urgent: bool
    matched_patterns: list[str]


# Words/phrases that negate the symptom when they appear shortly before it.
# Allows up to ~4 intervening words (e.g. "do not have any chest pain").
_NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|don'?t|doesn'?t|didn'?t|without|never|deny|denies|denying|negative\s+for)"
    r"\s+(?:\w+\s+){0,4}$",
    re.IGNORECASE,
)

_PATTERN_DEFS: list[tuple[str, re.Pattern[str]]] = [
    ("chest pain", re.compile(r"chest\s+pain", re.IGNORECASE)),
    ("difficulty breathing", re.compile(
        r"(?:difficulty|trouble|hard\s+time|struggling)\s+breathing"
        r"|shortness\s+of\s+breath"
        r"|can'?t\s+breathe|cannot\s+breathe",
        re.IGNORECASE,
    )),
    ("stroke symptoms", re.compile(
        r"stroke\s+symptoms?"
        r"|face\s+droop(?:ing)?"
        r"|arm\s+weakness"
        r"|sudden\s+numbness"
        r"|sudden\s+confusion"
        r"|sudden\s+(?:severe\s+)?headache",
        re.IGNORECASE,
    )),
    ("seizure", re.compile(r"seizures?|convuls(?:ions?|ing)", re.IGNORECASE)),
    ("severe bleeding", re.compile(
        r"severe(?:ly)?\s+bleed(?:ing)?"
        r"|(?:uncontrolled|heavy|profuse)\s+bleed(?:ing)?",
        re.IGNORECASE,
    )),
    ("suicidal ideation", re.compile(
        r"suicid(?:al|e)"
        r"|want(?:ing)?\s+to\s+(?:die|kill\s+my\s*self|end\s+(?:my\s+)?life)"
        r"|self[- ]?harm"
        r"|hurt(?:ing)?\s+my\s*self",
        re.IGNORECASE,
    )),
    ("loss of consciousness", re.compile(
        r"loss\s+of\s+consciousness"
        r"|lost\s+consciousness"
        r"|faint(?:ed|ing)"
        r"|pass(?:ed|ing)\s+out"
        r"|black(?:ed|ing)\s+out",
        re.IGNORECASE,
    )),
]


def _is_negated(text: str, match_start: int) -> bool:
    """Return True if the text immediately before *match_start* contains a negation word."""
    prefix = text[:match_start]
    return _NEGATION_PATTERN.search(prefix) is not None


class RiskDetector:
    """Evaluates user messages for emergency symptom patterns.

    Must run before any other pipeline step (Req 8.4).
    """

    EMERGENCY_PATTERNS: list[tuple[str, re.Pattern[str]]] = _PATTERN_DEFS

    def evaluate(self, message: str) -> RiskResult:
        """Check *message* against all emergency patterns (case-insensitive).

        Returns a ``RiskResult`` with ``is_urgent=True`` when at least one
        pattern matches, along with the de-duplicated list of matched labels.
        Negated mentions (e.g. "no chest pain") are excluded.
        """
        matched: list[str] = []
        seen: set[str] = set()

        for label, pattern in self.EMERGENCY_PATTERNS:
            if label in seen:
                continue
            for m in pattern.finditer(message):
                if not _is_negated(message, m.start()):
                    matched.append(label)
                    seen.add(label)
                    break

        return RiskResult(is_urgent=bool(matched), matched_patterns=matched)
