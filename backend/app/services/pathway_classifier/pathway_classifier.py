"""LLM-based classifier that maps symptom text to a pathway code."""

from __future__ import annotations

import logging

from app.services.ai_service.openai_client import get_openai_client

logger = logging.getLogger(__name__)

_PATHWAY_DESCRIPTIONS: dict[str, str] = {
    "fever": "Fever and febrile illness intake",
    "respiratory": "Cough, congestion, wheeze, breathing concerns",
    "vomiting_diarrhea": "GI symptom intake",
    "rash_skin": "Rash and skin reaction intake",
    "medication_reaction": "Medication-related reaction intake",
    "abdominal_pain": "Stomachache, belly pain, possible appendicitis patterns",
    "allergic_reaction": "Food, insect, or environmental allergy — hives, swelling, breathing symptoms",
    "newborn_concern": "Infants under ~3 months — feeding, jaundice, fever, breathing",
    "seizure_neurological": "First or repeated seizure, febrile seizure, prolonged episode",
    "chest_pain": "Chest pain, palpitations, or syncope",
    "poisoning_ingestion": "Accidental ingestion of medications, household chemicals, plants, or unknown substances",
}


def _build_system_prompt(available_pathways: list[str]) -> str:
    """Build a system prompt listing only the available pathway codes."""
    lines = [
        "You are a medical pathway classifier. Given a parent's description of "
        "their child's symptoms, select the single best-matching pathway code "
        "from the list below.",
        "",
        "Available pathways:",
    ]
    for code in available_pathways:
        desc = _PATHWAY_DESCRIPTIONS.get(code, code)
        lines.append(f"  - {code}: {desc}")
    lines.append("")
    lines.append(
        "Reply with ONLY the pathway code (e.g. 'fever'). "
        "Do not include any other text, explanation, or punctuation."
    )
    return "\n".join(lines)


class PathwayClassifier:
    """Single LLM call that maps symptom text to a pathway_code."""

    async def classify(
        self,
        symptom_text: str,
        available_pathways: list[str],
    ) -> str | None:
        """Classify *symptom_text* into one of *available_pathways*.

        Returns the pathway code when the LLM output matches a known code,
        otherwise ``None``.  Also returns ``None`` on any LLM failure.
        """
        if not symptom_text or not available_pathways:
            return None

        try:
            client = get_openai_client()
            response = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": _build_system_prompt(available_pathways),
                    },
                    {"role": "user", "content": symptom_text},
                ],
                temperature=0.0,
            )
            raw = (response.choices[0].message.content or "").strip().lower()

            if raw in available_pathways:
                return raw

            logger.warning(
                "PathwayClassifier: LLM returned '%s' which is not a known pathway code",
                raw,
            )
            return None
        except Exception:
            logger.exception("PathwayClassifier: LLM call failed")
            return None
