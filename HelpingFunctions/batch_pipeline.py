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

import torch

# Configurer les logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)

print("📋 Configuration des logs terminée")
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"📝 Variable d'environnement DATABASE_URL : {'Configurée' if DATABASE_URL else 'NON configurée'}")

# Charger le modèle Whisper
print("🔄 Chargement du modèle Whisper en cours...")
logging.info("Chargement du modèle Whisper...")
model = whisper.load_model("large-v3-turbo") #openai/whisper-large-v3-turbo
print("✅ Modèle Whisper chargé avec succès")
logging.info("Modèle Whisper chargé avec succès.")

def transcribe_file(file_path):
    """Transcrit un seul fichier avec Whisper et retourne la liste des entrées JSON (1 élément)."""
    print(f"🔊 Transcription en cours: {os.path.basename(file_path)}")
    logging.info(f"🔊 Début de la transcription pour : {os.path.basename(file_path)}")
    result = model.transcribe(file_path, language="ht")
    entry = {
        "name": os.path.basename(file_path),
        "transcription": result["text"],
        "timestamp": datetime.utcnow().isoformat(),
        "author": "whisper-large-v3"
    }
    print(f"✅ Transcription terminée: {os.path.basename(file_path)}")
    print(f"🗣️ Transcription terminée pour {entry['name']}: {entry['transcription']}")
    logging.info(f"🗣️ Transcription terminée pour {entry['name']}: {entry['transcription']}")
    return [entry]

def insert_transcription(conn, filename, transcription, timestamp, author, created_at):
    with conn.cursor() as cur:
        try:
            print(f"📥 Insertion dans fichiers_audio: {filename}")
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

            print(f"📥 Insertion dans contributeur: {author}")
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

            print(f"📥 Insertion dans transcription: {filename}")
            logging.info(f"Insertion dans transcription pour : {filename}")
            cur.execute(
                """
                INSERT INTO transcription (id_fichier_audio, id_contributeur, texte, date_creation)
                VALUES (%s, %s, %s, %s);
                """,
                (file_id, contrib_id, transcription, created_at)
            )

            conn.commit()
            print(f"✅ Transcription insérée: {filename}")
            logging.info(f"✅ Transcription insérée avec succès pour : {filename}")
        except Exception as e:
            conn.rollback()
            print(f"❌ ERREUR insertion {filename}: {e}")
            logging.error(f"❌ Erreur lors de l'insertion pour {filename} : {e}")

