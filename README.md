# Bandung Job Hunter

Repo ini sekarang menjadi mesin pencari lowongan kerja Bandung berbasis CV.

## Fokus
- Semua aspek marketing: marketing, digital/performance marketing, brand, social media, content, copywriting, SEO/SEM, CRM, KOL, partnership, marcom, PR, activation, sales/marketing, dan variasinya.
- Back office yang relevan dengan CV: admin, finance/accounting, HR/recruitment, purchasing/procurement, legal, secretary, data entry, operations, customer service/support, dan variasinya.
- Mode kerja bebas: full-time, part-time, freelance, contract, internship, hybrid, remote/WFH, dan on-site.
- Filter lokasi Bandung.
- Prioritas listing yang masih terbuka dan relatif baru.
- Penerima hanya alamat Gmail publik yang secara konteks dipakai untuk menerima lamaran.

## AI CV matching
CV PDF menjadi sumber utama. Gemini menilai kecocokan setiap lowongan dan membuat email lamaran yang spesifik untuk posisi tersebut.

Subjek default:
`Lamaran [Nama Posisi] - [Nama Kandidat] | WA 6287813871926`

Body menyebut CV terlampir dan nomor WhatsApp 6287813871926 tanpa mengarang pengalaman atau fakta perusahaan.

## Google Sheets
Setelah konfigurasi Google Sheets, tab `Job Applications` dipakai untuk memantau job_id, posisi, perusahaan, kategori, work mode, sumber, tanggal, Gmail penerima, fit score, alasan kecocokan, subject, body, status, dan approval.

## Jadwal
GitHub Actions menjalankan pencarian pada beberapa pagi hari kerja WIB agar antrean lowongan baru tersedia sebelum jam kerja. Jadwal saat ini UTC `0,2,4` yang setara sekitar 07:00, 09:00, dan 11:00 WIB.

Berbagai benchmark 2026 menunjukkan pagi hari Selasa-Kamis sering menjadi window yang baik untuk visibilitas aplikasi, tetapi timing bukan jaminan diterima dan kualitas kecocokan tetap lebih penting. cite tidak disimpan di README GitHub; referensi ada di dokumentasi chat.

## Secrets
- `CANDIDATE_NAME`
- `CV_PDF_BASE64`
- `GEMINI_API_KEY`
- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

`GMAIL_ADDRESS` dan nomor WhatsApp dikonfigurasi di workflow sebagai identitas kandidat.

## Status pengiriman
Repo ini menyiapkan antrean lamaran dan personalisasi otomatis. Pengiriman massal tanpa review tidak diaktifkan. Baris yang lolos akan berstatus `READY` dan dapat diproses setelah ditinjau.

Jangan simpan password Gmail biasa. Untuk koneksi Gmail yang memerlukan SMTP, gunakan mekanisme kredensial khusus yang aman dan sesuai kebijakan Google.

## Catatan
Mesin pencarian tidak dapat menjamin benar-benar mencakup semua lowongan internet. Ia menggabungkan hasil dari beberapa query publik, melakukan deduplikasi, lalu menyimpan hasil yang terdeteksi.