# 🚛 MFVRPTW - Multi-Fleet Vehicle Routing Problem with Time Windows

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://harunsatr-rvnd.streamlit.app)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/GitHub-Harunsatr%2FRVND-blue?logo=github)](https://github.com/Harunsatr/RVND)

Sistem optimasi rute untuk distribusi obat dari gudang ke berbagai pelanggan (rumah sakit, klinik, puskesmas) menggunakan berbagai jenis kendaraan dengan batasan kapasitas dan time windows.

## 🌐 Live Demo

> **Note**: Setelah deploy ke Streamlit Cloud, URL aplikasi akan tersedia di sini.
> 
> Contoh URL: `https://harunsatr-rvnd.streamlit.app`

---

## 📋 Deskripsi Program

Program ini menyelesaikan masalah **Multi-Fleet Vehicle Routing Problem with Time Windows (MFVRPTW)** - sebuah masalah optimasi yang kompleks untuk menemukan rute distribusi paling efisien dengan:

| Feature | Description |
|---------|-------------|
| 🚗 **Multi-Fleet** | Menggunakan berbagai jenis kendaraan (Motor, Mobil Kecil, Mobil Besar) dengan kapasitas dan biaya berbeda |
| ⏰ **Time Windows** | Setiap pelanggan memiliki waktu layanan yang harus dipenuhi |
| 📦 **Kapasitas** | Setiap kendaraan memiliki batasan kapasitas maksimal |
| 💰 **Optimasi Biaya** | Meminimalkan biaya tetap (fixed cost) dan biaya variabel (per km) |

---

## 🎯 Pipeline Optimasi

Program ini menggunakan algoritma multi-tahap untuk menghasilkan solusi optimal:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Distance    │     │  2. Sweep       │     │  3. Nearest     │
│     Matrix      │ ──► │     Clustering  │ ──► │     Neighbor    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  6. Final       │     │  5. RVND        │     │  4. ACS         │
│     Solution    │ ◄── │     Optimizer   │ ◄── │     Optimizer   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Algoritma Detail:

1. **Perhitungan Matriks Jarak & Waktu** (`distance_time.py`)
   - Menghitung jarak Euclidean dari koordinat
   - Waktu tempuh: 1 km = 1 menit

2. **Sweep Algorithm** (`sweep_nn.py`)
   - Mengurutkan pelanggan berdasarkan sudut polar
   - Membentuk cluster berdasarkan kapasitas kendaraan
   - 1 cluster = 1 kendaraan

3. **Nearest Neighbor (NN)** (`sweep_nn.py`)
   - Inisialisasi rute awal untuk setiap cluster
   - **Time Window Aware**: Menolak pelanggan jika arrival > TW_end (hard constraint)

4. **Ant Colony System (ACS)** (`acs_solver.py`)
   - Optimasi rute per cluster
   - Parameter: m=2, α=0.5, β=2, ρ=0.2, q₀=0.85, iterasi=2

5. **RVND (Randomized Variable Neighborhood Descent)** (`rvnd.py`) - **v2.0**
   - **Two-level local search** dengan strict neighborhood management
   - **Intra-route**: 2-opt, Or-opt, Reinsertion, Exchange
   - **Inter-route**: shift(1,0), shift(2,0), swap(1,1), swap(2,1), swap(2,2), cross
   - **Hard constraint** pada kapasitas, soft constraint pada time windows

6. **Final Integration** (`final_integration.py`)
   - Menggabungkan semua hasil
   - Validasi solusi
   - Menghasilkan laporan final

---

## 🎓 Academic Replay Mode (NEW!)

Fitur khusus untuk **validasi akademis** dengan langkah-langkah deterministik:

| Feature | Description |
|---------|-------------|
| 📝 **NN_TW_AWARE** | Nearest Neighbor dengan hard constraint time window |
| 🐜 **ACS_REPLAY** | Rute predefined sesuai dokumen Word |
| 🔄 **RVND_REPLAY** | Swap pairs predefined dengan capacity hard constraint |
| ⏰ **Time Window Analysis** | Analisis detail kepatuhan time window per pelanggan |

---

## 📊 Dashboard Interaktif

Program dilengkapi dengan GUI berbasis **Streamlit** yang menampilkan:

| Tab | Fitur |
|-----|-------|
| 📍 **Input Titik** | Input koordinat depot dan pelanggan |
| 📋 **Input Data** | Input data pelanggan (demand, time windows, service time) |
| 📈 **Hasil** | Tabel detail rute per kendaraan |
| 🗺️ **Graph Hasil** | Visualisasi rute dengan Plotly |
| 🎓 **Academic Replay** | Mode replay untuk validasi akademis |

