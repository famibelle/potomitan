import os
import psycopg2
import whisper
import argparse
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def upsert_file(cur, filename):
    """Insert or get ID from fichiers_audio."""
    cur.execute(
        """
        INSERT INTO fichiers_audio (chemin)
        VALUES (%s)
        ON CONFLICT (chemin) DO NOTHING
        RETURNING id
        """,
        (filename,)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("SELECT id FROM fichiers_audio WHERE chemin = %s", (filename,))
    return cur.fetchone()[0]

def has_transcription(cur, file_id):
    """Vérifie si une transcription existe pour file_id."""
    cur.execute(
        "SELECT 1 FROM transcription WHERE id_fichier_audio = %s LIMIT 1",
        (file_id,)
    )
    return cur.fetchone() is not None

def insert_transcription(cur, file_id, texte):
    """Insère une nouvelle transcription vide ou générée."""
    cur.execute(
        """
        INSERT INTO transcription (id_fichier_audio, texte, date_creation)
        VALUES (%s, %s, %s)
        """,
        (file_id, texte, datetime.utcnow())
    )

def main(audio_dir, model_name, language, dry_run):
    # Charger Whisper
    model = whisper.load_model(model_name)
    # Ouvrir connexion
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    try:
        with conn.cursor() as cur:
            files = sorted(f for f in os.listdir(audio_dir)
                           if f.lower().endswith(('.mp3', '.wav')))
            missing_transcriptions = 0
            for fname in tqdm(files, desc="Fichiers audio"):
                full = os.path.join(audio_dir, fname)
                # Upsert fichier_audio
                file_id = upsert_file(cur, fname)
                # Si déjà transcrit, on skip
                if has_transcription(cur, file_id):
                    continue
                missing_transcriptions += 1
                if dry_run:
                    print(f"🟡 Fichier sans transcription : {fname}")
                    continue
                # Transcrire
                print(f"🔊 Transcription de {fname}")
                res = model.transcribe(full, language=language)
                texte = res.get("text", "").strip()
                # Insérer transcription
                insert_transcription(cur, file_id, texte)
                conn.commit()
                print(f"✅ Transcription enregistrée pour {fname}")
            if dry_run:
                print(f"✅ Dry-run terminé. {missing_transcriptions} fichier(s) sans transcription.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur : {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch transcribe audio files into DB if not already done."
    )
    parser.add_argument(
        "--audio-dir",
        default="public/audio",
        help="Répertoire contenant les fichiers audio (default: public/audio)."
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        help="Nom du modèle Whisper à utiliser (default: large-v3)."
    )
    parser.add_argument(
        "--language",
        default="ht",
        help="Code langue pour Whisper (default: ht)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule la transcription sans insérer dans la base de données."
    )
    args = parser.parse_args()
    main(args.audio_dir, args.model, args.language, args.dry_run)