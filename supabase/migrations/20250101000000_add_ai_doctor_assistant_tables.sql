-- Migration: Add AI Doctor Assistant tables and columns
-- Requirements: 4.1, 4.2, 10.4, 11.1, 12.2, 12.4, 14.2

-- 1. Add phase column to conversations
ALTER TABLE before_doctor.conversations
  ADD COLUMN IF NOT EXISTS phase text NOT NULL DEFAULT 'gathering'
  CHECK (phase IN ('gathering', 'responding', 'follow_up'));

-- 2. Create question_bank table
CREATE TABLE IF NOT EXISTS before_doctor.question_bank (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  symptom text NOT NULL,
  question text NOT NULL,
  priority integer NOT NULL,
  conditions_to_ask jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_question_bank_symptom
  ON before_doctor.question_bank(symptom);

-- 3. Create user_profiles table
CREATE TABLE IF NOT EXISTS before_doctor.user_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES before_doctor.users(id) ON DELETE CASCADE,
  profile_data jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

-- 4. Create user_medical_memory table
CREATE TABLE IF NOT EXISTS before_doctor.user_medical_memory (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES before_doctor.users(id) ON DELETE CASCADE,
  fact_type text NOT NULL,
  fact_value text NOT NULL,
  source_conversation_id uuid REFERENCES before_doctor.conversations(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  is_active boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_medical_memory_user_active
  ON before_doctor.user_medical_memory(user_id) WHERE is_active = true;

-- 5. Create response_feedback table
CREATE TABLE IF NOT EXISTS before_doctor.response_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ai_response_id uuid NOT NULL REFERENCES before_doctor.ai_responses(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES before_doctor.users(id) ON DELETE CASCADE,
  rating integer NOT NULL CHECK (rating IN (1, -1)),
  comment text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(ai_response_id, user_id)
);

-- 6. Enable RLS on all new tables
ALTER TABLE before_doctor.question_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE before_doctor.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE before_doctor.user_medical_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE before_doctor.response_feedback ENABLE ROW LEVEL SECURITY;

-- 7. RLS policies for question_bank
-- Authenticated users can read
CREATE POLICY "authenticated users can read question_bank"
  ON before_doctor.question_bank
  FOR SELECT
  TO authenticated
  USING (true);

-- Service role can write
CREATE POLICY "service role can manage question_bank"
  ON before_doctor.question_bank
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 8. RLS policies for user_profiles
CREATE POLICY "users manage own profile"
  ON before_doctor.user_profiles
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 9. RLS policies for user_medical_memory
CREATE POLICY "users manage own medical memory"
  ON before_doctor.user_medical_memory
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 10. RLS policies for response_feedback
CREATE POLICY "users manage own feedback"
  ON before_doctor.response_feedback
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