---

## 🚀 Quick Start

### Opsi 1: Akses Online (Recommended)
Langsung akses aplikasi di **[Streamlit Cloud](https://mfvrptw-optimizer.streamlit.app)** - tidak perlu instalasi!

### Opsi 2: Instalasi Lokal

```bash
# 1. Clone repository
git clone https://github.com/Harunsatr/Route-Optimization.git
cd Route-Optimization/Program

# 2. Buat virtual environment (opsional tapi direkomendasikan)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Jalankan aplikasi
streamlit run gui/app.py
```

Dashboard akan terbuka di browser pada `http://localhost:8501`

---

## 📁 Struktur Folder

```
Program/
├── 📄 academic_replay.py       # Academic Replay Module (NEW!)
├── 📄 acs_solver.py            # Ant Colony System
├── 📄 distance_time.py         # Matriks jarak & waktu
├── 📄 final_integration.py     # Integrasi dan validasi
├── 📄 rvnd.py                  # RVND Optimization v2.0
├── 📄 sweep_nn.py              # Sweep + Nearest Neighbor
├── 📄 requirements.txt         # Dependencies
├── 📄 README.md                # File ini
│
├── 📁 data/processed/          # Data hasil optimasi
│   ├── parsed_instance.json        # Data instance
│   ├── parsed_distance.json        # Matriks jarak
│   ├── clusters.json               # Hasil clustering
│   ├── initial_routes.json         # Rute awal (NN)
│   ├── acs_routes.json             # Rute setelah ACS
│   ├── rvnd_routes.json            # Rute setelah RVND
│   ├── final_solution.json         # Solusi akhir
│   └── academic_replay_results.json # Hasil Academic Replay
│
├── 📁 docs/                    # Dokumentasi
│   ├── dokumentasi_id.md           # Dokumentasi lengkap
│   ├── rvnd_specification.md       # Spesifikasi RVND
│   └── final_summary.md            # Ringkasan hasil
│
└── 📁 gui/                     # Aplikasi Streamlit
    ├── app.py                      # File utama
    ├── agents.py                   # Background agents
    └── tabs/                       # Tab-tab dashboard
        ├── input_titik.py
        ├── input_data.py
        ├── hasil.py
        ├── graph_hasil.py
        └── academic_replay.py      # Academic Replay UI
```

---

## ☁️ Deployment ke Streamlit Cloud

### Prasyarat
- Akun GitHub dengan repository ini
- Akun Streamlit Cloud (gratis di [share.streamlit.io](https://share.streamlit.io))

### Langkah-langkah Deploy:

#### Step 1: Pastikan Repository Sudah di GitHub
```bash
# Cek remote repository
git remote -v
# Output: origin  https://github.com/Harunsatr/RVND.git

# Push perubahan terbaru
git add -A
git commit -m "Update for Streamlit deployment"
git push origin main
```

#### Step 2: Buka Streamlit Cloud
1. Kunjungi **[share.streamlit.io](https://share.streamlit.io)**
2. Klik **"Sign in with GitHub"**
3. Authorize Streamlit untuk mengakses repository Anda

#### Step 3: Deploy Aplikasi Baru
1. Klik tombol **"New app"** (pojok kanan atas)
2. Isi form dengan:
   | Field | Value |
   |-------|-------|
   | **Repository** | `Harunsatr/RVND` |
   | **Branch** | `main` |
   | **Main file path** | `gui/app.py` |

3. Klik **"Deploy!"**

#### Step 4: Tunggu Proses Build
- Streamlit akan menginstall dependencies dari `requirements.txt`
- Proses biasanya memakan waktu 2-5 menit
- Setelah selesai, aplikasi akan live di URL seperti:
  ```
  https://[nama-app].streamlit.app
  ```

### ⚙️ File yang Diperlukan untuk Deploy
| File | Status | Keterangan |
|------|--------|------------|
| `requirements.txt` | ✅ Ada | Dependencies Python |
| `gui/app.py` | ✅ Ada | Entry point aplikasi |
| `.streamlit/config.toml` | ✅ Ada | Konfigurasi tema |
| `.gitignore` | ✅ Ada | Exclude files |

### 🔧 Troubleshooting

**Error: ModuleNotFoundError**
- Pastikan semua package ada di `requirements.txt`
- Jalankan `pip freeze > requirements.txt` untuk update

**Error: File not found**
- Pastikan path `gui/app.py` benar (relatif dari root repository)

**Aplikasi lambat saat pertama kali load**
- Normal untuk free tier Streamlit Cloud
- Aplikasi "tidur" setelah tidak aktif beberapa waktu

---

## 🔧 Konfigurasi

### Parameter Algoritma

**ACS Parameters** (`acs_solver.py`):
```python
m = 2          # Jumlah semut
alpha = 0.5    # Pengaruh pheromone (updated)
beta = 2       # Pengaruh heuristic (jarak)
rho = 0.2      # Evaporation rate
q0 = 0.85      # Exploitation vs exploration
iterations = 2 # Jumlah iterasi
```

**RVND Parameters** (`rvnd.py`):
```python
MAX_INTER_ITERATIONS = 50   # Maksimal iterasi inter-route
MAX_INTRA_ITERATIONS = 100  # Maksimal iterasi intra-route
SEED = 84                   # Random seed untuk deterministic behavior
```

### Vehicle Types

| Type | Capacity | Fixed Cost | Variable Cost/km |
|------|----------|------------|------------------|
| A (Motor) | ≤ 60 | Rp 40,000 | Rp 1,000 |
| B (Mobil Kecil) | 60-100 | Rp 60,000 | Rp 1,500 |
| C (Mobil Besar) | 100-150 | Rp 80,000 | Rp 2,000 |

---

## 📊 Contoh Hasil Optimasi

```
📦 Total Clusters: 4
🚗 Total Vehicles: 4

Cluster 1: [C2, C4] - Demand: 40 - Vehicle: Type A
Cluster 2: [C3, C6, C9] - Demand: 66 - Vehicle: Type B
Cluster 3: [C1, C10] - Demand: 45 - Vehicle: Type A
Cluster 4: [C5, C7, C8] - Demand: 64 - Vehicle: Type B

💰 Total Cost: Rp 293,900
⏰ Total Wait Time: 263.3 min
✅ Time Window Violations: 0
```

---

## 🧪 Testing & Validasi

Program melakukan validasi otomatis:
- ✅ Semua pelanggan terlayani
- ✅ Kapasitas kendaraan tidak melebihi batas
- ✅ Time windows dipenuhi
- ✅ Setiap rute dimulai dan berakhir di depot
- ✅ Matriks jarak simetris
- ✅ Deterministic behavior (hasil sama dengan seed sama)

---

## 📖 Dokumentasi Lengkap

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Panduan utama (file ini) |
| [docs/dokumentasi_id.md](docs/dokumentasi_id.md) | Dokumentasi teknis lengkap |
| [docs/rvnd_specification.md](docs/rvnd_specification.md) | Spesifikasi algoritma RVND |
| [docs/final_summary.md](docs/final_summary.md) | Ringkasan hasil optimasi |

---

## 🤝 Kontribusi

1. Fork repository ini
2. Buat branch baru (`git checkout -b feature/AmazingFeature`)
3. Commit perubahan (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

---

## 📚 Referensi

- Dorigo, M., & Gambardella, L. M. (1997). *Ant colony system: a cooperative learning approach to the traveling salesman problem.*
- Hansen, P., & Mladenović, N. (2001). *Variable neighborhood search: Principles and applications.*
- Gillett, B. E., & Miller, L. R. (1974). *A heuristic algorithm for the vehicle-dispatch problem.*

---

## 👨‍💻 Author

**Harunsatr** - [GitHub](https://github.com/Harunsatr)

---

## 📝 Lisensi

Project ini dilisensikan di bawah [MIT License](LICENSE).

---

## ❓ FAQ

<details>
<summary><b>Program tidak bisa dijalankan, muncul error module not found?</b></summary>
Pastikan semua dependencies sudah terinstall dengan `pip install -r requirements.txt`
</details>

<details>
<summary><b>Dashboard tidak menampilkan data?</b></summary>
Pastikan file-file JSON di folder `data/processed/` ada dan tidak corrupt. Jika perlu, jalankan ulang pipeline optimasi.
</details>

<details>
<summary><b>Bagaimana cara mengubah data pelanggan?</b></summary>
Edit file `data/processed/parsed_instance.json` kemudian jalankan ulang pipeline optimasi.
</details>

<details>
<summary><b>Apakah bisa di-deploy ke Netlify?</b></summary>
Tidak, Netlify hanya untuk static sites. Streamlit membutuhkan Python backend server. Gunakan <b>Streamlit Cloud</b> (gratis) untuk deployment.
</details>

---

## 📞 Support

Jika ada pertanyaan atau masalah, silakan buat issue di [GitHub Issues](https://github.com/Harunsatr/Route-Optimization/issues)

---

⭐ **Jika project ini membantu, jangan lupa berikan star di GitHub!**
