import whisper
import os
from datetime import datetime
from tqdm import tqdm

import argparse

import psycopg2
from dotenv import load_dotenv

# Importer tes fonctions existantes
from batch_vocal_extract_demucs import extract_vocals
from batch_diarization import load_pipeline_diarization, detect_file_type, extract_audio, diarize_audio
from batch_remove_short_wav import delete_short_audio_files

import logging
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, ID3NoHeaderError

# Configurer les logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Charger le modèle Whisper
logging.info("Chargement du modèle Whisper...")
model = whisper.load_model("large-v3")
logging.info("Modèle Whisper chargé avec succès.")

def transcribe_file(file_path):
    """Transcrit un seul fichier avec Whisper et retourne la liste des entrées JSON (1 élément)."""
    logging.info(f"🔊 Début de la transcription pour : {os.path.basename(file_path)}")
    result = model.transcribe(file_path, language="ht")
    entry = {
        "name": os.path.basename(file_path),
        "transcription": result["text"],
        "timestamp": datetime.utcnow().isoformat(),
        "author": "whisper-large-v3"
    }
    logging.info(f"🗣️ Transcription terminée pour {entry['name']}: {entry['transcription']}")
    return [entry]

def insert_transcription(conn, filename, transcription, timestamp, author, created_at):
    with conn.cursor() as cur:
        try:
            logging.info(f"Insertion dans fichiers_audio pour : {filename}")
            cur.execute(
                """
                INSERT INTO fichiers_audio (chemin)
                VALUES (%s)
                ON CONFLICT (chemin) DO UPDATE SET chemin = EXCLUDED.chemin
                RETURNING id;
                """,
                (filename,)
            )
            file_id = cur.fetchone()[0]

            logging.info(f"Insertion dans contributeur pour : {author}")
            cur.execute(
                """
                INSERT INTO contributeur (nom)
                VALUES (%s)
                ON CONFLICT (nom) DO UPDATE SET nom = EXCLUDED.nom
                RETURNING id;
                """,
                (author,)
            )
            contrib_id = cur.fetchone()[0]

            logging.info(f"Insertion dans transcription pour : {filename}")
            cur.execute(
                """
                INSERT INTO transcription (id_fichier_audio, id_contributeur, texte, date_creation)
                VALUES (%s, %s, %s, %s);
                """,
                (file_id, contrib_id, transcription, created_at)
            )

            conn.commit()
            logging.info(f"✅ Transcription insérée avec succès pour : {filename}")
        except Exception as e:
            conn.rollback()
            logging.error(f"❌ Erreur lors de l'insertion pour {filename} : {e}")

def pipeline(audio_file, temp_dir, diarization_model_name="pyannote/speaker-diarization-3.1"):
    logging.info(f"Début du pipeline pour le fichier : {audio_file}")
    
    # 1. Extraction vocale
    vocals_dir = os.path.join(temp_dir, "vocals")
    os.makedirs(vocals_dir, exist_ok=True)
    logging.info(f"Dossier vocals créé : {vocals_dir}")
    try:
        extract_vocals(audio_file, vocals_dir)
        logging.info(f"Extraction des vocaux terminée pour : {audio_file}")
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'extraction des vocaux pour {audio_file} : {e}")
        return
    
    vocals_files = [os.path.join(vocals_dir, f) for f in os.listdir(vocals_dir) if f.endswith(".mp3") or f.endswith(".wav")]
    if not vocals_files:
        logging.warning("Aucun fichier vocal extrait.")
        return

    # 2. Diarization
    diarized_dir = os.path.join(temp_dir, "diarized")
    os.makedirs(diarized_dir, exist_ok=True)
    logging.info(f"Dossier diarized créé : {diarized_dir}")
    try:
        diarization_model = load_pipeline_diarization(diarization_model_name)
        logging.info("Pipeline de diarization chargé.")
    except Exception as e:
        logging.error(f"❌ Erreur lors du chargement du pipeline de diarization : {e}")
        return
    
    for vf in vocals_files:
        try:
            file_extension, file_type = detect_file_type(vf)
            audio = extract_audio(vf, file_extension, file_type)
            diarize_audio(vf, diarization_model, diarized_dir)
            logging.info(f"Diarization terminée pour : {vf}")
        except Exception as e:
            logging.error(f"❌ Erreur lors de la diarization pour {vf} : {e}")
    
    # 3. Suppression des fichiers < 2 secondes
    try:
        delete_short_audio_files(diarized_dir, min_duration=2.0)
        logging.info("Suppression des fichiers < 2 secondes terminée.")
    except Exception as e:
        logging.error(f"❌ Erreur lors de la suppression des fichiers courts : {e}")
    
    # Transcrire et mettre à jour DB fichier par fichier
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        logging.info("Connexion à la base de données établie.")
    except Exception as e:
        logging.error(f"❌ Erreur lors de la connexion à la base de données : {e}")
        return
    
    diarized_files = [
        os.path.join(diarized_dir, f)
        for f in os.listdir(diarized_dir)
        if f.endswith((".mp3", ".wav"))
    ]
    for df in tqdm(diarized_files, desc="Segments à transcrire"):
        try:
            entries = transcribe_file(df)
            created_at = datetime.fromtimestamp(os.path.getctime(df)).isoformat()
            for entry in entries:
                # Ajouter la transcription dans le tag ID3 'USLT' (Unsynchronized Lyrics/Text)
                try:
                    if df.lower().endswith(".mp3"):
                        # Charger ou créer les tags ID3
                        try:
                            id3_tags = ID3(df)
                        except ID3NoHeaderError:
                            id3_tags = ID3()
                            
                        # Ajouter la transcription comme paroles non synchronisées
                        id3_tags.add(USLT(
                            encoding=3,  # UTF-8
                            lang='ht',  # Code langue pour le texte
                            desc='Transcription',
                            text=entry["transcription"]
                        ))
                        
                        # Sauvegarder les modifications
                        id3_tags.save(df)
                        logging.info(f"✅ Transcription ajoutée aux tags ID3 pour {os.path.basename(df)}")
                except Exception as tag_e:
                    logging.error(f"❌ Erreur lors de l'ajout des tags ID3 à {os.path.basename(df)}: {tag_e}")
                try:
                    insert_transcription(
                        conn,
                        entry["name"],
                        entry["transcription"],
                        entry["timestamp"],
                        entry["author"],
                        created_at
                    )
                except psycopg2.errors.UniqueViolation:
                    logging.warning(f"⚠️ Doublon ignoré pour : {entry['name']}")
                    conn.rollback()
        except Exception as e:
            logging.error(f"❌ Erreur globale sur {os.path.basename(df)} : {e}")
            conn.rollback()
    conn.close()
    logging.info("Connexion à la base de données fermée.")
    logging.info(f"Pipeline terminé pour le fichier : {audio_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline audio : extraction, diarization, transcription, update DB")
    parser.add_argument("input_path", help="Fichier audio ou répertoire à traiter")
    parser.add_argument("--output_dir", default="pipeline_tmp", help="Répertoire de destination des fichiers intermédiaires (vocals, diarized, etc.)")
    args = parser.parse_args()

    input_path = args.input_path
    if os.path.isdir(input_path):
        files = [fname for fname in sorted(os.listdir(input_path)) if fname.lower().endswith((".mp3", ".wav"))]
        for fname in tqdm(files, desc="Fichiers à traiter"):
            file_path = os.path.join(input_path, fname)
            logging.info(f"▶️ Traitement de {file_path}")
            pipeline(file_path, args.output_dir)
    else:
        logging.info(f"▶️ Traitement de {input_path}")
        pipeline(input_path, args.output_dir)