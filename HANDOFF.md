# HANDOFF.md - Briefing Agent Berikutnya

Dokumen ini untuk agent yang melanjutkan pekerjaan ZZLUXORA. Baca ini dulu sebelum menyentuh apa pun.

**Terakhir diperbarui:** 19 Oktober 2026 (sesi verifikasi black-box, penyelarasan Bab 4 & 5 naskah v5, serta sinkronisasi Tritunggal repositori)
**Oleh:** sesi integrasi riset skripsi & hardware

---

## 0. BACA INI DULU: 3 HAL DALAM 30 DETIK

1. **Jangan menambah test dengan `cat >>`.** Itu menaruh test setelah blok
   `if __name__ == "__main__"` sehingga `unittest` tidak mengumpulkannya dan
   suite tetap melaporkan lulus. Tujuh belas test pernah lolos seperti itu.
   Selengkapnya di **§2c**: ini jebakan paling menyesatkan di repo ini.
2. **Ubah UI tanpa melihat = menebak.** Pakai
   `QT_QPA_PLATFORM=offscreen PYTHONPATH=$PWD/tools python3 tools/shoot_ui.py`
   lalu **baca PNG-nya**. Empat kali dalam sesi terakhir kesimpulan dari kesan
   visual terbukti salah setelah sampel piksel diperiksa.
3. **Ukur sebelum mengklaim.** Beberapa klaim di naskah dan di memori sudah
   terbukti keliru; lihat **§4 Jebakan** dan **§2b** sebelum mempercayai angka.

---

## 1. Status Sekarang

| | |
|---|---|
| Software `zzdree/zzluxora-v10` | HEAD **`dd4411a`**, working tree **bersih**, sinkron `origin/main` |
| Naskah `zzdree/zzluxora-thesis` | HEAD **`b2fbbc7`**, bersih, sinkron (Bab 4 & 5 naskah v5 terisi data empiris) |
| Hardware `zzdree/esp32-artnet-dmx` | HEAD **`cddd36f`**, bersih, sinkron (firmware v4.0.1 pacing absolut & packet counter) |
| Test suite | **194 test unik lulus** (163 unittest + 31 pytest), exit 0 · jumlah wajib diperiksa, lihat §2c |
| Skenario Tab | **38/38 skenario per tab LULUS 100%** (`python3 tools/run_all_tab_scenarios.py`) |
| Anti-slop | **189 berkas, 0 error, 0 warning** |
| Uji Black-Box | **100,0% Pass Rate** (23 kasus software lulus dari 23 kasus; FB-24 N/A [VERIFIKASI LAPANGAN]) |
| Integrasi Ekosistem | **Tritunggal Sistem saling terhubung (cross-linked)** di seluruh README dan memori |

### Perintah wajib

```bash
cd ~/ANDREAS/zzluxora_v10

# uji 38 skenario per tab (Address s.d. Mixer)
python3 tools/run_all_tab_scenarios.py

# uji penuh suite resmi (WAJIB pakai wrapper ini, bukan unittest langsung)
PYTHONPATH=$PWD/tools python3 tools/run_tests_guarded.py

# PERIKSA JUMLAH test yang benar-benar dikumpulkan (bukan hanya status OK)
QT_QPA_PLATFORM=offscreen PYTHONPATH=$PWD/tools python3 -m pytest tests/ --collect-only -q | tail -1
# 194 tests collected. JANGAN menghitung dengan unittest discover: ia ikut
# mengumpulkan berkas gaya-pytest dan melaporkan 149, angka yang menyesatkan.
# Kalau turun mendadak, ada berkas test gagal diimpor.

# anti-slop
node scripts/check-anti-slop.js --summary

# memori
python3 ~/ANDREAS/agent-memory/tools/memlog.py search "kata kunci"

# TANGKAP LAYAR UI untuk penilaian visual (tanpa perlu layar sungguhan)
QT_QPA_PLATFORM=offscreen PYTHONPATH=$PWD/tools python3 tools/shoot_ui.py --outdir /tmp/zz_shots
```

**Kenapa wrapper?** Tanpa itu, pengujian memunculkan popup `QMessageBox` di layar operator (beberapa jalur yang diuji memang berakhir dengan dialog, mis. penyimpanan berkas). `tools/_autodialog_guard.py` menetralkannya lebih dulu.

