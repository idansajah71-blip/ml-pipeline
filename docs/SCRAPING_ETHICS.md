# Panduan Etika Penggunaan Scraping

Fitur scraping di platform ini hanya boleh digunakan untuk:
- Data publik yang tidak memiliki larangan scraping (cek robots.txt)
- Data milik sendiri atau dengan izin tertulis dari pemilik situs
- Tujuan riset non-komersial yang sesuai Terms of Service sumber data

## Fitur yang Dibatasi

Fitur bypass captcha, fingerprint spoofing, dan distributed scraper **HANYA** dapat diakses oleh user dengan role **Admin** atau **Data Scientist**.

Fitur ini memerlukan pertimbangan etis dan legal sebelum digunakan.

## Yang DILARANG

- Mengakses data yang dilindungi tanpa izin
- Melanggar Terms of Service situs target
- Tujuan komersial tanpa persetujuan pemilik data
- Scraping yang membebani server target (overloading)

## Konsekuensi

Pelanggaran dapat melanggar:
- Undang-Undang Informasi dan Transaksi Elektronik (UU ITE)
- Computer Fraud and Abuse Act (CFAA)
- Terms of Service situs target

## Tips Penggunaan yang Bertanggung Jawab

1. Selalu periksa `robots.txt` situs target
2. Gunakan delay yang wajar antara request (minimal 1 detik)
3. Batasi jumlah request sesuai kebutuhan
4. Hormati rate limit yang ditetapkan situs
5. Gunakan data hanya untuk tujuan yang telah dideklarasikan
