import whisper
import os
import sys
import json
import logging
from datetime import datetime
from tqdm import tqdm


import psycopg2
from dotenv import load_dotenv

# Importer tes fonctions existantes
from batch_vocal_extract_demucs import extract_vocals
from batch_diarization import load_pipeline_diarization, detect_file_type, extract_audio, diarize_audio
from batch_remove_short_wav import delete_short_audio_files

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Charger le modèle Whisper
model = whisper.load_model("large-v3")

def transcribe_file(file_path):
    """Transcrit un seul fichier avec Whisper et retourne la liste des entrées JSON (1 élément)."""
    print(f"🔊 Transcription de : {os.path.basename(file_path)}")
    result = model.transcribe(file_path, language="ht")
    entry = {
        "name": os.path.basename(file_path),
        "transcription": result["text"],
        "timestamp": datetime.utcnow().isoformat(),
        "author": "whisper-large-v3"
    }
    print(f"🗣️ Transcription: {entry['transcription']}")
    return [entry]

def insert_transcription(conn, name, transcription, timestamp, author, created_at):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transcriptions (filename, transcription, timestamp, author, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (filename) DO NOTHING;
            """,
            (name, transcription, timestamp, author, created_at)
        )
        conn.commit()

def pipeline(audio_file, temp_dir, diarization_model_name="pyannote/speaker-diarization-3.1"):
    # 1. Extraction vocale
    vocals_dir = os.path.join(temp_dir, "vocals")
    os.makedirs(vocals_dir, exist_ok=True)
    extract_vocals(audio_file, vocals_dir)
    vocals_files = [os.path.join(vocals_dir, f) for f in os.listdir(vocals_dir) if f.endswith(".mp3") or f.endswith(".wav")]
    if not vocals_files:
        print("Aucun fichier vocal extrait.")
        return

    # 2. Diarization
    diarized_dir = os.path.join(temp_dir, "diarized")
    os.makedirs(diarized_dir, exist_ok=True)
    diarization_model = load_pipeline_diarization(diarization_model_name)
    for vf in vocals_files:
        file_extension, file_type = detect_file_type(vf)
        audio = extract_audio(vf, file_extension, file_type)
        diarize_audio(vf, diarization_model, diarized_dir)

    # 3. Suppression des fichiers < 2 secondes
    delete_short_audio_files(diarized_dir, min_duration=2.0)

    # Transcrire et mettre à jour DB fichier par fichier
    conn = psycopg2.connect(DATABASE_URL)
    diarized_files = [
        os.path.join(diarized_dir, f)
        for f in os.listdir(diarized_dir)
        if f.endswith((".mp3", ".wav"))
    ]
    for df in tqdm(diarized_files, desc="Segments à transcrire"):
        try:
            entries = transcribe_file(df)
            created_at = datetime.fromtimestamp(os.path.getctime(df)).isoformat()  # Date de création du fichier
            for entry in entries:
                try:
                    insert_transcription(
                        conn,
                        entry["name"],
                        entry["transcription"],
                        entry["timestamp"],
                        entry["author"],
                        created_at
                    )
                    print(f"✅ Transcription insérée dans la db pour {entry['name']}")
                except psycopg2.errors.UniqueViolation:
                    print(f"⚠️ Doublon ignoré pour {entry['name']}")
                    conn.rollback()
        except Exception as e:
            print(f"❌ Erreur globale sur {os.path.basename(df)} : {e}")
            conn.rollback()
    conn.close()
    print("Pipeline terminé.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline audio : extraction, diarization, transcription, update DB")
    parser.add_argument("audio_file", help="Fichier audio à traiter")
    parser.add_argument("--output_dir", default="pipeline_tmp", help="Répertoire de destination des fichiers intermédiaires (vocals, diarized, etc.)")

    args = parser.parse_args()

    pipeline(args.audio_file, args.output_dir)