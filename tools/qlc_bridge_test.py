"""
qlc_bridge_test.py - Art-Net Loopback Bridge Test for QLC+ Simulation
Sends continuous DMX512 frames to 127.0.0.1:6454 (Universe 0) to verify
that QLC+ Simple Desk / Virtual Console faders move in real time without physical hardware.
Integrated with ColorEngine (Russell 2D V-A plane & physical RGBW decomposition)
and official fixtures: Kumastb STL47 (8CH RGBW) & Alien AL36 (8CH RGB).
"""

import sys
import time
import math
import argparse
from pathlib import Path

# Ensure root directory in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.artnet_sender import ArtNetSender
from core.models import EmotionCoordinate, ColorRGBW
from core.color_engine import ColorEngine


def run_fader_test(target_ip: str = "127.0.0.1", duration: float = 30.0, fixture_model: str = "kumastb"):
    model_name = "Kumastb STL47 (8CH RGBW)" if fixture_model == "kumastb" else "Alien AL36 (8CH RGB)"
    is_rgbw = (fixture_model == "kumastb")
    fix_desc = "1 Unit Bench Test (DMX001)" if is_rgbw else "4 Units GIA Stage (DMX001, DMX017, DMX033, DMX049)"

    print("=" * 76)
    print("ZZLUXORA -> QLC+ ART-NET LOOPBACK BRIDGE TEST (SITL)")
    print("=" * 76)
    print(f"Target Host      : {target_ip}:6454 (UDP Art-Net)")
    print(f"Target Universe  : 0 (maps to Universe 1 in QLC+)")
    print(f"Active Fixture   : {model_name}")
    print(f"Addressing Map   : {fix_desc}")
    print(f"Color Pipeline   : Russell 2D Plane (V, A) -> HSV -> Physical {'RGBW' if is_rgbw else 'RGB'}")
    print(f"Transmission FPS : 43.07 FPS (Standard DMX refresh)")
    print("-" * 76)
    print("QLC+ Setup Instructions:")
    print("1. Open QLC+ -> open workspace showfiles/zzluxora_test.qxw")
    print("   or open the 'Inputs/Outputs' tab and check 'Input' for Universe 1, ArtNet 127.0.0.1.")
    print("2. Open the 'Simple Desk' or 'Virtual Console' tab in QLC+.")
    print("3. Channel faders move in real time with the audio mood!")
    print("=" * 76)
    print("Starting Art-Net packet transmission (Press Ctrl+C to stop)...\n")

    sender = ArtNetSender(target_ip=target_ip, universe=0)
    start_time = time.time()
    frame_count = 0

    try:
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            t = elapsed * 1.5

            # Simulate dynamic audio mood cycle (Praise Q1 -> Worship Q3)
            # Valence and Arousal sinusoidal orbital trajectory
            v = math.sin(t * 0.7)
            a = math.cos(t * 0.9)
            rms = (math.sin(t * 1.8) + 1.0) * 0.4 + 0.2  # RMS dynamic energy

            emotion = EmotionCoordinate(valence=v, arousal=a)
            h, s, val = ColorEngine.emotion_to_hsv(emotion, rms_energy=rms, master_dimmer=1.0)
            base_r, base_g, base_b = ColorEngine.hsv_to_rgb(h, s, val)

            if is_rgbw:
                # Kumastb STL47: 1 unit bench testing at DMX001
                rgbw = ColorEngine.rgb_to_physical_rgbw(base_r, base_g, base_b, dimmer=1.0)
                r, g, b, w = rgbw.to_dmx_bytes()
                master_dim = int(round(val * 255.0))
                # Ch 1-8: Dimmer, Red, Green, Blue, White, Strobe, Program, Speed
                sender.set_channels(1, [master_dim, r, g, b, w, 0, 0, 0])
                status_str = f"KUMA (DMX001): [DIM:{master_dim:3d} R:{r:3d} G:{g:3d} B:{b:3d} W:{w:3d}]"
            else:
                # Alien AL36: 4 units at DMX001, DMX017, DMX033, DMX049
                alien_starts = [1, 17, 33, 49]
                for fix_idx, start_ch in enumerate(alien_starts):
                    offset_rad = fix_idx * 0.5
                    fix_v = math.sin(t * 0.7 + offset_rad)
                    fix_a = math.cos(t * 0.9 + offset_rad)
                    fix_rms = max(0.1, min(1.0, rms + math.sin(t * 2.0 + offset_rad) * 0.2))

                    fix_emo = EmotionCoordinate(valence=fix_v, arousal=fix_a)
                    fh, fs, fval = ColorEngine.emotion_to_hsv(fix_emo, rms_energy=fix_rms, master_dimmer=1.0)
                    fr, fg, fb = ColorEngine.hsv_to_rgb(fh, fs, fval)
                    master_dim = int(round(fval * 255.0))

                    # 8-CH: Dimmer, Red, Green, Blue, Empty, Program, Speed, Emptz
                    sender.set_channels(start_ch, [master_dim, fr, fg, fb, 0, 0, 0, 0])

                status_str = f"ALIEN (DMX001, 017, 033, 049) | FIX#1: [DIM:{int(round(val * 255.0)):3d} R:{base_r:3d} G:{base_g:3d} B:{base_b:3d}]"

            sender.send_frame()
            frame_count += 1

            print(f"\r[Art-Net TX] Frame {frame_count:04d} | Mood: (V:{v:+.2f}, A:{a:+.2f}) | {status_str} | Time: {elapsed:.1f}s", end="", flush=True)

            time.sleep(1.0 / 43.07)

            print(f"\r[Art-Net TX] Frame {frame_count:04d} | Mood: (V:{v:+.2f}, A:{a:+.2f}) | {status_str} | Time: {elapsed:.1f}s", end="", flush=True)

            time.sleep(1.0 / 43.07)

    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")
    finally:
        print("\nTurning off faders (Blackout)...")
        sender.blackout()
        sender.close()
        print("All DMX channels reset to 0. Session complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZZLUXORA Art-Net Loopback Bridge Test for QLC+")
    parser.add_argument("--ip", default="127.0.0.1", help="Target Art-Net IP address (default: 127.0.0.1)")
    parser.add_argument("--duration", type=float, default=30.0, help="Test duration in seconds (default: 30)")
    parser.add_argument("--fixture", choices=["kumastb", "alien"], default="kumastb",
                        help="Fixture model to simulate: 'kumastb' (8CH RGBW) or 'alien' (8CH RGB)")
    args = parser.parse_args()

    run_fader_test(target_ip=args.ip, duration=args.duration, fixture_model=args.fixture)
