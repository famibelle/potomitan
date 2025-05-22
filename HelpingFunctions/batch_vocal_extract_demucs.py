import argparse
import os
import hashlib
import random
import string
import shutil
from tqdm import tqdm
import gc
import torch
import demucs.separate
import shlex


# Détecte automatiquement GPU ou CPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"💻 Utilisation de : {DEVICE.upper()}")


def generate_random_hash(file_path, length=8):
    # Extraire le nom de fichier à partir du chemin complet
    file_name = os.path.basename(file_path)

    # Créer un objet hash SHA-256 à partir du nom du fichier
    hash_object = hashlib.sha256(file_name.encode())

    # Retourner le hash sous forme hexadécimale, tronqué à la longueur spécifiée
    return hash_object.hexdigest()[:length]

def extract_vocals(audio_path, output_dir):
    """
    Extrait la partie vocale d'un fichier audio à l'aide de Demucs et sauvegarde uniquement la piste vocale.
    """
    # Lancer la séparation avec Demucs
    try:
        #command = f'--two-stems vocals -n mdx_extra "{audio_path}"'
        command = f'--two-stems vocals -n mdx_extra --device {DEVICE} "{audio_path}"'

        demucs.separate.main(shlex.split(command))
    except Exception as e:
        print(f"Erreur lors de la séparation de {audio_path} : {e}")
        return

    # Récupérer le nom de base
    base_name = os.path.splitext(os.path.basename(audio_path))[0]

    # Dossier où Demucs a exporté les résultats
    demucs_output_path = os.path.join("separated", "mdx_extra", base_name)
    vocals_path = os.path.join(demucs_output_path, "vocals.wav")

    if not os.path.exists(vocals_path):
        print(f"⚠️ Vocaux non trouvés pour {audio_path}")
        return

    # Générer un nom de fichier de sortie unique
    random_hash = generate_random_hash(audio_path)
    final_output_path = os.path.join(output_dir, f'{random_hash}_vocals.wav')

    # Créer le dossier de sortie s’il n’existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Déplacer la piste vocale
    shutil.move(vocals_path, final_output_path)
    print(f"✔️ Vocaux extraits : {final_output_path}")

    # Nettoyer
    try:
        shutil.rmtree(demucs_output_path)
    except Exception:
        pass

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def process_directory(input_dir, output_dir, batch_size=5):
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]

    for i in tqdm(range(0, len(files), batch_size), desc="Traitement en cours"):
        batch_files = files[i:i + batch_size]
        for filename in batch_files:
            audio_path = os.path.join(input_dir, filename)
            extract_vocals(audio_path, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extraire les vocaux des fichiers audio avec Demucs.')
    parser.add_argument('input_dir', type=str, help='Répertoire contenant les fichiers audio.')
    parser.add_argument('output_dir', type=str, help='Répertoire de sortie pour les vocaux.')
    parser.add_argument('--batch_size', type=int, default=10, help='Nombre de fichiers à traiter par lot.')

    args = parser.parse_args()
    process_directory(args.input_dir, args.output_dir, args.batch_size)
