import os
import argparse
from pydub import AudioSegment
from tqdm import tqdm

def delete_short_audio_files(directory, min_duration):
    # Obtenir la liste des fichiers dans le répertoire
    files = [f for f in os.listdir(directory) if f.endswith(".mp3") or f.endswith(".wav")]

    # Parcourir tous les fichiers avec une barre de progression
    for filename in tqdm(files, desc="Traitement des fichiers"):
        filepath = os.path.join(directory, filename)

        try:
            # Charger le fichier audio
            if filename.endswith(".mp3"):
                audio = AudioSegment.from_mp3(filepath)
            elif filename.endswith(".wav"):
                audio = AudioSegment.from_wav(filepath)

            # Obtenir la durée en secondes
            duration_in_seconds = len(audio) / 1000

            # Supprimer le fichier si la durée est inférieure à la durée minimale spécifiée
            if duration_in_seconds < min_duration:
                os.remove(filepath)
                tqdm.write(f"Supprimé : {filename} ({duration_in_seconds} secondes)")
            else:
                tqdm.write(f"Conservé : {filename} ({duration_in_seconds} secondes)")
        except Exception as e:
            tqdm.write(f"Erreur lors du traitement du fichier {filename}: {e}")

def main():
    # Configurer le parser d'arguments
    parser = argparse.ArgumentParser(description='Supprimer les fichiers MP3 et WAV dont la durée est inférieure à une durée spécifiée.')
    parser.add_argument('directory', type=str, help='Le répertoire contenant les fichiers audio')
    parser.add_argument('--min_duration', type=float, default=2.0, help='La durée minimale en secondes (par défaut : 2 secondes)')

    # Parser les arguments
    args = parser.parse_args()

    # Appeler la fonction avec les arguments fournis
    delete_short_audio_files(args.directory, args.min_duration)

if __name__ == "__main__":
    main()
