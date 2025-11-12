import os
import argparse
from pydub import AudioSegment
from tqdm import tqdm  # Ajout de tqdm

def convert_wav_to_mp3(input_dir, output_dir, bitrate="96k"):
    """
    Convertit tous les fichiers WAV d'un répertoire donné en MP3 et efface les fichiers WAV après conversion.

    :param input_dir: Répertoire contenant les fichiers WAV.
    :param output_dir: Répertoire où les fichiers MP3 seront sauvegardés.
    :param bitrate: Bitrate pour les fichiers MP3 (par défaut : 96k).
    """
    # Créer le répertoire de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Lister tous les fichiers wav
    wav_files = [f for f in os.listdir(input_dir) if f.endswith(".wav")]

    # Parcourir tous les fichiers avec tqdm
    for filename in tqdm(wav_files, desc="Conversion WAV -> MP3"):
        wav_file = os.path.join(input_dir, filename)
        print(f"Traitement du fichier : {filename}")  # Affichage du nom du fichier
        if os.path.getsize(wav_file) == 0:
            print(f"Fichier vide ignoré : {filename}")
            continue
        try:
            audio = AudioSegment.from_wav(wav_file)
        except Exception as e:
            print(f"Erreur lors de la lecture de {filename} : {e}")
            continue

        # Créer le nom de fichier MP3 de sortie
        mp3_filename = os.path.splitext(filename)[0] + ".mp3"
        mp3_file = os.path.join(output_dir, mp3_filename)

        # Exporter en MP3
        audio.export(mp3_file, format="mp3", bitrate=bitrate)
        print(f"Converti {filename} en {mp3_filename}")

        # Effacer le fichier WAV après conversion
        os.remove(wav_file)
        print(f"Effacé {filename}")

if __name__ == "__main__":
    # Configurer le parseur d'arguments
    parser = argparse.ArgumentParser(description="Convertit des fichiers WAV en MP3 et efface les fichiers WAV après conversion.")
    parser.add_argument("input_dir", help="Répertoire contenant les fichiers WAV.")
    parser.add_argument("output_dir", help="Répertoire où les fichiers MP3 seront sauvegardés.")
    parser.add_argument("--bitrate", default="96k", help="Bitrate pour les fichiers MP3 (par défaut : 96k).")

    # Analyser les arguments
    args = parser.parse_args()

    # Appeler la fonction de conversion
    convert_wav_to_mp3(args.input_dir, args.output_dir, args.bitrate)
