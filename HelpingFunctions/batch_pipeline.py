import whisper
import os
import sys
import json
import logging

import psycopg2
from dotenv import load_dotenv

# Importer tes fonctions existantes
from batch_vocal_extract_demucs import extract_vocals
from batch_diarization import load_pipeline_diarization, detect_file_type, extract_audio, diarize_audio
import batch_transcribe   # Remplace "from batch_transcribe import main as transcribe_main"
from batch_remove_short_wav import delete_short_audio_files

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Charger le modèle Whisper et l'injecter dans le module batch_transcribe
model = whisper.load_model("large-v3")
batch_transcribe.model = model

def insert_transcription(conn, name, transcription, timestamp, author):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transcriptions (filename, transcription, timestamp, author)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (filename) DO NOTHING;
            """,
            (name, transcription, timestamp, author)
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

    # 4. Transcription et update DB
    diarized_files = [os.path.join(diarized_dir, f) for f in os.listdir(diarized_dir) if f.endswith(".mp3") or f.endswith(".wav")]
    transcriptions = []
    for df in diarized_files:
        output_file = df + ".json"
        # Utilisation de batch_transcribe.main() qui va utiliser la variable global model injectée
        batch_transcribe.main(audio_dir=os.path.dirname(df), output_file=output_file)
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                transcriptions.extend(data)

    # 5. Update DB
    conn = psycopg2.connect(DATABASE_URL)
    for entry in transcriptions:
        insert_transcription(conn, entry["name"], entry["transcription"], entry.get("timestamp"), entry.get("author", "whisper"))
    conn.close()
    print("Pipeline terminé.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline audio : extraction, diarization, transcription, update DB")
    parser.add_argument("audio_file", help="Fichier audio à traiter")
    parser.add_argument("--output_dir", default="pipeline_tmp", help="Répertoire de destination des fichiers intermédiaires (vocals, diarized, etc.)")

    args = parser.parse_args()

    pipeline(args.audio_file, args.output_dir)