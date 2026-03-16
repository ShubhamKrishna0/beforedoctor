create schema if not exists before_doctor;

create extension if not exists "pgcrypto";

create table if not exists before_doctor.users (
  id uuid primary key,
  email text unique not null,
  created_at timestamptz not null default now(),
  subscription text not null default 'free'
);

create table if not exists before_doctor.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references before_doctor.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists before_doctor.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references before_doctor.conversations(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  text text,
  audio_url text,
  created_at timestamptz not null default now()
);

create table if not exists before_doctor.transcripts (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references before_doctor.messages(id) on delete cascade,
  original_text text not null,
  edited_text text not null,
  created_at timestamptz not null default now()
);

create table if not exists before_doctor.ai_responses (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references before_doctor.messages(id) on delete cascade,
  response_json jsonb not null,
  audio_response_url text,
  created_at timestamptz not null default now()
);

create table if not exists before_doctor.audio_files (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references before_doctor.users(id) on delete cascade,
  audio_url text not null,
  duration numeric(10,2),
  created_at timestamptz not null default now()
);

create index if not exists idx_before_doctor_conversations_user_id
  on before_doctor.conversations(user_id);

create index if not exists idx_before_doctor_messages_conversation_id
  on before_doctor.messages(conversation_id);

create index if not exists idx_before_doctor_transcripts_message_id
  on before_doctor.transcripts(message_id);

create index if not exists idx_before_doctor_ai_responses_message_id
  on before_doctor.ai_responses(message_id);

alter table before_doctor.users enable row level security;
alter table before_doctor.conversations enable row level security;
alter table before_doctor.messages enable row level security;
alter table before_doctor.transcripts enable row level security;
alter table before_doctor.ai_responses enable row level security;
alter table before_doctor.audio_files enable row level security;

create policy "users can view self"
  on before_doctor.users
  for select
  using (auth.uid() = id);

create policy "users manage own conversations"
  on before_doctor.conversations
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users manage own messages"
  on before_doctor.messages
  for all
  using (
    exists (
      select 1
      from before_doctor.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from before_doctor.conversations c
      where c.id = conversation_id and c.user_id = auth.uid()
    )
  );

create policy "users manage own transcripts"
  on before_doctor.transcripts
  for all
  using (
    exists (
      select 1
      from before_doctor.messages m
      join before_doctor.conversations c on c.id = m.conversation_id
      where m.id = message_id and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from before_doctor.messages m
      join before_doctor.conversations c on c.id = m.conversation_id
      where m.id = message_id and c.user_id = auth.uid()
    )
  );

create policy "users manage own ai responses"
  on before_doctor.ai_responses
  for all
  using (
    exists (
      select 1
      from before_doctor.messages m
      join before_doctor.conversations c on c.id = m.conversation_id
      where m.id = message_id and c.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from before_doctor.messages m
      join before_doctor.conversations c on c.id = m.conversation_id
      where m.id = message_id and c.user_id = auth.uid()
    )
  );

create policy "users manage own audio files"
  on before_doctor.audio_files
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