**Batasan mesin ini:** RAM 3,6 GB dan hanya **2 CPU**. Suite penuh butuh 9-11 menit. Jangan menjalankan suite bersamaan dengan pekerjaan berat lain; `npm run deploy` akan terbunuh bila RAM tersisa di bawah 1 GB.

---

## 2. Yang Sudah Selesai (jangan dikerjakan ulang)

**FASE 8 audit menyeluruh.** 18 defect diperbaiki, masing-masing direproduksi dulu lalu dikunci uji regresi. Yang paling penting:

- **Alat analisis sempat mengarang bukti.** Audio diam dan berkas 0-sampel dilaporkan `"C Major (Praise character)"` + `Q3_DEEP_WORSHIP`. Kini tonality digerbangi energi kroma → `"No tonal content"` + kuadran `Idle`. **Ini kritis untuk Bab 4 skripsi:** tanpa perbaikan ini, tabel bisa memuat klaim tonalitas palsu.
- **Alamat DMX rusak saat simpan** (rumus modulo-8): fixture di DMX 18 tertulis 17, 9 dari 15 posisi. Kini 0 dari 15.
- **Visualizer 3D:** lantai panggung, beam cone, dan floor pool **tidak terlihat sama sekali** pada pitch bawaan tepat 0 radian (poligon berluas nol). Kini pitch 15 derajat.
- **Tombol FLASH:** melepas tombol memadamkan panggung dan mengunci kanal warna.
- **BLACKOUT:** sempat mengirim frame basi ke rig; tidak memadamkan 256 fader kanal.
- **Fixture Editor:** menghapus label saat jumlah kanal diubah; save kehilangan `id`/`model`/`type`; widget bocor 24→264; tidak melacak perubahan belum disimpan.
- **Pintasan konsol mati saat jendela popup terbuka.**
- **Impor YouTube** rusak 3 lapis + sukses palsu via audio sintetis.

Rincian lengkap: `markdowns/ROADMAP.md` bagian **FASE 8**.

---

## 2b. Audit Adversarial 16 Okt 2026 (di luar FASE 8)

Audit 14 agen lintas kode, firmware, dan naskah. Setiap temuan diuji dua lensa
(refutasi + reproduksi) dan dinyatakan kukuh hanya bila keduanya gagal membantah.
**Tujuh defect diperbaiki** (suite kini 163 test, lihat 2c untuk jebakan test):

Komit `bc2846b` (lima defect pertama):

1. `save_project` memotong berkas tujuan lebih dulu lalu menulis bertahap, sehingga
   kegagalan di tengah menghancurkan showfile (1973 byte menjadi 51 byte rusak).
   Kini atomik (temp + fsync + `os.replace`); jalur GUI disamakan.
2. `.zlx` dimuat tanpa gerbang skema, sehingga berkas QLC+ atau `target_ip`
   `"not-an-ip"` diterima dan Art-Net dikirim ke alamat tak valid. Kini lewat
   `ProjectIO.validate_payload()`.
3. BLACKOUT tidak menghentikan crossfade; panggung menyala kembali 23 ms kemudian.
4. RESET DMX lalu PLAY mengirim look lama (fader nol, buffer masih terisi).
5. Worker QThread YouTubeDialog bocor dan bisa dimusnahkan saat masih berjalan.

Dua bug tambahan ditemukan saat memperbaiki di atas: `_refresh_dependency_line()`
dipanggil sebelum `btn_download` dibuat (dialog YouTube melempar `AttributeError`
setiap dibuka), dan `QDialog.reject()` mematikan proses di bawah plugin offscreen.

Komit `d06469f` (dua defect terakhir, keduanya menyentuh kebenaran hasil):

6. **`Mode_score` memakai cosine, bukan Pearson** (`core/emotion_model.py`). Kedua
   profil Krumhansl 0,9495 serupa di bawah cosine, sehingga skor terkurung di
   ±0,1782 padahal naskah menjanjikan skala ±1; bobot terbesar Valence (0,50)
   praktis lumpuh. Kini vektor dipusatkan sebelum dikorelasi (Pearson sejati):
   skor untuk profil Mayor persis naik dari +0,0373 ke +0,2124, batas atas dari
   0,1782 ke 0,6123, dan masukan rusak tidak lagi melempar `ValueError`.
