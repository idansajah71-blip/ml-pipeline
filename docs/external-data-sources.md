# External Data Sources — Referensi & Riset

> Dokumen ini jadi acuan untuk fitur "Cari & Ambil Data" (External Data Search & Import).
> Diperbarui: 8 Agustus 2026

---

## Prioritas Sumber

| Prioritas | Sumber | Alasan |
|-----------|--------|--------|
| 1 (Wajib) | BPS Web API | Data resmi Indonesia, API jelas, gratis, relevan UMKM/edukasi |
| 2 | World Bank Open Data | 16,000+ indikator global, CC-BY lisensi terbuka, no API key |
| 3 | data.go.id | 600,000+ dataset pemerintah Indonesia, portal Satu Data |
| 4 | Wikidata/Wikipedia | Data umum terstruktur, unlimited, CC-BY-SA |
| 5 | Open Data Kota/Provinsi | Data lokal spesifik (Jakarta, Kaltim, dll) |

---

## 1. BPS Web API (Badan Pusat Statistik)

### Informasi Umum
| Field | Nilai |
|-------|-------|
| Portal | https://webapi.bps.go.id |
| Dokumentasi | https://webapi.bps.go.id/documentation |
| Operator | Badan Pusat Statistik (BPS — Statistics Indonesia) |
| Tipe data | 1,000+ dataset statistik: ekonomi, demografi, harga, perdagangan |
| Format response | JSON |
| API key | **Wajib** — gratis, daftar di https://webapi.bps.go.id/developer/register |
| Rate limit | ~2 req/s (safe) |
| Lisensi | Data publik pemerintah Indonesia, boleh dipakai bebas dengan atribusi |

### Endpoint Utama

**Base URL:** `https://webapi.bps.go.id/v1/api`

| Endpoint | Method | Parameter Utama | Deskripsi |
|----------|--------|-----------------|-----------|
| `/list?model=subject` | GET | `domain`, `key` | Daftar topik/subjek data |
| `/list?model=subcat` | GET | `domain`, `key` | Daftar kategori subjek |
| `/list?model=var` | GET | `domain`, `subject`, `key` | Daftar variabel per subjek |
| `/list?model=data` | GET | `domain`, `var`, `th`, `key` | Data dinamis (time series) |
| `/list?model=unit` | GET | `domain`, `key` | Daftar satuan unit |
| `/list?model=th` | GET | `domain`, `var`, `key` | Daftar periode waktu |
| `/domain` | GET | `type`, `key` | Daftar domain wilayah (provinsi/kabupaten) |

### Contoh Request
```
# Cari subjek data di domain nasional (0000)
GET https://webapi.bps.go.id/v1/api/list?model=subject&domain=0000&key=YOUR_API_KEY

# Ambil data harga beras per provinsi
GET https://webapi.bps.go.id/v1/api/list?model=data&domain=0000&var=1215&th=2024&key=YOUR_API_KEY

# Cari wilayah (daftar provinsi)
GET https://webapi.bps.go.id/v1/api/domain?type=prov&key=YOUR_API_KEY
```

### Format Response (contoh)
```json
{
  "status": 200,
  "message": "Ok",
  "data": [
    {
      "id": 1215,
      "subject": 80,
      "unit": "Rp/Kg",
      "title": "Harga Rata-Rata Beras",
      "data": [
        {"label": "2024", "value": "13500"},
        {"label": "2023", "value": "12800"}
      ]
    }
  ]
}
```

### Catatan Penting
- Domain `"0000"` = nasional, kode provinsi 2 digit (contoh `"31"` = DKI Jakarta)
- Beberapa indikator punya nilai kosong (`"-"` atau `""`) — perlu dinormalisasi ke `null`
- Pencarian keyword hanya bahasa Indonesia
- Response pakai mixed camelCase & snake_case — perlu normalisasi

---

## 2. World Bank Open Data API

### Informasi Umum
| Field | Nilai |
|-------|-------|
| Portal | https://data.worldbank.org |
| API Docs | https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation |
| Operator | The World Bank Group |
| Tipe data | 16,000+ indikator time-series dari 200+ negara |
| Format response | JSON, XML, JSON-stat |
| API key | **Tidak perlu** — terbuka untuk semua |
| Rate limit | Tidak diumumkan secara resmi, tapi toleran untuk penggunaan normal |
| Lisensi | **CC-BY 4.0** — boleh dipakai komersial dengan atribusi |

