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
  phase text not null default 'gathering' check (phase in ('gathering', 'responding', 'follow_up')),
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

create table if not exists before_doctor.question_bank (
  id uuid primary key default gen_random_uuid(),
  symptom text not null,
  question text not null,
  priority integer not null,
  conditions_to_ask jsonb,
  created_at timestamptz not null default now()
);

create table if not exists before_doctor.user_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references before_doctor.users(id) on delete cascade,
  profile_data jsonb not null default '{}',
  updated_at timestamptz not null default now(),
  unique(user_id)
);

create table if not exists before_doctor.user_medical_memory (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references before_doctor.users(id) on delete cascade,
  fact_type text not null,
  fact_value text not null,
  source_conversation_id uuid references before_doctor.conversations(id),
  created_at timestamptz not null default now(),
  is_active boolean not null default true
);

create table if not exists before_doctor.response_feedback (
  id uuid primary key default gen_random_uuid(),
  ai_response_id uuid not null references before_doctor.ai_responses(id) on delete cascade,
  user_id uuid not null references before_doctor.users(id) on delete cascade,
  rating integer not null check (rating in (1, -1)),
  comment text,
  created_at timestamptz not null default now(),
  unique(ai_response_id, user_id)
);

create table if not exists before_doctor.conversation_pathway_state (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null unique references before_doctor.conversations(id) on delete cascade,
  pathway_code text,
  gathered_fields jsonb not null default '{}',
  current_question_code text,
  triggered_red_flags jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_before_doctor_conversations_user_id
  on before_doctor.conversations(user_id);

create index if not exists idx_before_doctor_messages_conversation_id
  on before_doctor.messages(conversation_id);

create index if not exists idx_before_doctor_transcripts_message_id
  on before_doctor.transcripts(message_id);

create index if not exists idx_before_doctor_ai_responses_message_id
  on before_doctor.ai_responses(message_id);

create index if not exists idx_question_bank_symptom
  on before_doctor.question_bank(symptom);

create index if not exists idx_medical_memory_user_active
  on before_doctor.user_medical_memory(user_id) where is_active = true;

create index if not exists idx_pathway_state_conversation
  on before_doctor.conversation_pathway_state(conversation_id);

alter table before_doctor.users enable row level security;
alter table before_doctor.conversations enable row level security;
alter table before_doctor.messages enable row level security;
alter table before_doctor.transcripts enable row level security;
alter table before_doctor.ai_responses enable row level security;
alter table before_doctor.audio_files enable row level security;
alter table before_doctor.question_bank enable row level security;
alter table before_doctor.user_profiles enable row level security;
alter table before_doctor.user_medical_memory enable row level security;
alter table before_doctor.response_feedback enable row level security;
alter table before_doctor.conversation_pathway_state enable row level security;

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

create policy "authenticated users can read question_bank"
  on before_doctor.question_bank
  for select
  to authenticated
  using (true);

create policy "service role can manage question_bank"
  on before_doctor.question_bank
  for all
  to service_role
  using (true)
  with check (true);

create policy "users manage own profile"
  on before_doctor.user_profiles
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users manage own medical memory"
  on before_doctor.user_medical_memory
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users manage own feedback"
  on before_doctor.response_feedback
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users manage own pathway state"
  on before_doctor.conversation_pathway_state
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