7. **Kanal putih terbuang ke fixture tanpa emitor putih** (`ui/main_window.py`).
   Palet worship mellow `(67,38,0,178)` sampai ke Alien AL36 sebagai R+G+B = 105
   alih-alih 639, dan cue putih murni menjadi `(0,0,0)` alias padam total. W kini
   dilipat kembali ke R/G/B bila tak ada kanal yang dapat menerimanya.

### ⚠️ KEPUTUSAN PEMBIMBING YANG MASIH DIBUTUHKAN (Keputusan 9)

Perbaikan #6 **tidak cukup** untuk menepati klaim naskah. Setelah diukur, akar
masalahnya ternyata **normalisasi relatif per-lagu**, bukan bobot suku mode:

- Setiap lagu selalu memuat frame dengan `SC_norm = 1,0` (miliknya sendiri),
  sehingga rerata `SC_norm` pada sepuluh berkas uji adalah **0,66–0,84** dan skor
  centroid selalu positif. Kontribusi centroid + MFCC terukur **+0,214 sampai
  +0,352**.
- Akibatnya **`V` positif untuk SEMUA lagu**, termasuk tiga lagu bermodus minor.
- **Menaikkan bobot mode tidak menolong:** pada bobot 0,80 pun (diuji) tiga lagu
  minor tetap `V > 0`, sebab suku mode hanya mampu ±0,61.

Naskah sudah diberi catatan kejujuran di `script_math_model.md` Bagian [2] dan
[3.2], serta Bab 2, dan Keputusan 9 (beserta Keputusan 10) sudah ditambahkan ke
`script/markdowns/script_konsultasi_pembimbing.md`. **Yang belum diputuskan:**
apakah normalisasi tetap relatif per-lagu (aman, naskah dibatasi pada perubahan
relatif) atau diubah ke skala absolut (klaim antar-lagu benar-benar berlaku, tetapi
**seluruh angka warna Bab 4 harus diregenerasi**). Ini keputusan metodologi Pak
Mario, bukan keputusan implementasi.

### Status angka Bab 4 setelah perbaikan #6

Angka pada Tabel 4.5 dan RGBW frame pertama Tabel 4.4 sudah diselaraskan dengan
mesin Pearson (RMS/centroid rata-rata **tidak berubah**, hanya dua koefisien
bergeser berarti). Tabel 4.6 (`V`/`A` per lagu) **belum diisi** karena masih
menunggu pemilihan lagu final; nilainya akan ikut mesin Pearson saat diisi.

---

## 2c. ⚠️ JEBAKAN SUITE TEST: BACA INI SEBELUM MENULIS TEST

**Tujuh belas test pernah "lulus" tanpa pernah dijalankan.** Penyebabnya cara
menambahkannya: `cat >> tests/berkas_test.py` menaruh test di **akhir berkas**,
dan setiap berkas test ini berakhir dengan

```python
if __name__ == "__main__":
    unittest.main()
```

sehingga test baru mendarat **setelah** blok itu. Kodenya sah secara sintaks
(berada di dalam `def`), jadi **tidak ada galat apa pun**, tetapi
`unittest.TestLoader` hanya mengumpulkan metode **dari kelas**. Suite tetap
melaporkan `OK`.

Yang terdampak justru verifikasi perbaikan paling kritis: `save_project` atomik,
gerbang skema `.zlx`, standar nama fixture, dan lifecycle dialog YouTube.

### Aturan yang harus dipatuhi

1. **Jangan pernah** menambah test dengan `cat >>`. Pakai `Edit` pada bagian
   dalam kelas, atau tulis di **atas** blok `if __name__`.
2. **`run_tests_guarded.py` memilih runner per berkas**: yang mengimpor `pytest`
   dijalankan pytest, sisanya `unittest` discovery.
3. **pytest MENGUMPULKAN** fungsi `test_` tingkat modul.
   **unittest TIDAK.** Jadi fungsi tingkat modul hanya sah di berkas bergaya
   pytest.
4. `tests/test_suite_hygiene.py` menjaga ketiganya. Ia menolak test setelah blok
   main, menolak fungsi tingkat modul pada berkas non-pytest, dan menolak
   discovery yang menemukan < 100 test (tanda berkas gagal diimpor).
