-- Seed: question_bank initial symptom questions
-- Requirements: 3.4, 4.1
-- Covers 7 common symptoms with priority-ordered clarifying questions
-- Topics: duration, severity (1-10), medical conditions, medications, symptom-specific follow-ups

INSERT INTO before_doctor.question_bank (symptom, question, priority, conditions_to_ask) VALUES

-- Headache
('headache', 'How long have you been experiencing this headache?', 1, NULL),
('headache', 'On a scale of 1 to 10, how severe is your headache right now?', 2, NULL),
('headache', 'Do you have any existing medical conditions such as migraines, high blood pressure, or neurological disorders?', 3, NULL),
('headache', 'Have you taken any medication for this headache? If so, what and when?', 4, NULL),
('headache', 'Where exactly is the pain located — front, back, one side, or all over?', 5, NULL),
('headache', 'Have you experienced any visual changes, nausea, or sensitivity to light?', 6, NULL),

-- Fever
('fever', 'How long have you had a fever?', 1, NULL),
('fever', 'What is your current temperature, and on a scale of 1 to 10 how unwell do you feel?', 2, NULL),
('fever', 'Do you have any existing medical conditions or a weakened immune system?', 3, NULL),
('fever', 'Have you taken any fever-reducing medication such as paracetamol or ibuprofen?', 4, NULL),
('fever', 'Are you experiencing any other symptoms like chills, sweating, body aches, or rash?', 5, NULL),

-- Chest pain
('chest pain', 'When did the chest pain start and how long has it lasted?', 1, NULL),
('chest pain', 'On a scale of 1 to 10, how severe is the pain?', 2, NULL),
('chest pain', 'Do you have any heart conditions, high blood pressure, or a history of blood clots?', 3, NULL),
('chest pain', 'Have you taken any medication for this pain, such as aspirin or nitroglycerin?', 4, NULL),
('chest pain', 'Does the pain get worse with breathing, movement, or exertion?', 5, NULL),
('chest pain', 'Does the pain radiate to your arm, jaw, or back?', 6, NULL),

-- Abdominal pain
('abdominal pain', 'How long have you been experiencing this abdominal pain?', 1, NULL),
('abdominal pain', 'On a scale of 1 to 10, how severe is the pain?', 2, NULL),
('abdominal pain', 'Do you have any existing digestive conditions such as IBS, ulcers, or gallstones?', 3, NULL),
('abdominal pain', 'Have you taken any medication or antacids for this pain?', 4, NULL),
('abdominal pain', 'Where exactly in your abdomen is the pain — upper, lower, left, right, or all over?', 5, NULL),
('abdominal pain', 'Is the pain related to eating, and have you noticed any changes in bowel habits?', 6, '{"ask_if": {"gender": "any"}}'),

-- Cough
('cough', 'How long have you had this cough?', 1, NULL),
('cough', 'On a scale of 1 to 10, how bothersome is the cough?', 2, NULL),
('cough', 'Do you have any existing respiratory conditions such as asthma, COPD, or allergies?', 3, NULL),
('cough', 'Have you taken any cough medicine or other medication for it?', 4, NULL),
('cough', 'Is the cough dry or are you producing mucus? If so, what color is it?', 5, NULL),

-- Dizziness
('dizziness', 'How long have you been feeling dizzy?', 1, NULL),
('dizziness', 'On a scale of 1 to 10, how severe is the dizziness?', 2, NULL),
('dizziness', 'Do you have any existing conditions such as low blood pressure, anemia, or inner ear problems?', 3, NULL),
('dizziness', 'Are you currently taking any medications that might cause dizziness?', 4, NULL),
('dizziness', 'Does the dizziness occur when you stand up, change position, or is it constant?', 5, NULL),
('dizziness', 'Have you experienced any hearing changes, ringing in your ears, or fainting episodes?', 6, NULL),

-- Back pain
('back pain', 'How long have you been experiencing this back pain?', 1, NULL),
('back pain', 'On a scale of 1 to 10, how severe is the pain?', 2, NULL),
('back pain', 'Do you have any existing conditions such as a herniated disc, arthritis, or osteoporosis?', 3, NULL),
('back pain', 'Have you taken any pain medication or anti-inflammatories for it?', 4, NULL),
('back pain', 'Is the pain in your upper, middle, or lower back?', 5, NULL),
('back pain', 'Does the pain radiate to your legs, and do you have any numbness or tingling?', 6, NULL);
