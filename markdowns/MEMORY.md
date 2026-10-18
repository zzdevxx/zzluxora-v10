# Memori Agen: memlog (SQLite) menggantikan hindsight-api

## Ringkasan keputusan

`hindsight-api` memuat **dua model ML lokal** (embedding `bge-small-en-v1.5` dan reranker `ms-marco-MiniLM-L-6`) sehingga memuncak di **1.149 MB RAM**. Di laptop ini (3,6 GB total) API tidak dapat berjalan bersamaan dengan sesi kerja lain, dan berulang kali dihentikan sistem karena kehabisan memori. Sebagai gantinya dipakai **memlog**, pencarian berbasis **SQLite FTS5** dari pustaka standar Python.

| | hindsight-api | memlog |
|---|---|---|
| Puncak RAM | 1.149 MB | **14 MB** |
| Proses latar | Ya (server + PostgreSQL) | Tidak (dipanggil saat perlu) |
| Dependensi | model ML, pgvector, PostgreSQL | **nol** (sqlite3 dari stdlib) |
| Waktu mulai | 60 detik | instan |
| Pencarian | semantik (embedding) | leksikal (FTS5 + BM25) |

Konsekuensi yang diterima: pencarian leksikal lemah pada parafrase jauh. Untuk catatan yang ditulis dengan istilah serupa, hasilnya setara. Ini dianggap memadai karena catatan proyek cenderung memakai istilah teknis yang konsisten.

## Perintah harian

Satu basis data dipakai **semua project** di mesin ini (`zzluxora_v10`, `script`,
`gia-deliksari-web`, dan seterusnya), dipisah oleh kolom `bank`. Skripnya boleh
dipanggil dari folder mana pun dengan path absolut.

```bash
# simpan catatan
python3 ~/ANDREAS/agent-memory/tools/memlog.py add --bank zzluxora --title "Judul singkat" \
    --tag desain --body "Isi catatan yang ingin diingat."

# cari lintas SEMUA project (tanpa --bank)
python3 ~/ANDREAS/agent-memory/tools/memlog.py search "jebakan"
# batasi ke satu project
python3 ~/ANDREAS/agent-memory/tools/memlog.py search '"blok penuh"' --bank zzluxora

# lihat, daftar, sunting, hapus
python3 ~/ANDREAS/agent-memory/tools/memlog.py show 12
python3 ~/ANDREAS/agent-memory/tools/memlog.py list --bank zzluxora --limit 20
python3 ~/ANDREAS/agent-memory/tools/memlog.py edit 12 --body "Isi baru"
python3 ~/ANDREAS/agent-memory/tools/memlog.py delete 12

# pindahkan isi basis data
python3 ~/ANDREAS/agent-memory/tools/memlog.py export /tmp/memlog.json
python3 ~/ANDREAS/agent-memory/tools/memlog.py import /tmp/memlog.json
```

**Basis data:** `~/ANDREAS/agent-memory/memlog.db` (lokasi bersama). Dulu file ini
berada di `zzluxora_v10/memory/memlog.db`, sehingga log tidak terpakai dari
folder project lain dan satu pemanggil sempat membuat `memlog.db` kosong di
tempat lain.

**Skripnya di luar repo:** `~/ANDREAS/agent-memory/tools/memlog.py`, satu berkas, nol
dependensi. Dipisahkan dari repo supaya alat memori tidak ikut hilang atau
tersalin saat repo berpindah laptop. `check-anti-slop.js` dan
`contrast-check.py` tetap di repo karena khas per-repo.

Untuk pemakaian terisolasi (uji, percobaan), set `MEMLOG_DB`:

```bash
MEMLOG_DB=/tmp/percobaan.db python3 ~/ANDREAS/agent-memory/tools/memlog.py list
```


## Hindsight sudah DIHAPUS (17 Okt 2026)

`hindsight-api`, direktori `~/ANDREAS/hindsight/` (1,1 GB), dan venv
`~/ANDREAS/.venv-hindsight/` (6,4 GB) sudah dihapus, bersama skrip
`hindsight_to_memlog.py` dan `create_backup.py` yang hanya berguna selagi
hindsight hidup. Ruang yang dibebaskan sekitar **7,5 GB**.

Data tidak hilang. Tersimpan di tiga tempat:

| Lokasi | Isi |
|---|---|
| `~/ANDREAS/agent-memory/memlog.db` | 143 entri hidup, 4 bank, pencarian penuh |
| `~/ANDREAS/memory-backup/<bank>-bank.zip` | arsip transfer asli hindsight, 3 bank, ~268 item |
| `~/ANDREAS/memory-backup/memlog-before-shared-20261017.db` | cadangan DB sebelum migrasi ke lokasi bersama |

Arsip `<bank>-bank.zip` memakai format transfer resmi hindsight, jadi bila
nantinya ingin menghidupkan hindsight lagi, arsipnya masih dapat diimpor ke
instance baru. Namun pemulihan itu perlu memasang ulang hindsight; tidak ada
prosedur siap pakai di repo ini karena tidak direncanakan.

## Keterbatasan yang diketahui

- **Pencarian leksikal, bukan semantik.** Query yang memakai kata yang sama sekali berbeda dari catatan tidak akan cocok. Tambahkan tag saat menyimpan untuk memperlebar jalan masuk.
- **Tidak ada ekstraksi fakta otomatis.** Hindsight memecah catatan panjang menjadi fakta lewat LLM; memlog menyimpan apa adanya. Fakta hasil ekstraksi hindsight yang sudah ada tetap ikut terimpor dari arsip.
- **Tidak ada konsolidasi.** Tidak ada proses latar yang menggabungkan catatan serupa. Deduplikasi hanya saat impor, berdasarkan isi fakta.

## Berkas

| Berkas | Fungsi |
|---|---|
| `~/ANDREAS/agent-memory/tools/memlog.py` | alat memori: tambah, cari, lihat, sunting, hapus, ekspor, impor |
| `~/ANDREAS/agent-memory/memlog.db` | basis data catatan |
| `../memory-backup/*.zip` | arsip asli hindsight |
