import argparse
import os

from spleeter.separator import Separator
from spleeter.audio.adapter import AudioAdapter

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
    waveform, sample_rate = audio_loader.load(audio_path, sample_rate=44100)

    # Séparer les sources
    prediction = separator.separate(waveform)

    # Sauvegarder les sources séparées
    vocals = prediction['vocals']

    # Sauvegarder la partie vocale
    output_path = os.path.join(output_dir, os.path.basename(audio_path).replace('.mp3', '_vocals.wav'))
    audio_loader.save(output_path, vocals, sample_rate)

    print(f"La partie vocale a été extraite et sauvegardée dans le fichier '{output_dir}'.")

# Exemple d'utilisation
#input_audio_path = "Mp3\Benzo.mp3"
#output_dir = 'output'
#extract_vocals(input_audio_path, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extraire la partie vocale d\'un fichier MP3.')
    parser.add_argument('audio_path', type=str, help='Chemin vers le fichier MP3 d\'entrée.')
    parser.add_argument('output_dir', type=str, help='Répertoire de sortie pour les fichiers séparés.')

    args = parser.parse_args()
    
    extract_vocals(args.audio_path, args.output_dir)