from pydub import AudioSegment


def concatenate_audio(recordings):
    """
    Concatenates audio together.

    recordings: a list of recording file names, in ogg format.
    """
    sound = AudioSegment.from_file(recordings[0], format="ogg")

    for recording in recordings[1:]:
        sound += AudioSegment.from_file(recording, format="ogg")

    return sound.export('combined.ogg', format='ogg')
