# Before Doctor

Before Doctor is a production-oriented AI health assistant built with Flutter, FastAPI, Supabase, and OpenAI APIs. Users can describe symptoms by text or voice, review transcripts, and receive structured pre-visit guidance with optional spoken playback.

## Architecture Diagram

```text
+--------------------+          +---------------------------+
| Flutter Mobile App |          | Supabase                  |
|--------------------|          |---------------------------|
| BLoC Presentation  |<-------->| Auth / Postgres / RLS     |
| Chat + Voice UI    |          | Storage / Realtime        |
| Audio Playback     |          +-------------+-------------+
| Dio API Client     |                        ^
+---------+----------+                        |
          | HTTPS / JWT                       |
          v                                   |
+---------+-----------------------------------+---------+
| FastAPI Backend                                       |
|-------------------------------------------------------|
| API Routes / Controllers                              |
| Security: JWT verification, rate limiting, validation |
| Services: audio, transcription, AI, TTS               |
| Doctor Agent Module                                   |
| Repositories / Database Gateway                       |
+---------+--------------------------+------------------+
          |                          |
          | OpenAI APIs              | Optional async queue
          v                          v
+---------+-------------+   +--------+----------------------+
| OpenAI API            |   | Redis / Worker               |
|-----------------------|   |------------------------------|
| gpt-4o-transcribe     |   | background TTS / retries     |
| gpt-4.1 Responses API |   | streaming / notifications    |
| gpt-4o-mini-tts       |   +------------------------------+
+-----------------------+
```

## End-to-End Flow

1. User sends text or records voice in Flutter.
2. Voice uploads to FastAPI, which stores the file in Supabase Storage.
3. Backend transcribes audio with `gpt-4o-transcribe`.
4. Transcript is stored and returned for user review/edit.
5. Edited transcript or direct text is submitted to the doctor agent.
6. `gpt-4.1` produces a structured medical-safety response.
7. Backend stores the AI response and optionally synthesizes speech with `gpt-4o-mini-tts`.
8. Flutter renders cards, conversation history, and audio controls.

## Flutter Structure

```text
lib/
  core/
    config/
    constants/
    network/
    themes/
  features/
    ai_response/
      data/
      domain/
      presentation/
    audio/
      data/
      domain/
      presentation/
    auth/
      data/
      domain/
      presentation/
    chat/
      data/
      domain/
      presentation/
    transcript/
      data/
      domain/
      presentation/
  presentation/
    bloc/
    pages/
    widgets/
  shared/
```

## Backend Structure

```text
backend/
  app/
    agents/
      doctor_agent/
    api/
      controllers/
      routes/
    core/
      config/
      constants/
      security/
    database/
    models/
    repositories/
    schemas/
    services/
      ai_service/
      audio_service/
      transcription_service/
      tts_service/
    utils/
    main.py
```

## API Design

- `POST /api/v1/audio/transcribe`
- `POST /api/v1/chat/message`
- `PATCH /api/v1/transcripts/{transcript_id}`
- `GET /health`

## UI Wireframe

```text
+------------------------------------------------------+
| Before Doctor                         profile / menu |
| "Describe symptoms before your appointment"          |
+------------------------------------------------------+
| AI safety banner: emergency symptoms -> call local   |
| emergency services immediately                        |
+------------------------------------------------------+
| [User bubble: "I have chest tightness and fatigue"]  |
|                                                      |
| [AI Card] Summary of Symptoms                        |
| [AI Card] Possible Causes                            |
| [AI Card] Immediate Advice                           |
| [AI Card] Warning Signs                              |
| [Audio controls] Play Pause Mute                     |
|                                                      |
| [Transcript editor card for voice uploads]           |
+------------------------------------------------------+
|  + text field................................. [send]|
|                                                      |
|                ((( glowing waveform )))             |
|                     [ mic button ]                  |
+------------------------------------------------------+
```

## Security

- Supabase schema `before_doctor` with RLS policies
- Bearer token verification for authenticated routes
- Request validation via Pydantic
- Rate limiting middleware hooks
- Structured disclaimers and emergency escalation language

## Deployment

- Backend: Dockerized FastAPI service deployable to Railway, AWS App Runner, Cloud Run, or ECS
- Database and storage: Supabase
- Frontend: Flutter Android and iOS builds

## OpenAI Models

- Speech-to-text: `gpt-4o-transcribe`
- AI reasoning: `gpt-4.1`
- Text-to-speech: `gpt-4o-mini-tts`

These model choices follow current OpenAI platform documentation for March 16, 2026:

- https://platform.openai.com/docs/guides/speech-to-text
- https://platform.openai.com/docs/models/gpt-4.1
- https://platform.openai.com/docs/guides/text-to-speech