5. **Verifikasi JUMLAH test yang dikumpulkan, bukan hanya status `OK`:**
   ```bash
   PYTHONPATH=$PWD/tools python3 -c "
   import sys; sys.path.insert(0,'tools'); import _autodialog_guard
   import unittest
   print(unittest.TestLoader().discover('tests', pattern='test_*.py').countTestCases())"
   ```

*Pelajarannya umum dan berlaku selamanya: "lulus" bukan bukti bila test-nya tidak
dikumpulkan.*

## 2d. Audit Mendalam 17 Okt 2026 (area yang BELUM diaudit)

Audit workflow multi-agen pada permukaan yang belum tersentuh FASE 8 maupun audit
16 Okt: `page_tab`, alur data Result/Analyze, `song_library`, serialisasi
`models`, sisa mixer/preview, dan kebenaran analisis audio. Setiap temuan diuji
dua lensa (refutasi + reproduksi) dan dinyatakan kukuh hanya bila keduanya gagal
membantah.

**Sembilan defect aplikasi + satu defect runner diperbaiki** (suite 163 → **177 test unik**):

1. **`core/audio_loader.py`**: `except Exception: pass` menelan `PermissionError`,
   `IsADirectoryError`, dan kegagalan decode lain dari jalur `soundfile`, lalu
   menasihatkan *"please install soundfile"* padahal soundfile **ada** dan
   penyebabnya berkas/jalur. Kini hanya `OSError`/`RuntimeError`/`ValueError`
   (kontainer tak terbaca) yang jatuh ke parser native; `MemoryError` dilempar;
   pesan sejati disertakan. Commit `8bfc49f`.
2. **`core/song_library.py::remove()`**: seleksi melompat ke lagu lain saat
   menghapus lagu **di depan** indeks terpilih (terukur: pilih `lagu_B`, hapus
   `lagu_A` → tampil `lagu_C`). Kini `_selected` digeser sejumlah indeks yang
   dibuang di bawahnya.
3. **`core/song_library.py::move()`**: `_selected = target` membuat urut-ulang
   **mencuri seleksi** ke lagu yang digeser (terukur: pilih `c.wav`, geser `a.wav`
   +1 → tampil `a.wav`). Kini identitas `SongEntry` yang dilacak.
4. **`core/song_library.py::add_analysis()`**: menempel analisis ke entri yang
   sudah terpilih tidak menyiarkan seleksi (karena `select()` early-return pada
   indeks sama), sehingga tab lain tak me-refresh.
5. **`ui/panels/result_tab.py::_on_library_selection()`**: hanya memindah
   sorotan; `setCurrentRow` berjalan dengan sinyal diblokir sehingga metrik tak
   pernah dimuat ulang. Kini memuat hasil lagu terpilih.
6. **`ui/panels/analyze_tab.py`**: palet diambil dari `frames[len//2]` (satu
   frame tengah) padahal V/A yang dilaporkan adalah **rata-rata**; naskah Bab 4
   Tabel 4.6 menyejajarkan "Rata-rata V/A | RGBW algoritmik" per lagu. Kini palet
   diturunkan dari `ColorEngine.process_frame(avg_v, avg_a, avg_rms)`. Determinisme
   **terjaga** (dua run identik bit-for-bit), jadi uji pengulangan Tabel 4.4 aman.
7. **`ui/main_window.py::closeEvent()`**: memanggil `artnet_sender.blackout()`
   saja, jadi wire gelap tetapi `dmx_buffer` dan seluruh fader mixer tetap berisi
   look lama (terukur: `dmx_buffer[:3]=[200,150,100]`, fader[1]=200 bertahan).
   Bahaya: shutdown bisa dibatalkan (`event.ignore()`), lalu PLAY mengirim buffer
   basi sambil fader tampil menyala. Kini mencerminkan jalur BLACKOUT penuh.
8. **`ui/panels/page_tab.py`**: dua hal: (a) `load_cues`/`_clear_executors`
   menghancurkan tombol FLASH yang masih ditekan tanpa mengirim pelepasan, sehingga
   panggung **tetap menyala** setelah ganti halaman (terukur `wire[:3]` tetap
   `[255,255,255]`); kini melepas flash sebelum menghapus. (b) `.zlx` dengan
   `cues=[42]` membuat `load_cues` melempar `AttributeError` saat muat; kini
   `validate_payload` menolak item cue non-dict dan `load_cues` melewatinya.
