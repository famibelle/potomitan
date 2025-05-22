import os
import json
import logging
import torch
import filetype
import argparse

from pydub import AudioSegment

from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook

# Prioriser les variables d'environnement système
HUGGING_FACE_KEY = os.getenv("HuggingFace_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_MCF")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if torch.cuda.is_available():
    logging.info(f"GPU trouvé! on utilise CUDA. Device: {device}")
else:
    logging.info(f"Pas de GPU de disponible... Device: {device}")

def load_pipeline_diarization(model):
    pipeline_diarization = Pipeline.from_pretrained(
        model,
        use_auth_token=HUGGING_FACE_KEY,
    )

    if torch.cuda.is_available():
        pipeline_diarization.to(torch.device("cuda"))

    logging.info(f"Pipeline Diarization déplacée sur {device}")

    return pipeline_diarization

def detect_file_type(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    logging.info(f"Extension détectée {file_extension}.")

    file_type = filetype.guess(file_path)
    logging.info(f"Type de fichier : {file_type.mime}, Extension : {file_type.extension}")

    return file_extension, file_type

def extract_audio(file_path, file_extension, file_type):
    extraction_status = {'extraction_audio_status': 'extraction_audio_ongoing', 'message': 'Extraction audio en cours ...'}
    logging.info(extraction_status)

    if file_extension in ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a']:
        logging.info(f"fichier audio détecté: {file_extension}.")
        audio = AudioSegment.from_file(file_path)
    else:
        raise ValueError("Format de fichier non supporté.")

    return audio

def diarize_audio(audio_path, diarization_model, output_dir):
    logging.info(f"Démarrage de la diarisation du fichier {audio_path}")
    file_name = os.path.basename(audio_path)

    audio = AudioSegment.from_file(audio_path)

    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)

    audio.export(audio_path, format="wav")

    # Étape 1 : Diarisation
    with ProgressHook() as hook:
        logging.debug(f"Diarization démarrée")
        diarization = diarization_model(audio_path, hook=hook)
        logging.debug(f"Diarization terminée {diarization}")

    segments = []

    # total_turns = len(list(diarization.itertracks(yield_label=True))) 
    # for turn, _, speaker in tqdm(diarization.itertracks(yield_label=True), total=total_turns, desc="Processing turns"):
    for turn, _, speaker in diarization.itertracks(yield_label=True):

        start_ms = int(turn.start * 1000)  # Convertir de secondes en millisecondes
        end_ms = int(turn.end * 1000)

        # Extraire le segment audio correspondant au speaker
        segment_audio = audio[start_ms:end_ms]

        segment_path = f"{output_dir}/{file_name}_segment_{start_ms}_{end_ms}.wav"
        segment_audio.export(segment_path, format="wav")

        segments.append({
            "speaker": speaker,
            "start_time": turn.start,
            "end_time": turn.end,
            "file": segment_path
        })
        logging.info("Diarization terminée.")
    
    print(f"segments: {segments}")

    return {"segments": segments}

def main(audio_path, output_dir):
    diarization_model = load_pipeline_diarization("pyannote/speaker-diarization-3.1")
    file_extension, file_type = detect_file_type(audio_path)
    audio = extract_audio(audio_path, file_extension, file_type)
    diarize_audio(audio_path, diarization_model, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a file for audio extraction and diarization.")
    parser.add_argument("file_path", type=str, help="Path to the file to process")
    parser.add_argument("output_dir", type=str, help="Directory to save the output audio files")
    args = parser.parse_args()

    main(args.file_path, args.output_dir)
