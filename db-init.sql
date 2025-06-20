CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    transcription TEXT NOT NULL,
    rating SMALLINT DEFAULT 0,
    timestamp TIMESTAMPTZ DEFAULT now(),
    author TEXT DEFAULT 'whisper-large-v3',
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_filename_transcription UNIQUE (filename, transcription)
);
