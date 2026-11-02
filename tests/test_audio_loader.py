import os
import tempfile
import unittest
import wave

import numpy as np

from core.audio_loader import AudioLoader


class TestAudioLoader(unittest.TestCase):
    def test_loads_pcm_wav_to_normalized_mono_samples(self):
        sample_rate = 22050
        samples = np.array([-32768, -16384, 0, 16384, 32767], dtype=np.int16)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "known_pcm.wav")
            with wave.open(path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(samples.tobytes())

            audio, loaded_rate = AudioLoader(target_sample_rate=sample_rate).load_audio(path)

        self.assertEqual(loaded_rate, sample_rate)
        self.assertEqual(audio.shape, samples.shape)
        self.assertTrue(np.isfinite(audio).all())
        self.assertGreaterEqual(float(audio.min()), -1.0)
        self.assertLessEqual(float(audio.max()), 1.0)
        np.testing.assert_allclose(audio, samples.astype(np.float32) / 32768.0, atol=1e-6)

    def test_unsupported_audio_file_has_clear_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "not_audio.xyz")
            with open(path, "wb") as source:
                source.write(b"not an audio file")

            with self.assertRaisesRegex(RuntimeError, "Cannot decode audio file"):
                AudioLoader().load_audio(path)

    def test_missing_wav_path_raises_file_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "missing.wav")

            with self.assertRaises(FileNotFoundError):
                AudioLoader().load_audio(path)

    def test_decode_failure_reports_the_actual_cause(self):
        """A broken file must not be blamed on a missing soundfile.

        The loader used to swallow any exception from the soundfile branch with
        a bare ``except Exception: pass`` and then say "please install
        soundfile or convert to PCM WAV". That message was wrong whenever
        soundfile was installed and the real problem was the file itself, so the
        operator was sent looking for the wrong fault.
        """
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "broken.wav")
            with open(path, "wb") as source:
                source.write(b"this is not audio at all" * 100)

            with self.assertRaises(RuntimeError) as caught:
                AudioLoader().load_audio(path)

            message = str(caught.exception)
            self.assertIn("Cannot decode audio file", message)
            self.assertNotIn("install soundfile", message.lower())

    def test_permission_error_is_not_swallowed(self):
        """An unreadable file is an I/O fault, not a decode fallback."""
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root bypasses POSIX permission bits")
        if os.name == "nt":
            self.skipTest("Windows does not support POSIX permission revocation via chmod")

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "locked.wav")
            with wave.open(path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(22050)
                wav_file.writeframes(b"\x00\x00" * 512)

            os.chmod(path, 0o000)
            try:
                with self.assertRaises(PermissionError):
                    AudioLoader().load_audio(path)
            finally:
                os.chmod(path, 0o644)

    def test_directory_named_wav_is_not_swallowed(self):
        """A directory is not audio; the error must surface, not be hidden."""
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "folder.wav")
            os.makedirs(path)

            with self.assertRaises((IsADirectoryError, PermissionError)):
                AudioLoader().load_audio(path)


if __name__ == "__main__":
    unittest.main()
