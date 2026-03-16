from app.core.constants.response_sections import DEFAULT_RESPONSE_SECTIONS


def normalize_doctor_response(response_json: dict) -> dict:
    normalized = {}
    for section in DEFAULT_RESPONSE_SECTIONS:
        value = response_json.get(section)
        if value is None:
            normalized[section] = [] if section in {
                "possible_causes",
                "immediate_advice",
                "lifestyle_suggestions",
                "warning_signs",
                "follow_up_questions",
            } else ""
        else:
            normalized[section] = value
    return normalized
