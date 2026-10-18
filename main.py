"""
ZZLUXORA v10.0.0 - Flagship Stage Lighting Control & Autonomous Audio-Reactive Engine
Developed for S1 Teknik Komputer FT Universitas Negeri Semarang (UNNES).
Peneliti: Andreas Restuawanta Christwara (NIM: 5312422036)
Dosen Pembimbing: Mario Norman Syah, S.Pd., M.Eng.
"""

from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path

# Ensure root directory in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core import (
    STFTEngine,
    ColorEngine,
    EmotionModel,
    ArtNetSender,
    AudioLoader,
    FeatureExtractor,
    ProjectIO,
)


def run_cli_demo(target_ip: str = "127.0.0.1", duration: float = 3.0) -> None:
    """Runs a standalone demonstration of the core FFT & Art-Net lighting engine."""
    print("=" * 70)
    print("ZZLUXORA v10.0.0 - CORE ENGINE STANDALONE RUNTIME")
    print("   Autonomous Audio-Reactive Stage Lighting Architecture")
    print("=" * 70)
    print(f"Target Art-Net Node IP : {target_ip}:6454 (Universe 0)")
    print(f"Sample Rate / Window   : 22,050 Hz | N_FFT = 2048 | Hop = 512 (laju analisis ~43.07 FPS)")

    loader = AudioLoader()
    print("\n[1/3] Generating synthetic Praise & Worship acoustic stream...")
    signal = loader.generate_synthetic_praise_beat(duration_sec=duration)
    print(f"      Signal generated: {len(signal):,} audio samples (~{duration} seconds)")

    print("\n[2/3] Executing STFT & Feature Extraction Pipeline (FFT/Chroma/Centroid/RMS)...")
    extractor = FeatureExtractor()
    t0 = time.time()
    frames = extractor.analyze_audio_stream(signal)
    t_elapsed = time.time() - t0
    print(f"      Analyzed {len(frames)} frames in {t_elapsed * 1000.0:.2f} ms ({len(frames) / t_elapsed:.1f} fps speedup)")

    print("\n[3/3] Streaming Art-Net 4 DMX512 frames to network...")
    artnet = ArtNetSender(target_ip=target_ip, universe=0)
    print("      Stream started (Press Ctrl+C to stop)...")

    try:
        for idx, f in enumerate(frames):
            # Patch to PAR LED channels 1-4
            artnet.set_channels(1, [f.color.red, f.color.green, f.color.blue, f.color.white])
            artnet.send_frame()

            bar = "#" * int(f.rms_energy * 20)
            bar = bar.ljust(20, "-")
            print(f"\rFrame {idx+1:03d}/{len(frames):03d} [{f.time_sec:.2f}s] "
                  f"RMS: [{bar}] | "
                  f"Centroid: {f.spectral_centroid:4.0f}Hz | "
                  f"Valence: {f.emotion.valence:+0.2f} | "
                  f"Arousal: {f.emotion.arousal:+0.2f} | "
                  f"RGBW: ({f.color.red:3d}, {f.color.green:3d}, {f.color.blue:3d}, {f.color.white:3d})",
                  end="", flush=True)
            time.sleep(1.0 / 43.0)
    except KeyboardInterrupt:
        print("\n\nUser interrupted stream.")
    finally:
        print("\n\nExecuting Blackout command...")
        artnet.blackout()
        artnet.close()
        print("All DMX channels reset to 0. Session complete.")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZZLUXORA v10 Stage Lighting Control Console")
    parser.add_argument("--cli", action="store_true", help="Run standalone CLI engine demonstration")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="Target Art-Net node IP (default: 127.0.0.1)")
    parser.add_argument("--duration", type=float, default=4.0, help="Demo duration in seconds")
    parser.add_argument("project", nargs="?", help="Optional .zlx showfile to load at startup")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_argument_parser().parse_args(argv)

    # If --cli or DISPLAY is not available, run CLI
    if args.cli or "DISPLAY" not in os.environ:
        run_cli_demo(target_ip=args.ip, duration=args.duration)
    else:
        # Check if Qt (PySide6 or PyQt6) is available for GUI
        try:
            from ui.qt_compat import QApplication, QIcon, HAS_QT
            if not HAS_QT:
                raise ImportError("No Qt binding available")
            from ui.main_window import MainWindow
            app = QApplication(sys.argv)
            logo_path = BASE_DIR / "ui" / "assets" / "logo_zz.png"
            if logo_path.exists():
                app.setWindowIcon(QIcon(str(logo_path)))
            window = MainWindow()
            if args.project:
                window.load_project_file(args.project, notify=False)
            window.show()
            sys.exit(app.exec())
        except ImportError as e:
            print(f"Qt GUI runtime not available ({e}). Running CLI engine mode...")
            run_cli_demo(target_ip=args.ip, duration=args.duration)


if __name__ == "__main__":
    main()