### Endpoint Utama

**Base URL:** `https://api.worldbank.org/v2`

| Endpoint | Deskripsi |
|----------|-----------|
| `/country/{code}/indicator/{indicator}` | Data indikator untuk negara tertentu |
| `/country/all/indicator/{indicator}` | Data indikator global (semua negara) |
| `/indicator?format=json` | Daftar semua indikator yang tersedia |
| `/country?format=json` | Daftar semua negara |
| `/source?format=json` | Daftar sumber data |

### Contoh Request
```
# Populasi Indonesia dari tahun ke tahun
GET https://api.worldbank.org/v2/country/IDN/indicator/SP.POP.TOTL?format=json&per_page=50

# GDP per capita Indonesia
GET https://api.worldbank.org/v2/country/IDN/indicator/NY.GDP.PCAP.CD?format=json&per_page=50

# Kemiskinan (persentase di bawah $2.15/hari)
GET https://api.worldbank.org/v2/country/IDN/indicator/SI.POV.DDAY?format=json&per_page=50

# Semua indikator untuk Indonesia
GET https://api.worldbank.org/v2/country/IDN/indicator?format=json
```

### Indikator Populer untuk UMKM/Edukasi Indonesia
| Kode Indikator | Nama | Relevansi |
|----------------|------|-----------|
| `SP.POP.TOTL` | Total Populasi | Ukuran pasar |
| `NY.GDP.PCAP.CD` | GDP per Capita (USD) | Daya beli |
| `SI.POV.DDAY` | Poverty Headcount ($2.15/day) | Kemiskinan |
| `SE.ADT.LITR.ZS` | Literacy Rate (15+) | Pendidikan |
| `SE.ENR.PRSC.FM` | School Enrollment (primary) | Akses pendidikan |
| `IC.REG.DURS` | Days to Start Business | Kemudahan berusaha |
| `SM.POP.NETM` | Net Migration | Mobilitas penduduk |
| `FP.CPI.TOTL.ZG` | Inflation (CPI) | Stabilitas harga |
| `BN.CAB.XOKA.CD` | Current Account Balance | Neraca perdagangan |
| `EG.USE.ELEC.KH.PC` | Electric Power Consumption | Infrastruktur |

### Format Response (contoh)
```json
[
  {"page": 1, "pages": 5, "per_page": 50, "total": 250},
  [
    {"indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
     "country": {"id": "IDN", "value": "Indonesia"},
     "date": "2023",
     "value": 277534122}
  ]
]
```

### Catatan Penting
- Kode negara ISO3: `IDN` = Indonesia, `USA` = Amerika, `CHN` = China
- `per_page` max 10000, gunakan pagination untuk data besar
- Response format: array [metadata, data[]]

---

## 3. Portal Satu Data Indonesia (data.go.id)

### Informasi Umum
| Field | Nilai |
|-------|-------|
| Portal | https://data.go.id |
| API Docs | https://satu-data.layananpublik.com/layanan/api |
| Operator | Kementerian Kominfo RI (Satu Data Indonesia) |
| Tipe data | 616,000+ dataset dari seluruh K/L & Pemda |
| Format response | JSON |
| API key | **Mungkin diperlukan** — cek portal untuk registrasi |
| Rate limit | Ada rate limiter (header `X-RateLimit-*`) |
| Lisensi | Data pemerintah Indonesia, terbuka dengan catatan |

### Endpoint Utama

**Base URL:** `https://api.satu-data.layananpublik.com`

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/v1/datasets?page=&limit=` | GET | Daftar dataset |
| `/v1/datasets/{id}` | GET | Detail satu dataset |
| `/v1/datasets/{id}/download` | GET | Download dataset |
| `/v1/categories` | GET | Daftar kategori |

### Contoh Request
```bash
# Cari dataset
curl -X GET "https://api.satu-data.layananpublik.com/v1/datasets?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Detail dataset tertentu
curl -X GET "https://api.satu-data.layananpublik.com/v1/datasets/12345" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Catatan Penting
- Portal data.go.id sedang dalam kurasi — beberapa dataset mungkin belum tersedia via API
- Data terdiri dari berbagai format (CSV, JSON, XLS) — perlu normalisasi
- Beberapa dataset berupa metadata saja (bukan data mentah)
- Untuk data kota spesifik, cek portal data kota masing-masing (contoh: satudata.bandarlampungkota.go.id)

