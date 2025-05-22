import whisper
import os
import json
from datetime import datetime, time
from tqdm import tqdm
import argparse
import torch

# Vérifie si CUDA est disponible
device = "cuda" if torch.cuda.is_available() else "cpu"

# Affiche le device sélectionné
print(f"Using device: {device}")

OUTPUT_FILE = "transcription_batch.json"

model = whisper.load_model("large-v3")

def main(audio_dir, start_datetime=None, end_datetime=None):
    try:
        # Charger les transcriptions existantes si elles existent
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
        else:
            results = []

        # Conserver une liste des fichiers déjà traités
        existing = {entry["name"] for entry in results}

        for filename in tqdm(os.listdir(audio_dir)):
            if (filename.endswith(".wav") or filename.endswith(".mp3")) and filename not in existing:
                filepath = os.path.join(audio_dir, filename)
                file_creation_time = os.path.getctime(filepath)
                file_creation_datetime = datetime.fromtimestamp(file_creation_time)

                if start_datetime is None or end_datetime is None or (start_datetime <= file_creation_datetime <= end_datetime):
                    print(f"🔊 Transcription de : {filename}")
                    try:
                        result = model.transcribe(filepath, language="ht")

                        entry = {
                            "name": filename,
                            "transcription": result["text"],
                            "author": "whisper-large-v3",
                            "timestamp": datetime.utcnow().isoformat()
                        }

                        results.append(entry)

                        # Sauvegarder immédiatement après chaque transcription
                        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)

                        print(f"✅ Fichier traité : {filename}")
                        print(f"📄 Transcription : {entry['transcription']}\n")

                    except Exception as e:
                        print(f"❌ Erreur pour {filename} : {e}")

        print("\n📄 Transcriptions sauvegardées dans :", OUTPUT_FILE)

    except Exception as e:
        print(f"❌ Une erreur est survenue lors de l'exécution du script : {e}")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Batch transcribe files created within a specific time range.')
        parser.add_argument('--audio_dir', type=str, default="public/audio", help='Directory containing audio files to transcribe')
        parser.add_argument('--start_datetime', type=str, help='Start datetime of files to transcribe (YYYY-MM-DD HH:MM:SS)')
        parser.add_argument('--end_datetime', type=str, help='End datetime of files to transcribe (YYYY-MM-DD HH:MM:SS)')

        args = parser.parse_args()

        start_datetime = datetime.strptime(args.start_datetime, '%Y-%m-%d %H:%M:%S') if args.start_datetime else None
        end_datetime = datetime.strptime(args.end_datetime, '%Y-%m-%d %H:%M:%S') if args.end_datetime else None

        main(args.audio_dir, start_datetime, end_datetime)
    except Exception as e:
        print(f"❌ Une erreur est survenue lors de l'analyse des arguments : {e}")
