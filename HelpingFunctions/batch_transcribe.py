import whisper
import os
import json
from datetime import datetime, time
from tqdm import tqdm
import argparse
import torch
import mutagen
from mutagen.id3 import ID3, USLT, ID3NoHeaderError

# Vérifie si CUDA est disponible
device = "cuda" if torch.cuda.is_available() else "cpu"

# Affiche le device sélectionné
print(f"Using device: {device}")

def main(audio_dir, start_datetime=None, end_datetime=None, output_file="transcription_batch.json"):
    try:
        # Charger les transcriptions existantes si elles existent
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
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
                        transcription_text = result["text"]
                        entry = {
                            "name": filename,
                            "transcription": transcription_text,
                            "author": "whisper-large-v3",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        results.append(entry)

                        # Si MP3, écrire la transcription dans les tags ID3 (lyrics)
                        if filename.endswith(".mp3"):
                            try:
                                try:
                                    tags = ID3(filepath)
                                except ID3NoHeaderError:
                                    tags = ID3()
                                tags.delall("USLT")
                                tags.add(USLT(encoding=3, lang=u'eng', desc=u'Lyrics', text=transcription_text))
                                tags.save(filepath)
                                print(f"🎵 Lyrics tag ajouté à {filename}")
                            except Exception as tag_err:
                                print(f"⚠️ Erreur lors de l'écriture des tags ID3 pour {filename} : {tag_err}")

                        # Sauvegarder immédiatement après chaque transcription
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)

                        print(f"✅ Fichier traité : {filename}")
                        print(f"📄 Transcription : {entry['transcription']}\n")

                    except Exception as e:
                        print(f"❌ Erreur pour {filename} : {e}")

        print("\n📄 Transcriptions sauvegardées dans :", output_file)

    except Exception as e:
        print(f"❌ Une erreur est survenue lors de l'exécution du script : {e}")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Batch transcribe files created within a specific time range.')
        parser.add_argument('--audio_dir', type=str, default="public/audio", help='Directory containing audio files to transcribe')
        parser.add_argument('--start_datetime', type=str, help='Start datetime of files to transcribe (YYYY-MM-DD HH:MM:SS)')
        parser.add_argument('--end_datetime', type=str, help='End datetime of files to transcribe (YYYY-MM-DD HH:MM:SS)')
        parser.add_argument('--output_file', type=str, default="transcription_batch.json", help='Nom du fichier JSON de sortie pour les transcriptions')

        args = parser.parse_args()

        start_datetime = datetime.strptime(args.start_datetime, '%Y-%m-%d %H:%M:%S') if args.start_datetime else None
        end_datetime = datetime.strptime(args.end_datetime, '%Y-%m-%d %H:%M:%S') if args.end_datetime else None

        model = whisper.load_model("large-v3")
        main(args.audio_dir, start_datetime, end_datetime, args.output_file)
    except Exception as e:
        print(f"❌ Une erreur est survenue lors de l'analyse des arguments : {e}")
