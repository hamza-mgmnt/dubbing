import os
import sys
import asyncio
import subprocess
import tempfile
import logging
import math
from typing import Callable, Optional, List, Dict, Any

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import edge_tts

from voices import get_voice_for_speaker, LANGUAGE_VOICES

logger = logging.getLogger("dubbing_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class DubbingEngine:
    def __init__(self, whisper_model_size: str = "base", device: str = "auto"):
        """
        Initializes the Dubbing Engine.
        Device: 'cpu', 'cuda', or 'auto' (detects CUDA availability).
        """
        self.model_size = whisper_model_size
        self.device = self._resolve_device(device)
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        logger.info(f"Initialized DubbingEngine on device={self.device}, compute={self.compute_type}")
        self._whisper = None

    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    def _get_whisper(self):
        if self._whisper is None:
            logger.info(f"Loading faster-whisper model: {self.model_size} ({self.device})...")
            self._whisper = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4
            )
        return self._whisper

    # =========================================================================
    # Step 1: Audio Extraction & Video Metadata via FFmpeg
    # =========================================================================
    def extract_audio(self, video_path: str, output_wav_path: str) -> float:
        """
        Extracts 16kHz mono WAV audio from video using FFmpeg.
        Returns total duration in seconds.
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")

        info = sf.info(output_wav_path)
        logger.info(f"Extracted audio: {output_wav_path} (duration: {info.duration:.2f}s, sr: {info.samplerate})")
        return info.duration

    # =========================================================================
    # Step 2: Speech-to-Text Transcription with Timestamps
    # =========================================================================
    def transcribe(self, audio_path: str, source_lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Transcribes speech into timestamped segments using faster-whisper.
        """
        whisper = self._get_whisper()
        segments_raw, info = whisper.transcribe(
            audio_path,
            language=source_lang,
            beam_size=5,
            word_timestamps=False,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        segments = []
        for s in segments_raw:
            text = s.text.strip()
            if text:
                segments.append({
                    "id": len(segments),
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "text": text,
                    "speaker": "SPEAKER_00"  # Default, updated in diarization step
                })

        logger.info(f"Transcription complete: {len(segments)} segments detected. Detected lang: {info.language}")
        return segments

    # =========================================================================
    # Step 3: Speaker Diarization (Pyannote or Smart Acoustic Clustering)
    # =========================================================================
    def diarize(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]],
        hf_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Assigns speaker IDs (SPEAKER_00, SPEAKER_01, etc.) to each segment.
        Uses pyannote.audio if hf_token is available, otherwise falls back to
        acoustic feature clustering (MFCC-based KMeans) for zero-setup multi-speaker detection.
        """
        if not segments:
            return segments

        # 1. Try Pyannote if token provided
        if hf_token and hf_token.strip():
            try:
                logger.info("Attempting Pyannote 3.1 speaker diarization...")
                from pyannote.audio import Pipeline
                import torch

                pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=hf_token.strip()
                )
                if self.device == "cuda":
                    pipeline.to(torch.device("cuda"))

                diarization = pipeline(audio_path)

                # Match Whisper segments to Pyannote speaker turns by maximum overlap
                for seg in segments:
                    seg_start = seg["start"]
                    seg_end = seg["end"]
                    best_speaker = "SPEAKER_00"
                    max_overlap = 0.0

                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        overlap_start = max(seg_start, turn.start)
                        overlap_end = min(seg_end, turn.end)
                        overlap = max(0.0, overlap_end - overlap_start)
                        if overlap > max_overlap:
                            max_overlap = overlap
                            best_speaker = speaker

                    seg["speaker"] = best_speaker

                logger.info("Pyannote diarization successfully applied.")
                return segments
            except Exception as e:
                logger.warning(f"Pyannote diarization failed or token not accepted: {e}. Falling back to acoustic clustering.")

        # 2. Smart Acoustic Fallback (MFCC + Spectral Centroid clustering)
        logger.info("Running acoustic clustering fallback for speaker diarization...")
        try:
            import librosa
            from sklearn.cluster import KMeans

            y, sr = sf.read(audio_path)
            features = []
            valid_indices = []

            for idx, seg in enumerate(segments):
                s_idx = int(seg["start"] * sr)
                e_idx = int(seg["end"] * sr)
                chunk = y[s_idx:e_idx]

                if len(chunk) < sr * 0.3:  # Chunk too short (<0.3s)
                    continue

                # Extract MFCCs and spectral features for speaker voice profiling
                mfcc = librosa.feature.mfcc(y=chunk, sr=sr, n_mfcc=13)
                mfcc_mean = np.mean(mfcc, axis=1)
                mfcc_std = np.std(mfcc, axis=1)
                centroid = np.mean(librosa.feature.spectral_centroid(y=chunk, sr=sr))
                feature_vec = np.hstack([mfcc_mean, mfcc_std, [centroid]])
                features.append(feature_vec)
                valid_indices.append(idx)

            if len(features) >= 2:
                # Determine number of clusters (2 speakers default, up to 4 if segments plentiful)
                n_speakers = 2 if len(features) < 10 else min(4, len(features) // 3)
                kmeans = KMeans(n_clusters=n_speakers, random_state=42, n_init=10)
                labels = kmeans.fit_predict(features)

                for orig_idx, cluster_id in zip(valid_indices, labels):
                    segments[orig_idx]["speaker"] = f"SPEAKER_{cluster_id:02d}"

                logger.info(f"Acoustic clustering finished: assigned {n_speakers} speaker clusters.")
            else:
                for seg in segments:
                    seg["speaker"] = "SPEAKER_00"
        except Exception as ex:
            logger.warning(f"Acoustic clustering fallback encountered error: {ex}. Using default single speaker.")
            for seg in segments:
                seg["speaker"] = "SPEAKER_00"

        return segments

    # =========================================================================
    # Step 4: Text Translation (100% Free via deep-translator)
    # =========================================================================
    def translate_segments(self, segments: List[Dict[str, Any]], target_lang: str) -> List[Dict[str, Any]]:
        """
        Translates transcribed segments to target language using GoogleTranslator.
        """
        if not segments:
            return segments

        translator = GoogleTranslator(source="auto", target=target_lang)
        logger.info(f"Translating {len(segments)} segments to '{target_lang}'...")

        for seg in segments:
            try:
                translated = translator.translate(seg["text"])
                seg["translated_text"] = translated if translated else seg["text"]
            except Exception as e:
                logger.error(f"Translation failed for segment {seg['id']}: {e}")
                seg["translated_text"] = seg["text"]

        return segments

    # =========================================================================
    # Step 5: Multi-Voice Edge-TTS Generation with Audio Time-Stretching
    # =========================================================================
    async def generate_speech_for_segments(
        self,
        segments: List[Dict[str, Any]],
        target_lang: str,
        temp_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Generates TTS audio clips for each segment with assigned speaker voices.
        Includes smart time-stretching (speed sync) to match original segment durations.
        """
        # Map unique speakers to distinct voices
        unique_speakers = sorted(list(set(seg["speaker"] for seg in segments)))
        speaker_voice_map = {}
        for idx, spk in enumerate(unique_speakers):
            voice_info = get_voice_for_speaker(target_lang, idx)
            speaker_voice_map[spk] = voice_info
            logger.info(f"Mapped {spk} -> {voice_info['label']} ({voice_info['id']})")

        for seg in segments:
            seg["voice"] = speaker_voice_map[seg["speaker"]]
            text_to_speak = seg["translated_text"]
            voice_id = seg["voice"]["id"]

            raw_tts_path = os.path.join(temp_dir, f"raw_tts_{seg['id']}.mp3")
            wav_tts_path = os.path.join(temp_dir, f"synced_tts_{seg['id']}.wav")

            # 1. Generate Raw TTS audio with Edge-TTS
            communicate = edge_tts.Communicate(text_to_speak, voice_id)
            await communicate.save(raw_tts_path)

            # 2. Time-stretching & Speed Synchronization
            target_duration = max(0.5, seg["end"] - seg["start"])

            # Measure generated audio duration
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                raw_tts_path
            ]
            probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                gen_duration = float(probe_res.stdout.strip())
            except (ValueError, TypeError):
                gen_duration = target_duration

            # Speed factor: if TTS is longer than target slot, speed it up
            # Keep speed factor within natural bounds [0.75, 1.6]
            speed_factor = gen_duration / target_duration
            speed_factor = max(0.75, min(1.6, speed_factor))

            # Apply FFmpeg atempo filter to time-stretch without changing pitch
            filter_str = f"atempo={speed_factor:.2f}"
            if speed_factor > 2.0:
                filter_str = f"atempo=2.0,atempo={speed_factor / 2.0:.2f}"

            ffmpeg_sync_cmd = [
                "ffmpeg", "-y",
                "-i", raw_tts_path,
                "-filter:a", filter_str,
                "-ar", "16000",
                "-ac", "1",
                wav_tts_path
            ]
            subprocess.run(ffmpeg_sync_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            seg["audio_path"] = wav_tts_path

        return segments

    # =========================================================================
    # Step 6: Audio Assembly into Synchronized Master Track
    # =========================================================================
    def build_master_dubbed_audio(
        self,
        segments: List[Dict[str, Any]],
        total_duration: float,
        output_master_wav: str,
        sample_rate: int = 16000
    ):
        """
        Assembles all segment audio clips at their exact timeline start positions
        onto a clean master audio track using sample-accurate numpy buffering.
        """
        total_samples = int(math.ceil(total_duration * sample_rate))
        master_buffer = np.zeros(total_samples, dtype=np.float32)

        for seg in segments:
            audio_path = seg.get("audio_path")
            if not audio_path or not os.path.exists(audio_path):
                continue

            chunk, sr = sf.read(audio_path)
            if sr != sample_rate:
                import librosa
                chunk = librosa.resample(chunk, orig_sr=sr, target_sr=sample_rate)

            # Mono guarantee
            if len(chunk.shape) > 1:
                chunk = np.mean(chunk, axis=1)

            start_sample = int(seg["start"] * sample_rate)
            end_sample = start_sample + len(chunk)

            if start_sample >= total_samples:
                continue

            if end_sample > total_samples:
                chunk = chunk[:total_samples - start_sample]
                end_sample = total_samples

            # Overlay chunk onto master timeline
            master_buffer[start_sample:end_sample] += chunk.astype(np.float32)

        # Soft limiter / prevent audio clipping
        max_val = np.max(np.abs(master_buffer))
        if max_val > 1.0:
            master_buffer = master_buffer / max_val * 0.98

        sf.write(output_master_wav, master_buffer, sample_rate, subtype="PCM_16")
        logger.info(f"Master dubbed audio written to {output_master_wav}")

    # =========================================================================
    # Step 7: Final Video Remuxing with FFmpeg
    # =========================================================================
    def remux_video(
        self,
        original_video: str,
        dubbed_audio: str,
        output_video: str,
        audio_mode: str = "replace"
    ):
        """
        Combines original video with dubbed audio:
        - "replace": completely replaces original audio track with dubbed audio.
        - "duck": ducks original background audio to 15% and mixes with dubbed audio.
        Uses -c:v copy to retain 100% video quality with near-instant rendering.
        """
        if audio_mode == "duck":
            cmd = [
                "ffmpeg", "-y",
                "-i", original_video,
                "-i", dubbed_audio,
                "-filter_complex",
                "[0:a]volume=0.15[bg];[bg][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_video
            ]
        else:  # replace
            cmd = [
                "ffmpeg", "-y",
                "-i", original_video,
                "-i", dubbed_audio,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_video
            ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg video remuxing failed: {res.stderr}")

        logger.info(f"Successfully rendered final dubbed video: {output_video}")

    # =========================================================================
    # Orchestrator: Full End-to-End Pipeline
    # =========================================================================
    async def process_video(
        self,
        video_path: str,
        output_video_path: str,
        target_lang: str,
        hf_token: Optional[str] = None,
        audio_mode: str = "replace",
        progress_cb: Optional[Callable[[int, str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the complete multi-speaker AI video dubbing pipeline.
        Calls progress_cb(percent, status_message, extra_data) at each step.
        """
        async def report(pct: int, msg: str, data: Any = None):
            logger.info(f"[{pct}%] {msg}")
            if progress_cb:
                if asyncio.iscoroutinefunction(progress_cb):
                    await progress_cb(pct, msg, data)
                else:
                    progress_cb(pct, msg, data)

        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Audio Extraction
            await report(10, "Extracting audio track from video...")
            extracted_wav = os.path.join(temp_dir, "extracted.wav")
            total_duration = self.extract_audio(video_path, extracted_wav)

            # 2. Whisper Transcription
            await report(25, "Transcribing speech and extracting timestamps...")
            segments = self.transcribe(extracted_wav)
            if not segments:
                raise ValueError("No audible speech detected in the provided video.")

            # 3. Speaker Diarization
            await report(45, "Detecting distinct speakers and turns...")
            segments = self.diarize(extracted_wav, segments, hf_token=hf_token)

            # 4. Translation
            await report(60, f"Translating transcript into target language ({target_lang})...")
            segments = self.translate_segments(segments, target_lang)

            # 5. Multi-Voice Edge-TTS Generation & Sync
            await report(75, "Generating multi-speaker neural voices and time-aligning audio...")
            segments = await self.generate_speech_for_segments(segments, target_lang, temp_dir)

            # 6. Master Dubbed Audio Assembly
            await report(88, "Assembling synchronized master audio timeline...")
            master_dubbed_wav = os.path.join(temp_dir, "master_dubbed.wav")
            self.build_master_dubbed_audio(segments, total_duration, master_dubbed_wav)

            # 7. Remux Video
            await report(95, "Merging dubbed audio track with video...")
            self.remux_video(video_path, master_dubbed_wav, output_video_path, audio_mode=audio_mode)

            # 8. Complete
            await report(100, "Dubbing completed successfully!", {"segments": segments})

            return {
                "output_video": output_video_path,
                "duration": total_duration,
                "segments": segments
            }
