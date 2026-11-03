# 🗺️ ROADMAP.md — Big Plan v3 Execution Roadmap (ZZLUXORA v10)

**Peta Jalan Rekayasa Perangkat Lunak & Tahapan Implementasi Terstruktur**  
*Basis: Feedback v3, Standar Konsol grandMA2 / grandMA3 onPC / QLC+, & Impeccable Design System*

---

## 📌 Rencana Induk Rekayasa (Big Plan v3 Phases)

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      PETA JALAN PENGEMBANGAN v10                       │
├────────────────────────────────────────────────────────────────────────┤
│  FASE 1: Identitas Visual, Logo Arial Black Italic, & Asset [SELESAI] │
│  FASE 2: Rombak Shell (Native QMenuBar, Program Bar)       [SELESAI]  │
│  FASE 3: Jendela Pop-up Non-Modal Independen              [SELESAI]   │
│  FASE 4: Restrukturisasi 6 Tab Workspaces & Clean State    [SELESAI]  │
│  FASE 5: Pengujian Software-in-the-Loop (SITL QLC+)        [TERUJI]   │
│  FASE 6: Pengujian Lapangan (ESP32 + PAR LED) & Packaging  [SIAP]     │
│  FASE 7: Impeccable Design System & FOH Elevation          [SELESAI]  │
│  FASE 8: Audit Defect Menyeluruh (18 defect, 129 test)     [SELESAI]  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 🚀 FASE 1: Identitas Visual & Asset Deployment (STATUS: TUNTAS 100%)
- [x] **Logo Resmi Anti-Slop:** Huruf kapital "ZZ" (Arial Black Italic, solid black #000000, pure white #ffffff, no glow, rasio 1:1 di `ui/assets/logo_zz.png`).
- [x] **Asset Multi-Format:** Mengonversi asset ke multi-size icon (`.ico` 16x16 s.d. 256x256) untuk integrasi OS window title bar dan taskbar.
- [x] **Aplikasi Identitas:** Mengikat logo resmi ke `setWindowIcon()` dan `setWindowTitle("ZZLUXORA [Untitled.zlx]")`.

---

### 🎛️ FASE 2: Rombak Total Shell & Header (STATUS: TUNTAS 100%)
- [x] **Eliminasi Sidebar Total:** Menghapus navigasi vertikal samping (`sidebar.py`) guna membebaskan area kerja horizontal.
- [x] **Header Desktop Bersih:**
  * **OS Window Title Bar:** Memuat logo resmi `ZZ` + Judul format bersih `ZZLUXORA [NamaFile.zlx]`.
  * **Menu Bar (Native QMenuBar):** Pure native menu bar (`[File]` `[Fixture]` `[Editor]` `[Preview]` `[Setting]` `[Help]` `[About]`).
  * **Program View Bar:** 6 tab workspace di kiri, status Art-Net + tombol Blackout + tombol Play/Stop toggle di kanan.
- [x] **Transmisi Play-Gated:** Paket DMX hanya dikirimkan ketika tombol PLAY aktif.
- [x] **Pemberian Shortcut Global:**
  * `Ctrl+O`: Open Project
  * `Ctrl+S`: Save Project
  * `Ctrl+Shift+S`: Save As Project
  * `Space`: Play/Stop Toggle Art-Net
  * `Escape` / `B`: Blackout
  * `Ctrl+Z` / `Ctrl+Shift+Z`: Global Undo / Redo

---

### 🪟 FASE 3: Implementasi Jendela Pop-up Mandiri (STATUS: TUNTAS 100%)
- [x] **Fixture List Window:**
  * Jendela independen non-modal dengan tombol *Minimize, Maximize, Close*.
  * Memuat pustaka fixture `.zfx` / JSON.
  * Mendukung aksi **Drag and Drop** langsung ke sel grid Tab Address.
- [x] **Fixture Definition Editor Window:**
  * Jendela editor profil lampu terisolasi berstandar QLC+ Fixture Editor.
  * Menubar mandiri: File -> Open, Save, Save As (`.zfx` / `.json`).
  * Profil ZZLUXORA 8-CH: `fixtures/generic_par_rgbw_8ch.zfx`.
  * Definisi fixture native QLC+: `fixtures/ZZLUXORA-PAR-RGBW-8CH.qxf`.
- [x] **Stage Visualizer Window:**
  * Jendela visualizer panggung non-modal (dapat dipindah ke second monitor FOH).
  * Tab 2D: Tampak depan panggung dengan pendaran cahaya lingkaran RGBW dinamis.
- [x] **Network Setting Dialog:**
  * Pemindaian otomatis adapter jaringan lokal.
  * Preset wajib: `127.0.0.1` (SITL QLC+), `192.168.4.1` (ESP32 AP), Custom IP, Universe 0.
- [x] **Help & About Windows:**
  * Help: Panduan penggunaan & tabel shortcut keyboard lengkap.
  * About: Keterangan resmi skripsi (Andreas, NIM 5312422036, Dospem Mario Norman Syah, S.Pd., M.Eng., UNNES).

---

### 📑 FASE 4: Restrukturisasi 6 Tab Workspaces (STATUS: TUNTAS 100%)
- [x] **Clean Initial State:** Seluruh tab dimulai dalam kondisi 100% kosong tanpa demo otomatis yang membingungkan operator.
- [x] **Berkas Demo Khusus:** `showfiles/demo_church_worship.zlx` disediakan untuk memuat demo kapan saja via `File -> Open Project...`.
- [x] **Tab 1 — Address:**
  * Matriks 256 kanal DMX (maksimal 24 kolom horizontal, sel compact 46x46px).
  * Tag fungsi teknis (`DIM`, `RED`, `GRN`, `BLU`, `WHT`, `STR`).
  * Tombol [CLEAR PATCH], [AUTO PATCH (4 PAR)], [UNDO], [REDO].
- [x] **Tab 2 — Analyze (Core Skripsi):**
  * Pemuat audio multi-format (`.wav`, `.mp3`, `.flac`, `.ogg`).
  * Input tautan YouTube via dialog pop-up mandiri (`YouTubeDialog`).
  * Analisis asinkron berbasis `QThread`: area analisis diburamkan tanpa freeze.
  * Progress bar saintifik dengan teks penjelasan proses DSP real-time.
- [x] **Tab 3 — Result:**
  * Dashboard metrik audio lagu rohani.
  * Visualisasi koordinat afektif Russell 2D Plane ($V, A$), BPM, akord Chroma, kuadran mood.
  * Tombol [RE-ANALYZE] dan [EXPORT TO PERFORM].
- [x] **Tab 4 — Perform:**
  * Manajemen playlist urutan lagu pertunjukan live ([MOVE UP], [MOVE DOWN], [DELETE]).
  * Pengaturan section cues dan transisi fade.
  * Tombol [GENERATE EXECUTORS] mengonversi playlist ke Tab Page secara otomatis.
- [x] **Tab 5 — Page:**
  * Halaman tombol eksekutor virtual interaktif bergaya grandMA & QLC+ (dimulai bersih).
  * Tombol cue (Praise, Worship, Verse, Chorus) dan Flash Strobe.
- [x] **Tab 6 — Mixer:**
  * Meja fader virtual 257 fader: 1 Grand Master Dimmer + 256 Kanal DMX.
  * Fader taktil grandMA (tinggi 190px, lebar 52px, cap bertakik 30x18, rel ber-LED menyala, garis skala analog).
  * Tombol [RESET DMX], [FULL MASTER], [REFRESH].

---

### 🔄 FASE 5: Verifikasi Software-in-the-Loop (STATUS: TERUJI)
- [x] Pengujian streaming paket DMX 43 FPS dari ZZLUXORA v10 ke QLC+ via Art-Net `127.0.0.1:6454` Universe 0.
- [x] Verifikasi Play-gated packet transmission: transmisi hanya terjadi saat tombol PLAY menyala.
- [x] Pengujian Blackout seketika memadamkan seluruh output DMX ke 0.
- [x] 65 dari 65 unit test di `tests/` lulus 100% (per 8 Okt 2026).

---

### 🎨 FASE 7: Impeccable Design System & FOH Elevation (STATUS: TUNTAS 100%)
*Basis: Big Plan Impeccable (commit `f938987`, 7 Oktober 2026)*

**Fase 1 — Design Truth:**
- [x] `PRODUCT.md` (Impeccable product-schema 1): platform, users (LD/FOH), operate mode, brand commitments.
- [x] `DESIGN.md` bertoken (YAML frontmatter valid): Creative North Star *"The Obsidian Control Deck"*, 10% accent rule, 7-state matrix.

**Fase 2 — Token Centralization:**
- [x] 70+ inline hex dipindah ke `Theme` semantic tokens (surface ramp, status tint, hardware drawing, scene/rigging).
- [x] `CONSOLE_QSS` diperluas: QGroupBox, QSplitter, QProgressBar, QListWidget, QToolTip global.

**Fase 3 — Anti-Slop Chrome:**
- [x] Transport `[PREV]` / `[GO+]` / `[FADE BLACK]` (emoji dibuang), ikon hamburger vektor QPainter, `[OK]` status, separator pipe `|`.

**Fase 4 — FOH Elevation:**
- [x] TactileFader: skala terukir `FL`/`50`/`0`, light-pipe LED dual-pass, ribs ganda emboss, dimensi lama dipertahankan (68x230 / 52x190).
- [x] Mixer: patch-aware tags (`AL36-1:DIM`) + indikator bank aktif mengikuti scroll viewport.
- [x] Address: bracket boundary fixture (`start`/`mid`/`end`), drag-hover preview mengikuti footprint asli fixture (bukan hardcode 8), kontras WCAG per tipe kanal.
- [x] Perform: `[GO+]` 48px commanding + hitung mundur crossfade live (`set_crossfade_progress` / `reset_crossfade_progress`).

**Fase 5 — Verifikasi:**
- [x] 41 unit test baru (saat itu total **65/65 lulus**), audit anti-slop 0 em-dash/en-dash/emoji/inline-hex, CLI Art-Net exit 0.
- [x] Diperluas menjadi **129 test** setelah audit menyeluruh (lihat FASE 8 di bawah).

**Ditunda atas pilihan owner:** *Live Cue Ribbon* (swatch RGBW + pan/tilt per cue) — belum dibuat.

---

### 🔍 FASE 8: Audit Defect Menyeluruh (STATUS: TUNTAS, 16 Okt 2026)

Audit adversarial atas seluruh permukaan aplikasi. Setiap temuan direproduksi lebih dulu, lalu ditutup uji regresi. **18 defect diperbaiki**, suite 65 menjadi **129 test**.

**Kritis (data/klaim salah):**
- [x] Audio **diam** dan berkas 0-sampel dilaporkan `"C Major (Praise character)"` + `Q3_DEEP_WORSHIP`. Alat penelitian mengarang bukti; kini tonality digerbangi energi kroma dan kuadran menjadi `Idle`.
- [x] Alamat awal DMX rusak saat simpan (rumus modulo-8): fixture di DMX 18 tertulis 17, **9 dari 15 posisi**. Kini 0 dari 15.
- [x] Visualizer 3D: pada pitch bawaan tepat 0 radian, lantai panggung, beam cone, dan floor pool menjadi poligon berluas nol alias tidak terlihat.
- [x] Tombol FLASH: melepas tombol memadamkan panggung dan mengunci kanal warna.
- [x] `ArtNetSender.blackout()` melempar OSError pada socket tertutup.

**Analisis dan hasil:**
- [x] Field hasil yang kosong tampil sebagai angka karangan (`1850 Hz`, `0.500`, `R:255 G:255`); kini `- (not measured)` dan Export hanya aktif bila lengkap.
- [x] Metrik tekstur dilaporkan pada skala mentah (flux 0-258, MFCC 24-48) padahal dilabeli indeks; kini 0-1.
- [x] Metrik lagu sebelumnya tetap tampil setelah analisis ulang gagal.
- [x] Kuadran Q2_INTENSE_REVERENCE diberi cue Praise; kini punya set Reverence sendiri.

**Fixture Editor:**
- [x] Mengubah jumlah kanal menghapus seluruh label dan tipe yang sudah diketik.
- [x] Save menghilangkan `id`/`model`/`type`, menulis ulang berkas resmi ke skema salah.
- [x] Widget sel bocor tanpa batas (24 menjadi 264).
- [x] Berkas rusak atau 0-kanal dimuat sebagai fixture hidup; kini ditolak dengan alasan.
- [x] Write non-atomik dan nama berkas tidak divalidasi.
- [x] Tidak melacak perubahan belum disimpan (editor reuse bisa menulis ulang berkas yang tak pernah dibuka).

**Visualizer dan shell:**
- [x] Seleksi 2D dan 3D tidak sinkron; geser slider menggeser fixture yang tidak dipilih.
- [x] Geser grup menumpuk seluruh anggota di satu titik alih-alih mempertahankan jarak.
- [x] Timer haze 30 FPS terus berjalan setelah jendela ditutup.
- [x] Hit-test 3D berhenti pada kecocokan pertama; fixture bertumpuk tak dapat dipilih.
- [x] Slider di panggung kosong menyimpan pivot dan menggeser permanen patch berikutnya.
- [x] BLACKOUT tidak memadamkan 256 fader kanal dan sempat mengirim frame basi ke rig.
- [x] Semua pintasan konsol mati saat jendela popup non-modal terbuka.
- [x] Lencana Art-Net menyatakan TRANSMITTING tanpa dasar; kini OUTPUT STREAMING.
- [x] Path proyek hardcoded di lima tempat sehingga gagal di luar `$HOME/ANDREAS`.
- [x] Tombol kontrol FPS tidak terhubung ke apa pun.

**Infrastruktur uji:**
- [x] `tools/_autodialog_guard.py` dan `tools/run_tests_guarded.py` menjalankan seluruh suite tanpa memunculkan dialog di layar operator.

---

### ⚡ FASE 6: Pengujian Lapangan Hardware & Deployment (SIAP DIJALANKAN)
- [ ] Uji coba koneksi Wi-Fi ke SoftAP ESP32 (`192.168.4.1`) di laptop ASUS X407MA.
- [ ] Uji coba pengontrolan fisik 4 unit PAR LED RGBW via kabel DMX512 XLR 3-pin di Gereja GIA Deliksari.
- [ ] Build installer executable Windows 11 (`.exe` via Inno Setup) di laptop Acer Swift 3.
- [x] Sinkronisasi penuh ke repositori GitHub `zzdevxx/zzluxora-v10` sebagai Single Source of Truth.
