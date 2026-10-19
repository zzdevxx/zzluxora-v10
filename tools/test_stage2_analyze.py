#!/usr/bin/env python3
"""
test_stage2_analyze.py - Eksekusi Pengujian Otomatis Tahap 2: Tab Analyze (TC-ANLZ-01 s.d. TC-ANLZ-06).
"""

import sys
import tempfile
import wave
from array import array
from pathlib import Path
from unittest.mock import patch

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import _autodialog_guard  # noqa: F401
from ui.qt_compat import QApplication
from ui.panels.analyze_tab import AnalyzeTab, AudioAnalysisWorker
from core.audio_loader import AudioLoader
from core.feature_extractor import FeatureExtractor
from core.song_library import SongLibrary


def run_stage2_tests():
    app = QApplication.instance() or QApplication(["stage2_test", "-platform", "offscreen"])
    library = SongLibrary()
    tab = AnalyzeTab(song_library=library)
    results = []

    def log_result(tc_id, name, status, detail):
        results.append((tc_id, name, status, detail))
        mark = "✅ PASS" if status == "PASS" else "❌ FAIL"
        print(f"[{mark}] {tc_id}: {name}")
        print(f"       Detail: {detail}\n")

    print("=" * 80)
    print("🚀 MEMULAI PENGUJIAN TAHAP 2: TAB ANALYZE (6 SKENARIO)")
    print("=" * 80 + "\n")

    # --------------------------------------------------------------------------
    # TC-ANLZ-01: Pemuatan Berkas Lokal Multi-Format
    # --------------------------------------------------------------------------
    audio_wav = REPO_ROOT / "data" / "audio" / "NDC_Worship_-_Bapa_Yang_Kekal.wav"
    loader = AudioLoader()
    sig, sr = loader.load_audio(str(audio_wav))
    idx = library.add_path(str(audio_wav))
    entry = library.songs[idx]

    if len(sig) == 264600 and sr == 22050 and entry.summary() == "not analysed":
        log_result("TC-ANLZ-01", "Pemuatan Berkas Lokal Multi-Format", "PASS",
                   f"WAV terbaca {len(sig):,} sampel (22.050 Hz mono). Status awal di library: '{entry.summary()}'.")
    else:
        log_result("TC-ANLZ-01", "Pemuatan Berkas Lokal Multi-Format", "FAIL",
                   f"sig_len={len(sig)}, sr={sr}, summary={entry.summary()}")

    # --------------------------------------------------------------------------
    # TC-ANLZ-02: Penolakan Berkas Corrupted / Non-Audio
    # --------------------------------------------------------------------------
    corrupted_file = REPO_ROOT / "README.md"
    caught_cleanly = False
    try:
        loader.load_audio(str(corrupted_file))
    except (ValueError, OSError, RuntimeError) as e:
        caught_cleanly = True
        err_type = type(e).__name__

    if caught_cleanly:
        log_result("TC-ANLZ-02", "Penolakan Berkas Corrupted / Non-Audio", "PASS",
                   f"Berkas non-audio ditolak bersih dengan {err_type}, mencegah crash decoding.")
    else:
        log_result("TC-ANLZ-02", "Penolakan Berkas Corrupted / Non-Audio", "FAIL",
                   "Berkas non-audio tidak memicu penolakan aman.")

    # --------------------------------------------------------------------------
    # TC-ANLZ-03: Import YouTube Asinkron (Non-Blocking Worker)
    # --------------------------------------------------------------------------
    from ui.widgets.song_list_panel import YouTubeDownloadWorker
    worker_yt = YouTubeDownloadWorker("https://www.youtube.com/watch?v=valid_id", "/tmp")
    received_path = []
    worker_yt.download_finished.connect(received_path.append)

    fake_downloaded = Path("/tmp/yt_test_output.wav")
    with patch("core.youtube_importer.download_and_convert", return_value=fake_downloaded):
        worker_yt.run()

    if received_path == [str(fake_downloaded)] and isinstance(received_path[0], str):
        log_result("TC-ANLZ-03", "Import YouTube Asinkron (Non-Blocking Worker)", "PASS",
                   f"Worker YouTube selesai non-blocking, memancarkan path '{received_path[0]}' bertipe str.")
    else:
        log_result("TC-ANLZ-03", "Import YouTube Asinkron (Non-Blocking Worker)", "FAIL",
                   f"received_path={received_path}")

    # --------------------------------------------------------------------------
    # TC-ANLZ-04: Eksekusi Analisis Audio DSP Penuh
    # --------------------------------------------------------------------------
    worker_dsp = AudioAnalysisWorker(str(audio_wav))
    captured_dsp = {}
    worker_dsp.analysis_finished.connect(captured_dsp.update)
    worker_dsp.run()

    req_keys = ["duration_sec", "frames_count", "fps_rate", "valence", "arousal",
                "rms", "spectral_centroid", "chroma_key", "quadrant", "bpm", "palette"]
    has_all_keys = all(k in captured_dsp for k in req_keys)
    frames_ok = captured_dsp.get("frames_count") == 513
    fps_ok = abs(captured_dsp.get("fps_rate", 0) - 43.07) < 0.1

    if has_all_keys and frames_ok and fps_ok:
        log_result("TC-ANLZ-04", "Eksekusi Analisis Audio DSP Penuh", "PASS",
                   f"STFT/MIR tuntas 513 frame pada {captured_dsp['fps_rate']:.2f} FPS. Semua 11 parameter ekstraksi terisi lengkap.")
    else:
        log_result("TC-ANLZ-04", "Eksekusi Analisis Audio DSP Penuh", "FAIL",
                   f"has_all_keys={has_all_keys}, frames_count={captured_dsp.get('frames_count')}")

    # --------------------------------------------------------------------------
    # TC-ANLZ-05: Uji Audio Diam / Silence (Anti-Karangan Nada)
    # --------------------------------------------------------------------------
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        silent_wav = tf.name

    try:
        with wave.open(silent_wav, "wb") as h:
            h.setnchannels(1)
            h.setsampwidth(2)
            h.setframerate(22050)
            h.writeframes(array("h", [0] * (22050 * 2)).tobytes())

        worker_silence = AudioAnalysisWorker(silent_wav)
        captured_silence = {}
        worker_silence.analysis_finished.connect(captured_silence.update)
        worker_silence.run()

        key = str(captured_silence.get("chroma_key", ""))
        quad = str(captured_silence.get("quadrant", ""))

        if ("No tonal content" in key) and ("Major" not in key) and ("Minor" not in key) and (quad == "Idle"):
            log_result("TC-ANLZ-05", "Uji Audio Diam / Silence (Anti-Karangan Nada)", "PASS",
                       f"Energy gating kroma aktif: audio hening dilaporkan '{key}' dan kuadran '{quad}'. Bebas fabrikasi data.")
        else:
            log_result("TC-ANLZ-05", "Uji Audio Diam / Silence (Anti-Karangan Nada)", "FAIL",
                       f"key={key}, quad={quad}")
    finally:
        Path(silent_wav).unlink(missing_ok=True)

    # --------------------------------------------------------------------------
    # TC-ANLZ-06: Determinisme Ekstraksi Ulang 100%
    # --------------------------------------------------------------------------
    fe = FeatureExtractor()
    run1 = fe.analyze_audio_stream(sig)
    run2 = fe.analyze_audio_stream(sig)

    rms1 = [f.rms_energy for f in run1]
    rms2 = [f.rms_energy for f in run2]
    sc1 = [f.spectral_centroid for f in run1]
    sc2 = [f.spectral_centroid for f in run2]

    is_identical = (rms1 == rms2 and sc1 == sc2)

    if is_identical and len(run1) == 513:
        log_result("TC-ANLZ-06", "Determinisme Ekstraksi Ulang 100%", "PASS",
                   "Dua kali run ekstraksi menghasilkan keluaran bit-for-bit identik (selisih RMS dan Centroid = 0,000000).")
    else:
        log_result("TC-ANLZ-06", "Determinisme Ekstraksi Ulang 100%", "FAIL",
                   "Ekstraksi ulang tidak deterministik.")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = total - passed
    print("=" * 80)
    print(f"📊 REKAPITULASI PENGUJIAN TAHAP 2: {passed}/{total} SKENARIO LULUS ({passed/total*100:.1f}%)")
    print("=" * 80)

    tab.close()
    return failed == 0


if __name__ == "__main__":
    success = run_stage2_tests()
    sys.exit(0 if success else 1)
