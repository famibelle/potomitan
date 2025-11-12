import whisper
import os
from datetime import datetime
from tqdm import tqdm
import time
from datetime import timedelta

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
import json
from pathlib import Path

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

def save_insertion_to_json(data, json_file="db_insertions.json"):
    """
    Sauvegarde les données d'insertion dans un fichier JSON.
    Chaque insertion est ajoutée comme un nouvel élément dans le fichier.
    
    Args:
        data: Dictionnaire contenant les données insérées
        json_file: Chemin vers le fichier JSON de sortie
    """
    # Créer le répertoire de sortie si nécessaire
    json_path = Path(json_file)
    json_path.parent.mkdir(exist_ok=True, parents=True)
    
    # Charger les données existantes si le fichier existe
    existing_data = []
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            # Si le fichier est corrompu, on repart de zéro
            print(f"⚠️ Fichier JSON corrompu, création d'un nouveau fichier")
            existing_data = []
    
    # Ajouter les nouvelles données
    existing_data.append(data)
    
    # Écrire dans le fichier
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    
    print(f"📝 Insertion enregistrée dans {json_file}")
    logging.info(f"Insertion enregistrée dans {json_file}")
    # Après avoir écrit le fichier
    print(f"📝 Fichier JSON mis à jour : {json_path.resolve()}")
    logging.info(f"Fichier JSON mis à jour : {json_path.resolve()}")

def insert_transcription(conn, filename, transcription, timestamp, author, created_at):
    with conn.cursor() as cur:
        # Variables pour stocker les IDs et l'état de l'opération
        file_id = None
        contrib_id = None
        success = False
        error_message = None
        
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
            success = True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ ERREUR insertion {filename}: {e}")
            logging.error(f"❌ Erreur lors de l'insertion pour {filename} : {e}")
            error_message = str(e)
            
        finally:
            # Toujours sauvegarder dans le JSON, que l'insertion ait réussi ou non
            insertion_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "success": success,
                "fichier_audio": {
                    "id": file_id,
                    "chemin": filename
                },
                "contributeur": {
                    "id": contrib_id,
                    "nom": author
                },
                "transcription": {
                    "texte": transcription,
                    "date_creation": created_at
                }
            }
            
            # Ajouter l'erreur si présente
            if error_message:
                insertion_data["error"] = error_message
            
            # Créer un dossier 'json_logs' dans le répertoire de sortie
            json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "json_logs")
            os.makedirs(json_dir, exist_ok=True)
            
            # Créer un fichier JSON par jour
            today = datetime.now().strftime("%Y-%m-%d")
            json_file = os.path.join(json_dir, f"db_insertions_{today}.json")
            
            save_insertion_to_json(insertion_data, json_file)
            
            if not success:
                # Re-lever l'exception pour maintenir le comportement original
                return False
            
            return True
def format_time(seconds):
    """Formatte un nombre de secondes en chaîne heures:minutes:secondes"""
    return str(timedelta(seconds=int(seconds)))

def estimate_pipeline_time(file_size_mb, remaining_files, avg_time_per_mb=None):
    """Estime le temps restant pour terminer le pipeline en fonction des données historiques"""
    if avg_time_per_mb is None:
        # Estimation grossière basée sur des benchmarks (à ajuster selon les performances réelles)
        # Valeurs indicatives: ~10s/Mo pour l'extraction vocale, ~15s/Mo pour la diarisation, ~5s/Mo pour la transcription
        avg_time_per_mb = 30
    
    total_size_mb = file_size_mb * remaining_files
    estimated_seconds = total_size_mb * avg_time_per_mb
    
    return estimated_seconds, format_time(estimated_seconds)