9. **`ui/panels/result_tab.py::_on_song_row_selected()`**: tanpa `else`, memilih
   lagu **belum dianalisis** menyisakan metrik lagu sebelumnya dan Export tetap
   aktif. Kini `_show_no_analysis()` membersihkan kartu seperti keadaan awal.
10. **`tools/run_tests_guarded.py`**: fase unittest memakai
    `discover("tests", "test_*.py")` **tanpa** mengecualikan berkas gaya-pytest,
    sementara fase pytest juga menjalankannya. `test_suite_hygiene.py` memuat
    kelas `TestCase`, jadi test-nya berjalan **dua kali**. Akibat lanjut: angka
    "179 test" menghitung tiga test itu dua kali; angka unik sebenarnya **177**
    (diverifikasi `pytest tests/ --collect-only`). Kini ada
    `_is_pytest_module()` + `collect_unittest_modules()` yang dapat diuji, dan
    penjaga `test_guarded_runner_does_not_run_pytest_modules_twice`.

**Dua pembersihan minor:** sinyal mati `MixerTab.blackout_triggered` dihapus;
nama factory `create_alien_al36`/`create_kumastb_stl47` diselaraskan ke standar
§2 (`Alien-AL36`, `Kumastb-STL47` + id tanpa `_8ch`).

### ⚠️ JANGAN audit ulang (REFUTED lewat pengukuran)

- **Label drawer Visualizer (`FIXTURE POSITION` dll) TIDAK menggambar kotak
  gelap.** Dugaan dari jebakan QLabel/`background` global terbukti salah: sampel
  piksel sudut = `#242830` (= `BG_SURFACE`, benar), bukan `#1e2024` (= `BG_ROOT`).
  QFrame induk ber-style membuat Qt memperlakukan label dengan benar.
- **`_get_target_dmx_for_cue` memilih cabang berdasarkan PATCH PRESENCE**
  (`if patched_boxes:`), **bukan** `cue_info["type"]`. Klaim "cue tanpa `type`
  jatuh ke fallback 4x8ch" salah paham kode.
- **Flash yang ditekan saat jendela ditutup**: Qt memang mengirim sinyal
  `released`; diuji dengan event mouse nyata (`QTest.mousePress`), bukan emit
  sinyal langsung.

**Pelajaran diulang:** dari tujuh temuan kandidat `PAGE-*`, tiga gugur saat
diuji. Verifikasi adversarial menyelamatkan repo dari perbaikan atas bug yang
tidak ada. **Ukur dulu, jangan menebak** (§4).

## 3. Yang BELUM Dikerjakan

### UI: sisa dari feedback v4 §11-14 (`script/notes/feedback_v4.md`)

Dua butir dari feedback 16 Okt **belum** tuntas:
- **Drag dari panel fixture ke grid belum diuji dengan mouse sungguhan.**
  Payload, anti-tumpang-tindih, dan pelepasan kanal asal sudah teruji lewat
  pemanggilan langsung (`_on_fixture_dropped`) dan ada uji regresi, tetapi
  jalur drag Qt yang sebenarnya (`mimeData` → drop) hanya terbukti secara
  headless. **Uji dengan mouse di layar** sebelum dianggap tuntas; khususnya
  bahwa fixture **tidak hilang** saat drop ditolak.
- **`Alien-AL36` tanpa nomor** bila owner ingin nama benar-benar bersih. Sekarang
  dipakai `Alien-AL36 #1..#4` (keputusan owner 16 Okt). Bila berubah pikiran,
  perbaiki di tiga tempat: `ui/panels/address_tab.py` (quick-patch), dua
  `showfiles/`, dan `TestFixtureNameStandard`.

