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
`Lamaran [Nama Posisi] | [Nama Kandidat] | Agent Agency AI Project | WA 6287813871926`

AI dapat memendekkan subject bila nama posisi terlalu panjang. Project disebut secara natural, bukan sebagai pengalaman kerja fiktif.

Body menyebut CV terlampir dan WhatsApp 6287813871926.

## Google Sheets
Tab `Job Applications` otomatis membuat/menambahkan header: job_id, job_title, company, company_tier, category, work_mode, location, source_url, published_date, deadline_date, recipient_email, candidate_headline, ai_project_note, fit_score, fit_reason, subject, body, status, send_approved, dan timestamp. Jadi kolom `candidate_headline` akan terisi otomatis dengan headline CV.

## Jadwal
GitHub Actions menjalankan discovery setiap hari pada beberapa window pagi/siang WIB: sekitar 06:00, 08:00, 10:00, dan 13:00 WIB. Benchmark 2026 yang tersedia cenderung menempatkan Selasa-Kamis pagi sebagai window yang baik, tetapi timing bukan jaminan diterima dan kualitas kecocokan tetap faktor utama.

## Secrets
- `CV_PDF_BASE64` — CV PDF disimpan sebagai GitHub Actions secret, bukan di repository publik.
- `GEMINI_API_KEY`
- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

Untuk mengisi `CV_PDF_BASE64` dari file CV di komputer: `base64 -w 0 Reynaldi_Kurnia_Sonjaya_Resume.pdf | gh secret set CV_PDF_BASE64` (macOS: gunakan `base64 < file.pdf | tr -d '\\n' | gh secret set CV_PDF_BASE64`).

Email kandidat dikonfigurasi sebagai `reybyoo@gmail.com` dan WhatsApp sebagai `6287813871926` di workflow. Perlu diperhatikan: CV yang diunggah saat ini masih menampilkan email `reynaldis334@gmail.com`; sebaiknya samakan email di CV dengan alamat pengirim sebelum mulai melamar agar tidak membingungkan HR.

## Pengiriman
Mesin ini otomatis mencari, menyaring, menganalisis, dan menyiapkan lamaran. Pengiriman massal tanpa review tidak diaktifkan. Baris yang lolos berstatus `READY` sehingga bisa ditinjau sebelum dikirim.

Gunakan kredensial Gmail yang aman; jangan memasukkan password Gmail biasa ke repository.

## Catatan
Tidak ada mesin pencari yang dapat menjamin benar-benar melihat semua lowongan di internet. Sistem menggabungkan beberapa query publik, melakukan deduplikasi, dan menyimpan hasil yang terdeteksi.
## Kirim setelah review
Untuk mengirim satu lamaran yang sudah berstatus `READY`, gunakan `python -m app.send_single JOB_ID` pada environment yang memiliki kredensial Gmail dan CV PDF. Sistem pengiriman tidak mempunyai mode bulk 100-300 email otomatis.
