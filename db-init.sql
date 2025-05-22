CREATE TABLE IF NOT EXISTS transcriptions (
  id SERIAL PRIMARY KEY,
  filename TEXT NOT NULL,
  transcription TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT now()
);