### Butuh hardware (FASE 6)
- Uji lapangan ESP32 + 4 unit PAR LED Alien AL36 di GIA Deliksari (DMX 1/17/33/49).
- Ukur laju DMX fisik. Firmware sudah diperbaiki ke penjadwalan absolut `esp_timer` (`DMX_PERIOD_US=23220`), tetapi **belum ada pengukuran nyata**: sebelumnya `vTaskDelay(22)` relatif menghasilkan ~22 fps, bukan 44.
- Ukur latensi end-to-end dan packet loss. Rencana: `script/markdowns/script_fase6_execution.md`.
- Build installer Windows 11 di Acer Swift 3 (PyInstaller + Inno Setup).
- **Firmware `artnet_dmx_final.ino` belum pernah dikompilasi.** Toolchain Arduino
  tidak ada di laptop ini. Patch penghitung paket (§2b) ditulis tanpa build
  pertama; lakukan build di laptop utama sebelum hari-H.

### Naskah skripsi (repo `script`)
- Bab 4 dan 5 masih kerangka: **81 penanda `[BELUM*]` di Bab 4**.
- **10 `[PERLU PERSETUJUAN DOSEN PEMBIMBING]`** (Keputusan 1-10) di
  `script/markdowns/script_konsultasi_pembimbing.md`. Dua di antaranya baru
  dan menyentuh metodologi: **Keputusan 9** (normalisasi relatif vs absolut) dan
  **Keputusan 10** (reliabilitas instrumen).
- 🔥 **Keputusan belum diambil:** 10 WAV di `data/audio/` **sintetis** (dibuat `tools/generate_benchmark_audio.py`, seragam 12,00 detik) tetapi dinamai band nyata. Bab 4 §4.1.2 mewajibkan lagu asli untuk penilaian persepsi.
  **Alat unduhnya sudah siap:** `python3 tools/fetch_test_audio.py --self-test --outdir data/audio`
  untuk memeriksa status bahan; `--manifest` untuk mengunduh lagu nyata dengan
  sidecar provenance. Belum dipakai karena daftar lagu belum ditetapkan owner.
- Olah data lapangan: `script/tools/analyze_field_data.py` (CSV 41 kolom → tabel
  Bab 4). **Perhatikan:** alat ini ada di repo **script**, bukan `zzluxora_v10`.
- Bridge korelasi fitur audio: `zzluxora-v10/tools/export_correlation.py`.

### Sisa temuan low (belum ditindak)
Tidak ada yang mendesak. Beberapa `except Exception: pass` yang sengaja (probe opsional, tutup socket) versus satu yang bermasalah (`audio_loader.py:109` menelan kegagalan decode lalu pindah format diam-diam).

---

## 4. Jebakan yang Harus Diketahui

### Qt: QLabel mewarisi background global
`CONSOLE_QSS` memuat `QWidget { background-color: ... }` yang **diwarisi setiap QLabel**. Setiap QLabel di atas widget berwarna WAJIB diberi `background: transparent`, kalau tidak ia menggambar persegi gelap yang menutupi warna induknya.

### Qt6: enum dipindah ke dalam kelas enum
`QListWidget.ExtendedSelection` **tidak ada** di Qt6; yang benar
`QListWidget.SelectionMode.ExtendedSelection`. Hal yang sama untuk
`QListWidget.DragDropMode.DragOnly`. Tetapi `Qt.UserRole` dan `Qt.AlignCenter`
**masih** ada di namespace `Qt`. **Selalu pakai `hasattr` dengan fallback**,
jangan asumsikan salah satu bentuk.

### Python: `__len__` membuat objek kosong bernilai falsy
`SongLibrary` mendefinisikan `__len__`, sehingga `bool(SongLibrary()) is False`
saat kosong. Akibatnya pola `song_library or SongLibrary()` **membuang** library
yang diberikan pemanggil dan membuat yang baru: pernah membuat tiga tab tidak
sinkron selama satu sesi penuh. **Untuk parameter default bertipe itu, selalu
pakai `x if x is not None else Default()`**, jangan `x or Default()`.

### Memblokir sinyal menghilangkan efek samping
Repaint list dengan `widget.blockSignals(True)` juga mematikan handler
`currentRowChanged`, sehingga tabel cue tetap kosong. Efek samping harus
dipanggil **eksplisit** setelah repaint. Lihat `PerformTab._refresh_playlist_view`.

### Preferensi desain owner
- **Tombol aksi WAJIB netral** abu-abu. Warna hanya untuk MAKNA, bukan hiasan.
  Doktrin `DESIGN.md` 10% Accent Rule: hijau = transmisi/simpan/aksi utama,
  merah = blackout/clear destruktif, amber = master dimmer, cyan = rail fader.
