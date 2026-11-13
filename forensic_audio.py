import json
import shutil
import subprocess
import wave
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def run(cmd):
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-4000:] or "Falha ao executar comando externo.")
    return proc.stdout


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def normalize_to_wav(source, destination):
    run([
        "ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1",
        "-ar", "16000", "-sample_fmt", "s16", str(destination)
    ])


def ffprobe_json(source):
    output = run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(source)
    ])
    return json.loads(output)


def analyze_audio(source, case_dir, progress_callback=None):
    case_dir = Path(case_dir)
    normalized = case_dir / "normalized.wav"
    if progress_callback:
        progress_callback(8, "Convertendo áudio para WAV mono 16 kHz...")
    normalize_to_wav(source, normalized)

    if progress_callback:
        progress_callback(13, "Extraindo metadados com FFprobe...")
    probe = ffprobe_json(source)
    audio_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), {}
    )
    metadata = {
        "container": probe.get("format", {}).get("format_name"),
        "format_long_name": probe.get("format", {}).get("format_long_name"),
        "duration_seconds": float(probe.get("format", {}).get("duration", 0) or 0),
        "size_bytes": int(probe.get("format", {}).get("size", 0) or 0),
        "bit_rate": probe.get("format", {}).get("bit_rate"),
        "codec": audio_stream.get("codec_name"),
        "codec_long_name": audio_stream.get("codec_long_name"),
        "sample_rate": audio_stream.get("sample_rate"),
        "channels": audio_stream.get("channels"),
        "channel_layout": audio_stream.get("channel_layout"),
        "sample_format": audio_stream.get("sample_fmt"),
        "tags": probe.get("format", {}).get("tags", {}),
    }
    if progress_callback:
        progress_callback(16, "Gerando espectrograma...")
    make_spectrogram(normalized, case_dir / "spectrogram.png")
    return metadata


def make_spectrogram(wav_path, output_path):
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if len(samples) == 0:
        return
    samples = samples[: rate * 180]
    plt.figure(figsize=(14, 5))
    # Suppress the expected log10 warning for zero-energy frequency bins.
    with np.errstate(divide="ignore", invalid="ignore"):
        plt.specgram(samples, Fs=rate, NFFT=1024, noverlap=768, vmin=-120)
    plt.xlabel("Tempo (s)")
    plt.ylabel("Frequência (Hz)")
    plt.title("Espectrograma — análise visual")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def transcribe_audio(source, case_dir, model_size="small", language="pt", task="transcribe", progress_callback=None):
    normalized = Path(case_dir) / "normalized.wav"
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("faster-whisper não está instalado. Execute install_windows.bat.") from exc

    if progress_callback:
        progress_callback(19, f"Carregando modelo Whisper ({model_size})...")
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    if progress_callback:
        progress_callback(22, "Modelo carregado. Iniciando transcrição...")

    segments, info = model.transcribe(
        str(normalized), language=language, task=task, beam_size=5,
        vad_filter=True, word_timestamps=True
    )
    items = []
    duration = float(info.duration or 0)
    for segment in segments:
        words = []
        if segment.words:
            for word in segment.words:
                words.append({
                    "word": word.word, "start": word.start,
                    "end": word.end, "probability": word.probability
                })
        items.append({
            "id": len(items) + 1, "start": segment.start,
            "end": segment.end, "text": segment.text.strip(), "words": words
        })
        if progress_callback and duration > 0:
            pct = 22 + int(min(segment.end / duration, 1.0) * 72)
            progress_callback(min(pct, 94), f"Transcrevendo: {segment.end:.1f} de {duration:.1f} segundos")

    result = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration_seconds": info.duration,
        "segments": items
    }
    write_txt(result, Path(case_dir) / "transcription.txt")
    write_srt(result, Path(case_dir) / "transcription.srt")
    return result


def timestamp(seconds):
    seconds = max(0, float(seconds))
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(result, path):
    lines = []
    for i, seg in enumerate(result["segments"], start=1):
        lines.extend([str(i), f"{timestamp(seg['start'])} --> {timestamp(seg['end'])}", seg["text"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_txt(result, path):
    lines = [
        "TRANSCRIÇÃO DE ÁUDIO", "",
        f"Idioma: {result.get('language')}",
        f"Confiança do idioma: {result.get('language_probability')}", ""
    ]
    for seg in result["segments"]:
        start = timestamp(seg["start"]).replace(",", ".")
        lines.append(f"[{start}] {seg['text']}")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
