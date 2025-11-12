import argparse
import os
import hashlib
import random
import string
from tqdm import tqdm
from spleeter.separator import Separator
from spleeter.audio.adapter import AudioAdapter
import gc
import tensorflow as tf
import torch

def generate_random_hash(length=8):
    # Générer une chaîne aléatoire de caractères
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    # Créer un hash SHA-256 de la chaîne aléatoire
    hash_object = hashlib.sha256(random_string.encode())
    # Retourner les premiers 8 caractères du hash
    return hash_object.hexdigest()[:length]

def extract_vocals(audio_path, output_dir):
    """
    Extrait la partie vocale d'un fichier MP3 et la sauvegarde dans un fichier WAV.

    :param input_audio_path: Chemin vers le fichier MP3 d'entrée.
    :param output_dir: Répertoire de sortie pour les fichiers séparés.
    """
    # Créer le répertoire de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialiser le séparateur de sources
    separator = Separator('spleeter:2stems')

    # Charger l'audio
    audio_loader = AudioAdapter.default()
    waveform, sample_rate = audio_loader.load(audio_path, sample_rate=16000)

    # Séparer les sources
    try:
        with tf.Graph().as_default(), tf.compat.v1.Session() as sess:
            prediction = separator.separate(waveform)

            # Sauvegarder les sources séparées
            vocals = prediction['vocals']

            # Sauvegarder la partie vocale
            random_hash = generate_random_hash()
            output_path = os.path.join(output_dir, f'{random_hash}_vocals.wav')
            audio_loader.save(output_path, vocals, sample_rate)

            print(f"La partie vocale a été extraite et sauvegardée dans le fichier '{output_path}'.")

    except Exception as e:
        print(f"i pa ka maché: {e}")

    # Libérer la mémoire
    del waveform, sample_rate, prediction, vocals
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def process_directory(input_dir, output_dir, batch_size=5):
    """
    Traite tous les fichiers MP3 dans un répertoire donné par lots.

    :param input_dir: Répertoire contenant les fichiers MP3.
    :param output_dir: Répertoire de sortie pour les fichiers séparés.
    :param batch_size: Nombre de fichiers à traiter par lot.
    """
    # Lister tous les fichiers dans le répertoire d'entrée
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp3', '.wav'))]

    for i in tqdm(range(0, len(files), batch_size), desc="Processing files"):
        batch_files = files[i:i + batch_size]
        for filename in batch_files:
            audio_path = os.path.join(input_dir, filename)
            extract_vocals(audio_path, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extraire la partie vocale de tous les fichiers MP3 dans un répertoire.')
    parser.add_argument('input_dir', type=str, help='Répertoire contenant les fichiers MP3 d\'entrée.')
    parser.add_argument('output_dir', type=str, help='Répertoire de sortie pour les fichiers séparés.')
    parser.add_argument('--batch_size', type=int, default=10, help='Nombre de fichiers à traiter par lot.')

    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir, args.batch_size)
