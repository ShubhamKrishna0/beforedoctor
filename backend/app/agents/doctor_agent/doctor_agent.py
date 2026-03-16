import json

from app.agents.doctor_agent.doctor_prompt import build_doctor_system_prompt
from app.agents.doctor_agent.doctor_response_formatter import normalize_doctor_response
from app.agents.doctor_agent.doctor_rules import SAFETY_RULES
from app.core.config.prompt_loader import load_prompt_config
from app.core.config.settings import get_settings
from app.services.ai_service.openai_client import get_openai_client


class DoctorAgent:
    async def generate_response(self, symptom_text: str) -> dict:
        settings = get_settings()
        prompt_config = load_prompt_config()
        client = get_openai_client()

        schema = {
            "type": "object",
            "properties": {
                "summary_of_symptoms": {"type": "string"},
                "possible_causes": {"type": "array", "items": {"type": "string"}},
                "immediate_advice": {"type": "array", "items": {"type": "string"}},
                "lifestyle_suggestions": {"type": "array", "items": {"type": "string"}},
                "warning_signs": {"type": "array", "items": {"type": "string"}},
                "when_to_see_a_real_doctor": {"type": "string"},
                "medical_disclaimer": {"type": "string"},
                "follow_up_questions": {"type": "array", "items": {"type": "string"}},
            },
            "required": prompt_config["response_sections"],
            "additionalProperties": False,
        }

        response = await client.responses.create(
            model=settings.openai_doctor_model,
            input=[
                {"role": "system", "content": build_doctor_system_prompt()},
                {
                    "role": "developer",
                    "content": "Medical safety rules:\n- " + "\n- ".join(SAFETY_RULES),
                },
                {"role": "user", "content": symptom_text},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "doctor_response",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        return normalize_doctor_response(json.loads(response.output_text))