def pipeline(audio_file, temp_dir, diarization_model_name="pyannote/speaker-diarization-3.1"):
    print(f"\n🚀 DÉMARRAGE PIPELINE: {audio_file}")
    logging.info(f"Début du pipeline pour le fichier : {audio_file}")
    
    # 1. Extraction vocale
    vocals_dir = os.path.join(temp_dir, "vocals")
    os.makedirs(vocals_dir, exist_ok=True)
    print(f"📁 Dossier créé: {vocals_dir}")
    logging.info(f"Dossier vocals créé : {vocals_dir}")
    try:
        print(f"🎵 Extraction vocale en cours: {audio_file}")
        extract_vocals(audio_file, vocals_dir)
        print(f"✅ Extraction vocale terminée: {audio_file}")
        
        # Libération mémoire après extraction vocale
        import gc
        import torch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()
        print("🧹 Mémoire libérée après extraction vocale")
        logging.info("Mémoire libérée après extraction vocale")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        logging.error(f"❌ Erreur lors de l'extraction vocale : {e}")
        return
    
    vocals_files = [os.path.join(vocals_dir, f) for f in os.listdir(vocals_dir) if f.endswith(".mp3") or f.endswith(".wav")]
    if not vocals_files:
        print("⚠️ Aucun fichier vocal extrait!")
        logging.warning("Aucun fichier vocal extrait.")
        return

    # 2. Diarization
    diarized_dir = os.path.join(temp_dir, "diarized")
    os.makedirs(diarized_dir, exist_ok=True)
    print(f"📁 Dossier créé: {diarized_dir}")
    logging.info(f"Dossier diarized créé : {diarized_dir}")
    
    try:
        print("🔄 Chargement modèle diarization...")
        diarization_model = load_pipeline_diarization(diarization_model_name)
        print("✅ Modèle diarization chargé")
        logging.info("Pipeline de diarization chargé.")
        
        for vf in vocals_files:
            try:
                print(f"🎙️ Diarization en cours: {os.path.basename(vf)}")
                file_extension, file_type = detect_file_type(vf)
                audio = extract_audio(vf, file_extension, file_type)
                diarize_audio(vf, diarization_model, diarized_dir)
                print(f"✅ Diarization terminée: {os.path.basename(vf)}")
                logging.info(f"Diarization terminée pour : {vf}")
            except Exception as e:
                print(f"❌ ERREUR diarization {os.path.basename(vf)}: {e}")
                logging.error(f"❌ Erreur lors de la diaration pour {vf} : {e}")
        
        # Libération mémoire après diarisation
        del diarization_model
        import gc
        import torch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()
        print("🧹 Mémoire libérée après diarisation")
        logging.info("Mémoire libérée après diarisation")
        
        # NOUVEAU: Nettoyer les fichiers vocaux intermédiaires après diarisation
        cleanup_vocal_files(vocals_dir)
        
    except Exception as e:
        print(f"❌ ERREUR chargement diarization: {e}")
        logging.error(f"❌ Erreur lors du chargement du pipeline de diarization : {e}")
        return
    
    # 3. Suppression des fichiers < 2 secondes
    try:
        print("🔍 Suppression des fichiers < 2 secondes...")
        delete_short_audio_files(diarized_dir, min_duration=2.0)
        print("✅ Suppression terminée")
        logging.info("Suppression des fichiers < 2 secondes terminée.")
    except Exception as e:
        print(f"❌ ERREUR suppression fichiers courts: {e}")
        logging.error(f"❌ Erreur lors de la suppression des fichiers courts : {e}")
    
    # Transcrire et mettre à jour DB fichier par fichier
    try:
        print("🔄 Connexion à la base de données...")
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        print("✅ Connexion BDD établie")
        logging.info("Connexion à la base de données établie.")
    except Exception as e:
        print(f"❌ ERREUR connexion BDD: {e}")
        logging.error(f"❌ Erreur lors de la connexion à la base de données : {e}")
        return
    
    diarized_files = [
        os.path.join(diarized_dir, f)
        for f in os.listdir(diarized_dir)
        if f.endswith((".mp3", ".wav"))
    ]
    print(f"📊 {len(diarized_files)} segments à transcrire")
    
    # Récupérer une référence au modèle global
    global model
    
    # Traiter les segments par lots pour économiser la mémoire
    batch_size = 5  # Adapter selon votre mémoire disponible
    for i in range(0, len(diarized_files), batch_size):
        batch = diarized_files[i:i+batch_size]
        
        for df in tqdm(batch, desc=f"Segments à transcrire (lot {i//batch_size + 1}/{(len(diarized_files)-1)//batch_size + 1})"):
            try:
                entries = transcribe_file(df)
                created_at = datetime.fromtimestamp(os.path.getctime(df)).isoformat()
                for entry in entries:
                    # Tags ID3
                    try:
                        if df.lower().endswith(".mp3"):
                            print(f"🏷️ Ajout des tags ID3: {os.path.basename(df)}")
                            logging.info(f"🔄 Début de l'ajout des tags ID3 pour : {os.path.basename(df)}")
                            
                            # Charger ou créer les tags ID3
                            try:
                                id3_tags = ID3(df)
                                print(f"📄 Tags ID3 existants chargés")
                                logging.info(f"📂 Tags ID3 existants chargés pour : {os.path.basename(df)}")
                            except ID3NoHeaderError:
                                id3_tags = ID3()
                                print(f"📄 Création nouveaux tags ID3")
                                logging.info(f"📂 Aucun tag ID3 trouvé, création de nouveaux tags pour : {os.path.basename(df)}")
                            
                            # Ajouter la transcription comme paroles non synchronisées
                            id3_tags.add(USLT(
                                encoding=3,  # UTF-8
                                lang='hat',  # Code langue pour le texte
                                desc='Transcription',
                                text=entry["transcription"]
                            ))
                            print(f"✅ Transcription ajoutée aux tags")
                            logging.info(f"📝 Transcription ajoutée aux tags ID3 pour : {os.path.basename(df)}")
                            
                            # Sauvegarder les modifications
                            id3_tags.save(df)
                            print(f"✅ Tags ID3 sauvegardés")
                            logging.info(f"✅ Tags ID3 sauvegardés avec succès pour : {os.path.basename(df)}")
                    except Exception as tag_e:
                        print(f"❌ ERREUR tags ID3: {tag_e}")
                        logging.error(f"❌ Erreur lors de l'ajout des tags ID3 à {os.path.basename(df)} : {tag_e}")
                    # Insertion en base
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
                        print(f"⚠️ Doublon ignoré: {entry['name']}")
                        logging.warning(f"⚠️ Doublon ignoré pour : {entry['name']}")
                        conn.rollback()
            except Exception as e:
                print(f"❌ ERREUR globale: {os.path.basename(df)}: {e}")
                logging.error(f"❌ Erreur globale sur {os.path.basename(df)} : {e}")
                conn.rollback()
        
        # Libération mémoire après chaque lot
        import gc
        import torch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()
        print(f"🧹 Mémoire libérée après traitement du lot {i//batch_size + 1}")
        logging.info(f"Mémoire libérée après traitement du lot {i//batch_size + 1}")
    
    conn.close()
    print("📤 Connexion BDD fermée")
    logging.info("Connexion à la base de données fermée.")
    print(f"🏁 PIPELINE TERMINÉ: {audio_file}")
    logging.info(f"Pipeline terminé pour le fichier : {audio_file}")

