# Memori Agen: memlog (SQLite) menggantikan hindsight-api

> **Diperbarui 18 Okt 2026 (memlog v2).** Bagian "Hindsight sudah dihapus" dan
> "Keterbatasan" di bawah menggambarkan keadaan sebelum pembaruan; lihat
> §"Memlog v2" untuk yang berlaku sekarang.

## Ringkasan keputusan

`hindsight-api` memuat **dua model ML lokal** (embedding `bge-small-en-v1.5` dan reranker `ms-marco-MiniLM-L-6`) sehingga memuncak di **1.149 MB RAM**. Di laptop ini (3,6 GB total) API tidak dapat berjalan bersamaan dengan sesi kerja lain, dan berulang kali dihentikan sistem karena kehabisan memori. Sebagai gantinya dipakai **memlog**, pencarian berbasis **SQLite FTS5** dari pustaka standar Python.

| | hindsight-api | memlog |
|---|---|---|
| Puncak RAM | 1.149 MB | **16 MB** |
| Proses latar | Ya (server + PostgreSQL) | Tidak (dipanggil saat perlu) |
| Dependensi | model ML, pgvector, PostgreSQL | **nol** (sqlite3 dari stdlib) |
| Waktu mulai | 60 detik | instan |
| Pencarian | semantik (embedding) | leksikal (FTS5 + BM25) |
| Cakupan lintas proyek | **tidak bisa** (bank terisolasi) | **ya** (kolom `bank`, satu query) |
| Sinkron dua mesin | volume Postgres, bukan git | **markdown di git** |

Dua baris terakhir yang menentukan, bukan RAM-nya saja. Hindsight memisahkan bank
secara ketat ("no cross-bank leakage") sehingga sembilan proyek tidak bisa dicari
dalam satu query, dan datanya hidup di volume Postgres sehingga tidak bisa
disinkronkan lewat git antar dua laptop.

Konsekuensi yang diterima: pencarian leksikal lemah pada parafrase jauh. Untuk catatan yang ditulis dengan istilah serupa, hasilnya setara. Ini dianggap memadai karena catatan proyek cenderung memakai istilah teknis yang konsisten.

## Memlog v2 (18 Okt 2026)

Tiga hal berubah setelah riset 24 proyek memory agent (Engram, Tigerless,
CC Agent Brain, Anamnesis, OKF, Claude-Mem, MemPalace, dan lainnya). Kesimpulan
riset: **perbaiki arsitektur yang ada, jangan ganti** — markdown sebagai sumber
kebenaran + SQLite FTS5 sebagai cache adalah pola yang justru dikonvergensikan
kandidat terbaik.

### 1. Auto-capture

`hooks/memlog_sync_hook.py` dipasang di **Stop** dan **PreCompact**. Ia memindai
`~/.claude/projects/*/memory/*.md` dan mengimpor berkas yang berubah ke memlog,
lalu mencerminkan DB ke `notes/`.

