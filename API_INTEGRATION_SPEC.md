# Before Doctor API Integration Spec

Base URL: `https://beforedoctor.onrender.com`

Versioned API prefix: `/api/v1`

## Auth

- Header: `Authorization: Bearer <supabase_jwt>`
- In non-production env, backend falls back to a fixed user id and may allow requests without a token.

## 1) Voice -> Transcript (Required)

Endpoint: `POST /api/v1/audio/transcribe`

Content-Type: `multipart/form-data`

Form fields:
- `file` (required, file): audio file upload
- `conversation_id` (required in your integration, string UUID): use one stable ID for the full flow

Response fields:
- `message_id` (string UUID): created user message row
- `transcript_id` (string UUID): transcript row id
- `audio_url` (string URL): stored original audio URL
- `original_text` (string): STT output text
- `edited_text` (string): initially same as `original_text`

Example:

```bash
curl -X POST "https://beforedoctor.onrender.com/api/v1/audio/transcribe" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@sample.wav" \
  -F "conversation_id=3c8c4120-0f1e-4db8-8b7f-8b5134f1e6fd"
```

## 2) Edit Transcript (Required)

Endpoint: `PATCH /api/v1/transcripts/{transcript_id}`

Content-Type: `application/json`

Request body:
- `edited_text` (required, string, min 2, max 4000)

Response fields:
- `transcript_id` (string UUID)
- `edited_text` (string)

Example:

```bash
curl -X PATCH "https://beforedoctor.onrender.com/api/v1/transcripts/<transcript_id>" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"edited_text\":\"I have fever and sore throat for 2 days\"}"
```

## 3) Text/Transcript -> AI Response + TTS Audio (Required)

Endpoint: `POST /api/v1/chat/message`

Content-Type: `application/json`

Request body fields:
- `conversation_id` (required in your integration, string UUID)
- `text` (required, string, min 2, max 4000)
- `transcript_id` (required in your integration, string UUID)
- `generate_audio` (required in your integration, boolean, send `true`)

Response fields:
- `conversation_id` (string UUID)
- `user_message_id` (string UUID)
- `ai_message_id` (string UUID)
- `response` (object)
  - `summary_of_symptoms` (string)
  - `possible_causes` (string[])
  - `immediate_advice` (string[])
  - `lifestyle_suggestions` (string[])
  - `warning_signs` (string[])
  - `when_to_see_a_real_doctor` (string)
  - `medical_disclaimer` (string)
  - `follow_up_questions` (string[])
- `audio_response_url` (string | null): AI speech output URL

Example:

```bash
curl -X POST "https://beforedoctor.onrender.com/api/v1/chat/message" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{
    \"conversation_id\":\"3c8c4120-0f1e-4db8-8b7f-8b5134f1e6fd\",
    \"text\":\"I have fever and sore throat for 2 days\",
    \"transcript_id\":\"<transcript_id>\",
    \"generate_audio\":true
  }"
```

## Health Check

Endpoint: `GET /health`

Response:

```json
{ "status": "ok" }
```

## Recommended Integration Sequence

1. Generate a client-side UUID for `conversation_id`.
2. Call `POST /api/v1/audio/transcribe` with `file` + same `conversation_id`.
3. Call `PATCH /api/v1/transcripts/{transcript_id}` with final corrected `edited_text`.
4. Call `POST /api/v1/chat/message` with same `conversation_id`, final `text`, `transcript_id`, and `generate_audio:true`.
5. Use `response` for cards/UI and `audio_response_url` for playback.

## Backend Behavior Note

- Backend code still allows some fields to be omitted (`conversation_id`, `transcript_id`, `generate_audio`).
- This spec intentionally treats them as required for your external AI project integration contract.