def get_gpu_memory():
    """Affiche l'utilisation de la mémoire GPU."""
    if torch.cuda.is_available():
        print(f"📊 GPU: {torch.cuda.get_device_name(0)}")
        print(f"📊 Mémoire totale: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} Go")
        print(f"📊 Mémoire utilisée: {torch.cuda.memory_allocated() / 1e9:.2f} Go")
        print(f"📊 Mémoire réservée: {torch.cuda.memory_reserved() / 1e9:.2f} Go")

# Ajouter après chaque étape majeure
#get_gpu_memory()

def split_audio_file(file_path, output_dir, segment_duration_min=15):
    """
    Découpe un fichier audio en segments de durée fixe.
    
    Args:
        file_path: Chemin vers le fichier audio à découper
        output_dir: Répertoire où sauvegarder les segments
        segment_duration_min: Durée des segments en minutes (par défaut: 15)
        
    Returns:
        Liste des chemins vers les segments créés
    """
    from pydub import AudioSegment
    
    print(f"🔪 Découpage de {os.path.basename(file_path)} en segments de {segment_duration_min} minutes...")
    logging.info(f"Découpage de {os.path.basename(file_path)} en segments de {segment_duration_min} minutes...")
    
    # Créer le répertoire de sortie si nécessaire
    os.makedirs(output_dir, exist_ok=True)
    
    # Charger le fichier audio
    try:
        audio = AudioSegment.from_file(file_path)
        
        # Afficher la durée totale
        total_duration_sec = len(audio) / 1000
        print(f"📊 Durée totale: {total_duration_sec:.2f} secondes ({total_duration_sec/60:.2f} minutes)")
        
        # Calculer la durée du segment en millisecondes
        segment_duration_ms = segment_duration_min * 60 * 1000
        
        # Découper le fichier en segments
        segments = []
        for i in range(0, len(audio), segment_duration_ms):
            # Extraire le segment
            end_pos = min(i + segment_duration_ms, len(audio))
            segment = audio[i:end_pos]
            
            # Générer le nom du segment
            basename = os.path.basename(file_path)
            name, ext = os.path.splitext(basename)
            segment_number = i // segment_duration_ms + 1
            segment_file = os.path.join(output_dir, f"{name}_segment_{segment_number:03d}{ext}")
            
            # Exporter le segment
            segment.export(segment_file, format=ext.replace(".", ""))
            segments.append(segment_file)
            
            segment_duration = (end_pos - i) / 1000
            print(f"  ✓ Segment {segment_number}: {segment_duration:.2f} secondes - {os.path.basename(segment_file)}")
            logging.info(f"Segment {segment_number} créé: {segment_file}")
        
        print(f"✅ {len(segments)} segments créés")
        return segments
    except Exception as e:
        print(f"❌ ERREUR lors du découpage: {e}")
        logging.error(f"Erreur lors du découpage de {file_path}: {e}")
        return []