---

## 4. Wikidata / Wikipedia API

### Informasi Umum
| Field | Nilai |
|-------|-------|
| API Endpoint | https://www.wikidata.org/w/api.php |
| Tipe data | Entity terstruktur (populasi, geografi, sejarah, dll) |
| Format response | JSON |
| API key | **Tidak perlu** |
| Rate limit | ~200 req/s (sangat toleran) |
| Lisensi | **CC-BY-SA 4.0** — boleh komersial dengan atribusi |

### Endpoint Utama
| Endpoint | Parameter | Deskripsi |
|----------|-----------|-----------|
| Wikidata Query Service | SPARQL | Query data terstruktur |
| Wikipedia API | `action=query` | Cari artikel, extract data |

### Contoh SPARQL Query
```sparql
# Populasi semua provinsi Indonesia
SELECT ?prov ?provLabel ?pop WHERE {
  ?prov wdt:P31 wd:Q15760237 .  # provinsi Indonesia
  ?prov wdt:P1082 ?pop .         # populasi
  SERVICE wikibase:label { bd:serviceParam wikibase:language "id,en". }
}
```

### Catatan Penting
- Butuh SPARQL query untuk data terstruktur → wrapper Python diperlukan
- Cocok untuk data geografi, demografi, informasi umum
- Bukan sumber utama untuk data ekonomi detail

---

## 5. Open Data Kota/Provinsi

### Contoh Portal

| Portal | URL | API | Catatan |
|--------|-----|-----|---------|
| Jakarta Open Data | data.jakarta.go.id | REST API | Data DKI Jakarta |
| Jawa Timur | data.jatimprov.go.id | REST API | Data provinsi Jatim |
| Bandar Lampung | satudata.bandarlampungkota.go.id | REST API | Data kota |
| Kaltim | data.kaltimprov.go.id | REST API | Data Kaltim |

### Pola Umum API
```
GET /api/public/v1/dataset-records?year=2025&topic=econom
GET /api/public/v1/dataset-years
GET /api/public/v1/data-producers
```

### Catatan Penting
- Format API relatif seragam (sebagian besar pakai pola REST yang mirip)
- Data spesifik daerah — cocok untuk use case lokal
- Ketersediaan API bervariasi antar daerah
- Beberapa portal hanya punya metadata, bukan data mentah

---

## Ringkasan Perbandingan Sumber

| Sumber | API Key | Rate Limit | Lisensi | Ketersediaan Data | Kompleksitas Integrasi |
|--------|---------|------------|---------|-------------------|----------------------|
| BPS | Ya (gratis) | ~2 req/s | Publik | Tinggi (1,000+ dataset) | Sedang |
| World Bank | Tidak | Toleran | CC-BY 4.0 | Sangat Tinggi (16,000+ indikator) | Rendah |
| data.go.id | Mungkin | Ada | Publik | Sangat Tinggi (616,000+) | Sedang-Tinggi |
| Wikidata | Tidak | 200 req/s | CC-BY-SA 4.0 | Tinggi | Tinggi (SPARQL) |
| Open Data Kota | Tergantung | Tergantung | Tergantung | Rendah-Sedang | Sedang |

---

## Implementasi yang Direkomendasikan

### Fase 1-3: BPS + World Bank (Prioritas Utama)
- BPS: paling relevan untuk konteks Indonesia, data ekonomi/demografi
- World Bank: global benchmark, lisensi paling jelas (CC-BY), tanpa API key

### Fase 4-5: data.go.id + Cache
- data.go.id: cakupan luas tapi perlu validasi ketersediaan API
- Cache wajib sebelum tambah sumber untuk hindari rate limit issues

### Fase 6+: Open Data Lokal
- Hanya jika ada kebutuhan spesifik dari user

---

*Dokumen ini akan diperbarui seiring implementasi fitur.*
