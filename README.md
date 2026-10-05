# Bandung Job Hunter

Repo ini sekarang menjadi mesin pencari lowongan kerja Bandung berbasis CV.

## Fokus
- Semua aspek marketing: marketing, digital/performance marketing, brand, social media, content, copywriting, SEO/SEM, CRM, KOL, partnership, marcom, PR, activation, sales/marketing, dan variasinya.
- Back office yang relevan dengan CV: admin, finance/accounting, HR/recruitment, purchasing/procurement, legal, secretary, data entry, operations, customer service/support, dan variasinya.
- Mode kerja: full-time, part-time, freelance, contract, internship, hybrid, remote/WFH, dan on-site.
- Lokasi: Bandung.
- Prioritas: listing baru dan/atau masih terbuka.
- Penerima: alamat Gmail publik yang terdeteksi dalam konteks menerima lamaran.

## AI CV matching
CV PDF menjadi sumber utama. Gemini membaca CV dan lowongan, memberi fit score, lalu membuat subject dan body email yang berbeda untuk setiap posisi. Pengalaman atau skill tidak boleh diada-adakan.

Subjek default:
`Lamaran [Nama Posisi] - [Nama Kandidat] | WA 6287813871926`

Body menyebut CV terlampir dan WhatsApp 6287813871926.

## Google Sheets
Tab `Job Applications` menyimpan job_id, posisi, perusahaan, kategori, work mode, sumber, tanggal, Gmail penerima, fit score, alasan kecocokan, subject, body, status, dan approval.

## Jadwal
GitHub Actions menjalankan discovery beberapa kali pada pagi hari kerja WIB. Jadwal UTC `0,2,4` setara sekitar 07:00, 09:00, dan 11:00 WIB. Benchmark 2026 yang tersedia cenderung menempatkan Selasa-Kamis pagi sebagai window yang baik, tetapi timing bukan jaminan diterima dan kualitas kecocokan tetap faktor utama.

## Secrets
- `CANDIDATE_NAME`
- `CV_PDF_BASE64`
- `GEMINI_API_KEY`
- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

Email kandidat dikonfigurasi sebagai `reybyoo@gmail.com` dan WhatsApp sebagai `6287813871926` di workflow.

## Pengiriman
Mesin ini otomatis mencari, menyaring, menganalisis, dan menyiapkan lamaran. Pengiriman massal tanpa review tidak diaktifkan. Baris yang lolos berstatus `READY` sehingga bisa ditinjau sebelum dikirim.

Gunakan kredensial Gmail yang aman; jangan memasukkan password Gmail biasa ke repository.

## Catatan
Tidak ada mesin pencari yang dapat menjamin benar-benar melihat semua lowongan di internet. Sistem menggabungkan beberapa query publik, melakukan deduplikasi, dan menyimpan hasil yang terdeteksi.
## Kirim setelah review
Untuk mengirim satu lamaran yang sudah berstatus `READY`, gunakan `python -m app.send_single JOB_ID` pada environment yang memiliki kredensial Gmail dan CV PDF. Sistem pengiriman tidak mempunyai mode bulk 100-300 email otomatis.
