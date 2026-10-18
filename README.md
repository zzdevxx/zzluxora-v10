# 🎛️ ZZLUXORA v10.0.0 — Next-Gen Production Stage Lighting Console

> **Tugas Akhir / Skripsi Sarjana Teknik Komputer**  
> **Judul:** *"Rancang Bangun Sistem Audio-Reactive Lighting Design Berbasis Analisis Mood Lagu Rohani dengan Pemetaan Warna HSV-RGBW dan Protokol Art-Net DMX512"*  
> **Peneliti:** Andreas Restuawanta Christwara (`NIM: 5312422036`)  
> **Dosen Pembimbing:** Mario Norman Syah, S.Pd., M.Eng.  
> **Institusi:** Program Studi S1 Teknik Komputer, Jurusan Teknik Elektro, Fakultas Teknik, Universitas Negeri Semarang (UNNES)

---

## 🌟 Fitur Utama

1. **Pure Zero-GUI Core Engine:**
   - Komputasi STFT diskrit dengan Hann Windowing ($f_s = 22.050\text{ Hz}$, $N=2048$, $H=512$, laju $\approx 43\text{ FPS}$ selaras dengan DMX512).
   - Ekstraksi Fitur Akustik Spektral: RMS Energy, Spectral Centroid, Chroma 12-Semitone, dan MFCC.
   - Pemodelan Emosi Musik 2D Russell (Valence-Arousal).
   - Dekomposisi 4-Kanal Physical RGBW untuk mencegah desaturasi warna pada lampu PAR LED panggung.
   - Art-Net 4 DMX512 Transmitter (UDP port 6454 ke ESP32 Node atau simulator).

2. **Antarmuka Konsol Panggung (grandMA3 & QLC+ Inspired):**
   - Desain gelap (*dark industrial console*), modern-minimalis, tanpa ikon/emoji berlebih.
   - Header Bar terintegrasi: status Art-Net live, toggle Play/Pause, dan tombol instan Blackout.
   - Tab Address: Grid patch DMX maksimal 24 kolom horizontal dengan indikator visual kanal.
   - Tab Mixer: 513 Slider Fader (1 Master Dimmer + 512 Kanal DMX fisik) bernilai 0–255.
   - Tab Preview: Visualisasi panggung 2D tampak depan dengan draggable fixture dan panel koordinat.
   - Fixture Editor: Pembuat profil lampu custom format JSON.

---

## 🚀 Menjalankan Core Engine (CLI Standalone)

Untuk menguji mesin komputasi sinyal dan transmisi Art-Net secara mandiri tanpa GUI:

```bash
# Jalankan demo streaming Art-Net ke localhost
python3 main.py --cli --duration 4.0

# Jalankan ke IP modul ESP32 panggung (Mode AP: 192.168.4.1)
python3 main.py --cli --ip 192.168.4.1 --duration 10.0
```

---

## 🧪 Menjalankan Pengujian (Unit Tests)

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Seluruh 11 pengujian unit (FFT, dekomposisi RGBW, emosi, paket Art-Net, dan I/O project) akan terverifikasi 100% lulus.

---

## 📄 Hak Cipta & Lisensi

Hak Cipta (C) 2026 Andreas Restuawanta Christwara. Seluruh hak cipta dilindungi undang-undang.