- **Elemen berwarna harus BLOK PENUH**, bukan outline. Ini sudah ditindak 16 Okt:
  outline amber di kolom Grand Master dan penanda seleksi bergaya garis tepi
  dihapus; tab aktif dan item terpilih kini memakai latar penuh.
- **Interaksi bermakna harus BLOK PENUH, bukan garis tepi.**
- UI konsol sengaja "jadul" demi stabilitas. Kata owner: *"software profesional
  harusnya clean ui nya, biasanya malah kayak ui jadul sih, soalnya kan ngejar
  stabilitas"*.
- **Tanpa judul/deskripsi per tab.** Nama tab sudah ada di tab bar; judul besar
  dan subjudul di bawahnya adalah pola halaman pemasaran, bukan konsol. Sudah
  dihapus dari keenam tab 16 Okt.

### Ukur dulu, jangan menebak
**Lima kali** kesimpulan dari kesan visual terbukti salah di sesi-sesi terakhir.
Contoh terbaru: keluhan "tab berwarna-warni": sampel piksel membuktikan teks tab
sudah netral (`#cbd5e1`); yang berwarna adalah aksen. Teknik yang bekerja:
`w.grab().save()` lalu hitung piksel, hitung kontras dari token, sampel area teks
dengan `PIL` + `Counter`, dan `tools/shoot_ui.py` untuk menangkap setiap tab.

### RAM hanya 3,6 GB, 2 CPU
Jangan jalankan hal berat bersamaan. Suite penuh 9-11 menit; `npm run deploy`
terbunuh bila available RAM < 1 GB.

---

## 5. Memori

### Lokasi catatan
- **Memori Claude** (dimuat otomatis): `~/.claude/projects/-home-zzdree-ANDREAS/memory/` (indeks di `MEMORY.md`). Tidak di git.
- **Memlog** (SQLite, **pengganti hindsight**): `~/ANDREAS/agent-memory/memlog.db`, **satu basis data untuk semua project**, dipisah kolom `bank`. Sumber kebenaran ada di `~/ANDREAS/agent-memory/notes/*.md` (di git); DB hanyalah cache yang bisa dihapus dan dibangun ulang.

**Sejak 18 Okt 2026 (memlog v2), auto-memory disalin ke memlog secara otomatis.** `hooks/memlog_sync_hook.py` berjalan di Stop dan PreCompact, mengimpor berkas yang berubah dari auto-memory, lalu mencerminkan DB ke `notes/`. Tidak perlu tindakan manual; `import_auto_memory.py` hanya untuk impor paksa seluruh folder.

```bash
# boleh dipanggil dari folder mana pun
python3 ~/ANDREAS/agent-memory/tools/memlog.py search "kata kunci"            # lintas semua project
python3 ~/ANDREAS/agent-memory/tools/memlog.py search "kata kunci" --bank zzluxora
python3 ~/ANDREAS/agent-memory/tools/memlog.py add --bank zzluxora --title "..." --tag ... --body "..."
python3 ~/ANDREAS/agent-memory/tools/memlog.py list --limit 20

# pemakaian terisolasi (uji): MEMLOG_DB=/tmp/coba.db python3 .../memlog.py list
```

### Kenapa bukan hindsight lagi
`hindsight-api` memuat dua model ML lokal sehingga memuncak **1.149 MB RAM** dan berulang kali di-OOM di laptop ini. Pengganti `memlog` memakai SQLite FTS5: **14 MB**, nol dependensi, mulai instan.

Tidak bisa diringankan: 9router punya 40 model tetapi **0 embedding**, dan reranker tidak punya opsi mati.

### Hindsight sudah DIHAPUS (17 Okt 2026)
`~/ANDREAS/hindsight/` (1,1 GB), `~/ANDREAS/.venv-hindsight/` (6,4 GB), dan dua
skrip yang hanya berguna selagi hindsight hidup (`hindsight_to_memlog.py`,
`create_backup.py`) sudah dihapus. Total sekitar **7,5 GB** dibebaskan.