def process_large_file(audio_file, temp_dir, diarization_model_name="pyannote/speaker-diarization-3.1", segment_duration_min=15):
    """Traite un fichier audio volumineux en le découpant en segments."""
    print(f"\n🚀 DÉMARRAGE TRAITEMENT DU FICHIER VOLUMINEUX: {audio_file}")
    logging.info(f"Début du traitement du fichier volumineux : {audio_file}")
    
    # Créer un sous-dossier unique pour ce fichier
    file_basename = os.path.splitext(os.path.basename(audio_file))[0]
    file_temp_dir = os.path.join(temp_dir, file_basename)
    os.makedirs(file_temp_dir, exist_ok=True)
    
    # Découper le fichier en segments
    segments_dir = os.path.join(file_temp_dir, "segments")
    segments = split_audio_file(audio_file, segments_dir, segment_duration_min)
    
    if not segments:
        print(f"⚠️ Aucun segment créé, traitement du fichier entier")
        pipeline(audio_file, temp_dir, diarization_model_name)
        return
    
    # Traiter chaque segment
    for i, segment in enumerate(segments):
        print(f"\n🔄 Traitement du segment {i+1}/{len(segments)}: {os.path.basename(segment)}")
        logging.info(f"Traitement du segment {i+1}/{len(segments)}: {os.path.basename(segment)}")
        
        pipeline(segment, temp_dir, diarization_model_name)
        
        # Libérer la mémoire après chaque segment
        import gc
        import torch
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        gc.collect()
        print(f"🧹 Mémoire libérée après traitement du segment {i+1}/{len(segments)}")
        logging.info(f"Mémoire libérée après traitement du segment {i+1}/{len(segments)}")
    
    # Nettoyer les fichiers segments après traitement
    cleanup_vocal_files(segments_dir)
    
    print(f"🏁 TRAITEMENT DU FICHIER VOLUMINEUX TERMINÉ: {audio_file}")
    logging.info(f"Traitement du fichier volumineux terminé : {audio_file}")

# Ajouter une fonction pour nettoyer les fichiers vocaux
def cleanup_vocal_files(vocals_dir):
    """Supprime les fichiers vocaux intermédiaires après utilisation"""
    try:
        if os.path.exists(vocals_dir):
            print(f"🧹 Nettoyage des fichiers vocaux dans {vocals_dir}")
            files_deleted = 0
            for file in os.listdir(vocals_dir):
                file_path = os.path.join(vocals_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    files_deleted += 1
            
            # Suppression du dossier s'il est vide
            if not os.listdir(vocals_dir):
                os.rmdir(vocals_dir)
                print(f"✅ Dossier {vocals_dir} supprimé ({files_deleted} fichiers)")
                logging.info(f"Dossier {vocals_dir} supprimé ({files_deleted} fichiers)")
            else:
                print(f"✅ {files_deleted} fichiers vocaux supprimés")
                logging.info(f"{files_deleted} fichiers vocaux supprimés")
    except Exception as e:
        print(f"❌ ERREUR lors du nettoyage des fichiers vocaux: {e}")
        logging.error(f"Erreur lors du nettoyage des fichiers vocaux: {e}")

if __name__ == "__main__":
    print("\n🔄 DÉMARRAGE DU SCRIPT BATCH_PIPELINE.PY")
    parser = argparse.ArgumentParser(description="Pipeline audio : extraction, diarization, transcription, update DB")
    parser.add_argument("input_path", help="Fichier audio ou répertoire à traiter")
    parser.add_argument("--output_dir", default="pipeline_tmp", help="Répertoire de destination des fichiers intermédiaires")
    parser.add_argument("--segment_duration", type=int, default=15, help="Durée des segments en minutes (par défaut: 15)")
    parser.add_argument("--model", default="large-v3-turbo", 
                        choices=["tiny", "base", "small", "medium", "large-v3", "openai/whisper-large-v3-turbo"], 
                        help="Modèle Whisper à utiliser (par défaut: openai/whisper-large-v3-turbo)")
    args = parser.parse_args()
    
    print(f"📂 Entrée: {args.input_path}")
    print(f"📂 Sortie: {args.output_dir}")
    print(f"⏱️ Durée des segments: {args.segment_duration} minutes")
    print(f"🔤 Modèle Whisper: {args.model}")

    # Charger le modèle Whisper
    print("🔄 Chargement du modèle Whisper en cours...")
    logging.info(f"Chargement du modèle Whisper {args.model}...")
    model = whisper.load_model(args.model)
    print("✅ Modèle Whisper chargé avec succès")
    logging.info("Modèle Whisper chargé avec succès.")

    input_path = args.input_path
    if os.path.isdir(input_path):
        files = [fname for fname in sorted(os.listdir(input_path)) if fname.lower().endswith((".mp3", ".wav"))]
        print(f"📊 {len(files)} fichiers à traiter dans le dossier")
        for fname in tqdm(files, desc="Fichiers à traiter"):
            file_path = os.path.join(input_path, fname)
            print(f"\n🔄 TRAITEMENT: {file_path}")
            logging.info(f"▶️ Traitement de {file_path}")
            process_large_file(file_path, args.output_dir, segment_duration_min=args.segment_duration)
    else:
        print(f"\n🔄 TRAITEMENT: {input_path}")
        logging.info(f"▶️ Traitement de {input_path}")
        process_large_file(input_path, args.output_dir, segment_duration_min=args.segment_duration)
    
    print("\n✅ TRAITEMENT TERMINÉ")