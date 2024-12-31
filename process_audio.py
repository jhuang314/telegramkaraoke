import numpy as np # numpy==1.25
from pydub import AudioSegment
from pydub.playback import play
from pydub.generators import Sine
import whisper
from whisper_normalizer.basic import BasicTextNormalizer
import librosa
import json
from scipy.spatial.distance import cosine
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging
import warnings
import csv
from jiwer import wer


transcriber = whisper.load_model('medium.en')
normalizer = BasicTextNormalizer()


def concatenate_audio(recordings):
    """
    Concatenates audio together.

    recordings: a list of recording file names, in ogg format.
    """
    sound = AudioSegment.from_file(recordings[0], format="ogg")
    filename = recordings[0].removesuffix('.ogg')


    for recording in recordings[1:]:
        sound += AudioSegment.from_file(recording, format="ogg")

    combined_filename = f'{filename}_combined.ogg'

    return sound.export(combined_filename, format='ogg'), combined_filename



def _transcribe(input_file, output_dir="data/lyrics/"):
    os.makedirs(output_dir, exist_ok=True)
    file_name = input_file.split('/')[-1].split('.')[0].split('_')[0]
    output_file = os.path.join(output_dir, file_name + ".txt")


    if os.path.exists(output_file):
        with open(output_file, "r") as file:
            return file.read()


    logging.info(f"Input file:{input_file}")

    cwd = os.getcwd()
    logging.info(f"cwd: {cwd}")
    logging.info(f"Input file exists: {os.path.exists(input_file)}")
    result = transcriber.transcribe(input_file)["text"]

    result = normalizer(result)

    with open(output_file, "w") as file:
        file.write(result)
        logging.info(f"Saved transcription for {input_file}.")

    return result

def _extract_features(audio_file, output_dir="data/audio_features"):
    file_name = os.path.basename(audio_file).split('.')[0]
    feature_file = os.path.join(output_dir, file_name + "_features.json")

    if os.path.exists(feature_file):
        logging.info(f"Loading cached features for {audio_file}")
        with open(feature_file, "r") as file:
            return json.load(file)

    logging.info('transcribing')
    text = _transcribe(audio_file)
    logging.info('transcribing done')

    logging.info('librosa pitch and beat analysis')
    y, sr = librosa.load(audio_file)
    logging.info('librosa pitch and beat analysis, load audio done')
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    logging.info('librosa pitch and beat analysis piptrack')
    pitch_track = [np.max(pitches[i]) for i in range(pitches.shape[0]) if np.max(pitches[i]) > 0]
    logging.info('librosa pitch and beat analysis pitch_track')
    average_pitch = np.mean(pitch_track) if pitch_track else 0
    logging.info('librosa pitch and beat analysis average_pitch')
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    logging.info('librosa pitch and beat analysis tempo')
    duration = librosa.get_duration(y=y, sr=sr)
    logging.info('librosa pitch and beat analysis duration')

    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0])

    norm = float(np.linalg.norm(np.array(pitch_track)))

    logging.info('librosa pitch and beat analysis DONE')

    output = {
        "bpm": tempo,
        "duration": duration,
        "average_pitch": float(average_pitch),
        "pitch_track": norm,
        "text": text,
        "pitch_range": len(pitch_track)
    }

    output = {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in output.items()}

    os.makedirs(output_dir, exist_ok=True)
    with open(feature_file, "w") as file:
        json.dump(output, file, indent=4)

    return output

def compare_audios(file1, file2):
    """Compare two audio files based on their pitch, tempo, length, and text similarity."""

    feature1 = _extract_features(file1)
    feature2 = _extract_features(file2)

    pk, pq = feature1["pitch_range"], feature2["pitch_range"]

    length_difference_threshold = 0.5
    if feature1["duration"] * length_difference_threshold - feature2["duration"] > 0 or feature2["duration"] * length_difference_threshold - feature1["duration"] > 0  :
        return 0.0

    pitch_diff = np.abs(feature1["pitch_track"] - feature2["pitch_track"])
    tempo_diff = abs(feature1["bpm"] - feature2["bpm"])

    word_error_rate = 0.0
    if feature1["text"] and feature2["text"]:
        word_error_rate = wer(feature1["text"], feature2["text"])

    pitch_range = max([pk, pq])
    tempo_range = max([feature1["bpm"], feature2["bpm"]])

    normalized_tempo_diff = tempo_diff / tempo_range
    normalized_pitch_diff = pitch_diff / pitch_range

    logging.info(f"word error rate: {word_error_rate}")
    logging.info(f"pitch diff: {normalized_pitch_diff}")
    logging.info(f"{normalized_tempo_diff}")

    score = (1 - normalized_pitch_diff - normalized_tempo_diff)*0.15 + (1 - word_error_rate)*0.85

    return int(max(score, 0) * 100000)