# Ajouter cette fonction pour la gestion des statistiques de temps
class PipelineTimer:
    def __init__(self):
        self.start_time = time.time()
        self.step_start_time = self.start_time
        self.processed_files = 0
        self.processed_mb = 0
        self.total_files = 0
        self.times = {
            'extraction': [],
            'diarization': [],
            'transcription': [],
            'total_per_file': []
        }
    
    def set_total_files(self, total):
        """Définir le nombre total de fichiers à traiter"""
        self.total_files = total
        
    def start_step(self, step_name=None):
        """Démarrer le chronométrage d'une étape"""
        self.step_start_time = time.time()
        self.current_step = step_name
        
    def end_step(self, step_name=None, file_size_mb=None):
        """Terminer le chronométrage d'une étape et enregistrer la statistique"""
        elapsed = time.time() - self.step_start_time
        if step_name:
            if step_name in self.times:
                self.times[step_name].append(elapsed)
                
        if file_size_mb:
            self.processed_mb += file_size_mb
            
        return elapsed
        
    def end_file(self, file_size_mb):
        """Enregistrer les statistiques pour un fichier complet"""
        self.processed_files += 1
        elapsed = time.time() - self.start_time
        self.times['total_per_file'].append(elapsed)
        self.processed_mb += file_size_mb
        
        # Calculer le temps moyen par Mo
        avg_time_per_mb = elapsed / self.processed_mb if self.processed_mb > 0 else 30
        
        return avg_time_per_mb
    
    def get_estimates(self):
        """Récupérer les estimations de temps restant"""
        if self.processed_files == 0 or self.total_files == 0:
            return "Estimation en attente...", 0
            
        elapsed = time.time() - self.start_time
        avg_time_per_file = elapsed / self.processed_files
        remaining_files = self.total_files - self.processed_files
        estimated_remaining = avg_time_per_file * remaining_files
        
        return format_time(estimated_remaining), estimated_remaining
    
    def get_stats(self):
        """Afficher des statistiques complètes"""
        if not self.times['total_per_file']:
            return "Pas encore de données disponibles"
            
        avg_extraction = sum(self.times['extraction']) / len(self.times['extraction']) if self.times['extraction'] else 0
        avg_diarization = sum(self.times['diarization']) / len(self.times['diarization']) if self.times['diarization'] else 0
        avg_transcription = sum(self.times['transcription']) / len(self.times['transcription']) if self.times['transcription'] else 0
        
        return {
            "temps_moyen_extraction": format_time(avg_extraction),
            "temps_moyen_diarisation": format_time(avg_diarization),
            "temps_moyen_transcription": format_time(avg_transcription),
            "temps_total_écoulé": format_time(time.time() - self.start_time),
            "fichiers_traités": self.processed_files,
            "fichiers_restants": self.total_files - self.processed_files
        }

# Créer un timer global
pipeline_timer = PipelineTimer()

# Modifier la fonction pipeline pour utiliser le timer
def pipeline(audio_file, temp_dir, diarization_model_name="pyannote/speaker-diarization-3.1"):
    print(f"\n🚀 DÉMARRAGE PIPELINE: {audio_file}")
    logging.info(f"Début du pipeline pour le fichier : {audio_file}")
    
    # Calculer la taille du fichier pour les statistiques
    file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
    print(f"📊 Taille du fichier : {file_size_mb:.2f} Mo")
    
    # 1. Extraction vocale
    vocals_dir = os.path.join(temp_dir, "vocals")
    os.makedirs(vocals_dir, exist_ok=True)
    print(f"📁 Dossier créé: {vocals_dir}")
    logging.info(f"Dossier vocals créé : {vocals_dir}")
    try:
        print(f"🎵 Extraction vocale en cours: {audio_file}")
        # Chronométrer l'extraction vocale
        pipeline_timer.start_step('extraction')
        extract_vocals(audio_file, vocals_dir)
        extraction_time = pipeline_timer.end_step('extraction', file_size_mb)
        print(f"✅ Extraction vocale terminée: {audio_file} en {format_time(extraction_time)}")
        
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
        pipeline_timer.start_step('diarization')
        diarization_model = load_pipeline_diarization(diarization_model_name)
        print("✅ Modèle diarization chargé")
        
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
        
        diarization_time = pipeline_timer.end_step('diarization', file_size_mb)
        print(f"⏱️ Temps de diarisation : {format_time(diarization_time)}")
        
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
    
    # Transcrire et mettre à jour DB ou JSON
    diarized_files = [
        os.path.join(diarized_dir, f)
        for f in os.listdir(diarized_dir)
        if f.endswith((".mp3", ".wav"))
    ]
    print(f"📊 {len(diarized_files)} segments à traiter")

    # Mode JSON only
    if NO_DB:
        print("⚠️ Mode JSON uniquement, pas d'insertion en base")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Ajouter un timestamp
        json_output = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            f"all_transcriptions_{timestamp}.json"  # Nom du fichier avec timestamp
        )
        for df in tqdm(diarized_files, desc="Enregistrement JSON"):
            entries = transcribe_file(df)
            created_at = datetime.fromtimestamp(os.path.getctime(df)).isoformat()
            for entry in entries:
                # Préparer la donnée
                json_record = {
                    "file": entry["name"],
                    "transcription": entry["transcription"],
                    "timestamp": entry["timestamp"],
                    "author": entry["author"],
                    "created_at": created_at
                }
                save_insertion_to_json(json_record, json_output)
        return

    # Sinon, connexion et inserts en base (code existant)…
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
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Ne pas insérer en base, enregistrer toutes les entrées dans un seul JSON"
    )
    args = parser.parse_args()

    # Flag global pour désactiver les inserts
    NO_DB = args.no_db

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