Prinsipnya: **amati artefaknya, jangan andalkan niat prompt.** Claude menulis ke
auto-memory entah kita memintanya atau tidak. Meminta model "panggil tool memlog"
terbukti kalah oleh system prompt auto-memory (MemPalace issue #622).

`PreCompact` wajib ada karena `Stop` tidak dijamin menyala saat terminal ditutup.

### 2. Identitas stabil

Kolom `source_key` (`auto-memory:<slug>:<stem>`) menggantikan id AUTOINCREMENT
sebagai identitas lintas mesin. Tanpa ini, dua laptop yang mengimpor berkas sama
sama-sama mendapat `id=185`, git menyimpan dua berkas, dan `reindex` mati dengan
`UNIQUE constraint failed: notes.id`.

### 3. Anti-duplikasi tiga lapis

| Lapis | Mekanisme | Efek |
|---|---|---|
| 1 | state `mtime` + `size` | mayoritas run tidak membaca berkas sama sekali |
| 2 | `UNIQUE INDEX` parsial pada `source_key` | satu berkas tidak pernah jadi dua baris |
| 3 | `content_hash` | impor identik tidak menggeser `updated_at` |

### 4. Kolom baru

`source_key`, `content_hash`, `revision_count`, `review_after`, `last_seen_at`.

`review_after` diisi saat impor menurut jenis catatan (config/preference 90 hari,
discovery/decision 180, architecture/bugfix 365) dan ditampilkan oleh
`list --needs-review`. Nilainya ikut ditulis ke frontmatter markdown supaya
bertahan melewati `reindex`.

### 5. Perintah baru

```bash
# tandai catatan lama digantikan, dalam satu langkah
memlog.py add --bank X --title "..." --body "..." --supersedes 133

# catatan yang sudah lewat masa tinjau
memlog.py list --needs-review
```

`search` sekarang juga **melaporkan istilah yang tidak ada di korpus** beserta
saran kata mirip. Ini hanya peringatan, bukan filter: menyaring query ke istilah
yang dikenal terbukti menjatuhkan MRR dari 0,41 ke 0,33.

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

- **Pencarian leksikal, bukan semantik.** Query yang memakai kata yang sama sekali berbeda dari catatan tidak akan cocok. Tambahkan tag saat menyimpan untuk memperlebar jalan masuk. Sejak v2, `search` setidaknya memberi tahu istilah mana yang tidak ada di korpus, alih-alih diam.
- **Tidak ada ekstraksi fakta otomatis dengan LLM.** Catatan disimpan apa adanya. Ini keputusan sadar: ekstraksi LLM per sesi berbiaya token dan menurut literatur justru menjadi titik masuk kesalahan memori. Yang otomatis hanyalah impor berkas dari auto-memory, bukan penulisan ulang isinya.
- **Tidak ada konsolidasi otomatis.** Tidak ada proses latar yang menggabungkan catatan serupa. Deduplikasi terjadi saat impor (berdasarkan `source_key` dan `content_hash`), bukan secara semantik. Penggabungan manual lewat `--supersedes`.
- **Tidak ada embedding.** Diukur pada korpus ini: cosine hit@5 = 0,60, BM25 hit@5 = 0,60. Model vektor berarti ratusan MB RAM untuk hasil yang sama.
- **Batas skala belum diuji.** 187 catatan masih jauh dari titik di mana FTS5 perlu disesuaikan.

## Berkas

| Berkas | Fungsi |
|---|---|
| `~/ANDREAS/agent-memory/tools/memlog.py` | alat memori: tambah, cari, lihat, sunting, hapus, ekspor, impor |
| `~/ANDREAS/agent-memory/tools/memory_mirror.py` | cerminkan DB ke markdown, reindex, supersede |
| `~/ANDREAS/agent-memory/tools/import_auto_memory.py` | impor manual seluruh auto-memory (hook melakukan ini otomatis) |
| `~/ANDREAS/agent-memory/hooks/memlog_sync_hook.py` | impor inkremental auto-memory, dipanggil Stop + PreCompact |
| `~/ANDREAS/agent-memory/hooks/memlog_start_hook.py` | cetak jumlah + 5 judul terbaru saat sesi mulai |
| `~/ANDREAS/agent-memory/hooks/memlog_stop_hook.py` | cerminkan DB ke markdown di akhir sesi |
| `~/ANDREAS/agent-memory/hooks/memlog_pull_hook.py` | tarik catatan dari mesin lain, hanya bila tree bersih |
| `~/ANDREAS/agent-memory/notes/*.md` | sumber kebenaran, di git |
| `~/ANDREAS/agent-memory/memlog.db` | cache pencarian, tidak di git, bisa dihapus |
| `~/ANDREAS/agent-memory/backup/` | arsip sebelum migrasi (DB lama, zip hindsight) |
| `~/ANDREAS/agent-memory/research/` | benchmark dan laporan yang melahirkan arsitektur ini |

Status 18 Okt 2026: 188 catatan, 15 test lulus, 0 dependensi, ~16 MB RAM.
Repo privat: GitLab (`origin`) dan Codeberg (`codeberg`).