Data tidak hilang, tersimpan tiga lapis: `~/ANDREAS/agent-memory/memlog.db` (143 entri
hidup), `~/ANDREAS/memory-backup/<bank>-bank.zip` (arsip transfer resmi
hindsight, 3 bank, ~268 item), dan
`~/ANDREAS/memory-backup/memlog-before-shared-20261017.db`. Jangan menulis
prosedur "perbarui arsip hindsight" lagi: tidak ada instance untuk diperbarui.

### Pelajaran dari sesi lalu
Skrip probe pernah memunculkan popup `QMessageBox` berulang di layar owner yang sedang bekerja, padahal ia tidak menjalankan aplikasi. Itu mengganggu dan membingungkan. **Selalu pakai wrapper berpengaman**; kalau menulis skrip probe sendiri, impor `_autodialog_guard` sebagai baris pertama dengan `PYTHONPATH=<repo>/tools`.

---

## 6. Berkas Penting

| Berkas | Isi |
|---|---|
| `CLAUDE.md` | aturan proyek, design system, status uji |
| `DESIGN.md` + `PRODUCT.md` | doktrin desain (Impeccable, "The Obsidian Control Deck") |
| `markdowns/ROADMAP.md` | FASE 1-8, rincian 18 defect audit |
| `markdowns/TEST_PLAN.md` | matriks uji, Level 1-5, suite UT-01..UT-12 |
| `markdowns/MEMORY.md` | cara pakai memlog, arsip, pemulihan |
| `tools/run_tests_guarded.py` | perintah uji resmi |
| `tools/_autodialog_guard.py` | penetral dialog |
| `tools/shoot_ui.py` | tangkap layar tiap tab tanpa perlu layar sungguhan |
| `tools/fetch_test_audio.py` | unduh bahan uji audio nyata + catatan provenance |
| `core/song_library.py` | satu daftar lagu bersama Analyze/Result/Perform |
| `tests/test_suite_hygiene.py` | penjaga agar test tidak lolos tanpa dijalankan |
| `scripts/check-anti-slop.js` | pemindai mutu |
| `~/ANDREAS/agent-memory/tools/memlog.py` | memori agen (di luar repo, lintas project) |
| `../script/notes/feedback_v4.md` | **lembar acuan tunggal.** Bagian 1-10 (6 Okt) + bagian 11-14 (17 Okt) |
| `../script/markdowns/script_plans.md` | status naskah skripsi |
| `../script/markdowns/script_konsultasi_pembimbing.md` | agenda konsultasi dospem |

---

## 7. Langkah Pertama yang Disarankan

1. Baca **§0** dokumen ini (30 detik), lalu `markdowns/ROADMAP.md` FASE 8,
   **§2b**, **§2c**, dan `../script/notes/feedback_v4.md` bagian 11-14.
2. Verifikasi keadaan. **Periksa jumlah test, bukan hanya status `OK`:**
   ```bash
   PYTHONPATH=$PWD/tools python3 tools/run_tests_guarded.py
   QT_QPA_PLATFORM=offscreen PYTHONPATH=$PWD/tools python3 -m pytest tests/ --collect-only -q | tail -1
   # 177 tests collected; periksa angkanya, jangan hanya status OK
   ```
3. **Lihat UI-nya sebelum mengubahnya:**
   ```bash
   QT_QPA_PLATFORM=offscreen PYTHONPATH=$PWD/tools python3 tools/shoot_ui.py --outdir /tmp/zz_shots
   ```
   lalu baca PNG di `/tmp/zz_shots/`.
4. Cari konteks relevan: `python3 ~/ANDREAS/agent-memory/tools/memlog.py search "<topik>"`.
5. **Tanya owner mau lanjut ke mana.** Pilihan yang tersedia:
   **(a)** uji drag fixture dengan mouse sungguhan (sisa v5, §3),
   **(b)** kerjakan naskah Bab 4/5 dan keputusan audio,
   **(c)** siapkan FASE 6 saat hardware tersedia,
   **(d)** test manual aplikasi lalu perbaiki temuan yang muncul.

**Jangan** mengaudit ulang area yang sudah tuntas: FASE 8 (18 defect) dan audit
adversarial 16 Okt (7 defect) sudah direproduksi dan dikunci uji regresi.
**Jangan** mempercayai klaim di naskah atau memori tanpa memeriksa kodenya: 
beberapa sudah terbukti keliru dan tercatat di §4.
