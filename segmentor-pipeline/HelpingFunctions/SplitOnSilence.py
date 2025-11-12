import argparse

from pydub import AudioSegment, silence
import numpy as np

import numpy as np
import hashlib
import random
import string

def generate_random_hash(length=8):
    # Générer une chaîne aléatoire de caractères
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    # Créer un hash SHA-256 de la chaîne aléatoire
    hash_object = hashlib.sha256(random_string.encode())
    # Retourner les premiers 8 caractères du hash
    return hash_object.hexdigest()[:length]

def split_audio_on_silence(audio_path, output_path, silence_thresh=-40, min_silence_len=500, max_segment_duration=10000, min_segment_duration=1000):
    # Charger le fichier audio
    audio = AudioSegment.from_file(audio_path)

    # Détecter les silences
    silent_ranges = silence.detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)

    # Diviser l'audio en fonction des silences
    chunks = []
    start = 0
    for start_silence, end_silence in silent_ranges:
        chunk = audio[start:start_silence]
        if len(chunk) > 0:
            # Diviser le morceau en segments de max_segment_duration
            for i in range(0, len(chunk), max_segment_duration):
                segment = chunk[i:i+max_segment_duration]
                if len(segment) >= min_segment_duration:
                    chunks.append(segment)
        start = end_silence
    # Ajouter le dernier morceau
    last_chunk = audio[start:]
    if len(last_chunk) > 0:
        for i in range(0, len(last_chunk), max_segment_duration):
            segment = last_chunk[i:i+max_segment_duration]
            if len(segment) >= min_segment_duration:
                chunks.append(segment)

    # Sauvegarder chaque segment avec un nom de fichier aléatoire
    for i, chunk in enumerate(chunks):
        random_hash = generate_random_hash()
        chunk.export(f"{output_path}/segment_{random_hash}.wav", format="wav")


# Exemple d'utilisation
#audio_path = "Mp3/toutouni_vocals.wav"
#audio_path = "Mp3/baimbridge_cho_vocals.wav"
#audio_path = "Mp3/RADYO_TANBOU.wav"

#output_path = "output/"
#split_audio_on_silence(audio_path, output_path)

def main():
    parser = argparse.ArgumentParser(description='Split audio on silence.')
    parser.add_argument('--audio_path', type=str, help='Path to the audio file')
    parser.add_argument('--output_path', type=str, help='Path to the output directory')
    parser.add_argument('--silence_thresh', type=int, default=-40, help='Silence threshold in dB')
    parser.add_argument('--min_silence_len', type=int, default=500, help='Minimum silence length in ms')
    parser.add_argument('--max_segment_duration', type=int, default=10000, help='Maximum segment duration in ms')
    parser.add_argument('--min_segment_duration', type=int, default=1000, help='Minimum segment duration in ms')

    args = parser.parse_args()

    split_audio_on_silence(
        args.audio_path,
        args.output_path,
        args.silence_thresh,
        args.min_silence_len,
        args.max_segment_duration,
        args.min_segment_duration
    )

if __name__ == "__main__":
    main()