# Bandung Job Hunter

Sistem ini terdiri dari dua tahap: mengumpulkan database lowongan dan mengirim hanya baris yang kamu pilih di Google Sheets.

## 1. Discovery

Agent mencari lowongan publik di Bandung untuk:
- semua aspek marketing: marketing, digital marketing, performance marketing, brand, social media, content, copywriting, SEO/SEM, CRM, KOL, influencer, marketing communication, PR, activation, partnership, growth, sales & marketing, dan variasinya;
- back office: admin, administration, finance, accounting, HR/HRD, recruitment, purchasing, procurement, legal, secretary, data entry, operations, customer service/support, general affair, dan variasinya;
- semua mode kerja: full-time, part-time, freelance, contract, internship, hybrid, remote/WFH, dan on-site.

Lowongan harus relatif hangat, default maksimal 14 hari atau masih mempunyai deadline aktif. Lowongan umum tanpa tanggal yang dapat diverifikasi tidak dimasukkan kecuali ALLOW_UNKNOWN_DATE=true.

Aturan email:
- Jika lowongan menyediakan Gmail untuk menerima lamaran, lowongan masuk sebagai kandidat kirim.
- Jika perusahaan terkenal/bagus tetapi memakai ATS/portal resmi tanpa Gmail, lowongan tetap masuk sebagai WATCHLIST.
- Lowongan non-Gmail biasa tidak dimasukkan.

Sistem menggabungkan beberapa sumber publik dan query perusahaan besar. Tidak ada crawler yang bisa menjamin mencakup 100% internet.



## 2A. Cakupan discovery

Discovery dibuat multi-sumber untuk mencari seluas mungkin lowongan publik yang terindeks:
- LinkedIn Jobs dan Glints sebagai sumber utama.
- portal kerja Indonesia: JobStreet, Indeed, Kalibrr, KitaLulus, Dealls, Pintarnya, Talentics, KarirHub/Kemnaker, Karir.com, Loker.id, TopKarir, Urbanhire, EKRUT, Tech in Asia Jobs, Glassdoor, HiredToday, Toploker, dan Redy.
- Google hanya dipakai sebagai mesin pencari untuk menemukan halaman publik dari platform-platform tersebut; Bing dan Brave tidak dipakai.

Tidak ada crawler yang secara jujur dapat menjamin 100% internet, terutama konten yang login-only, aplikasi mobile-only, private group, atau halaman yang melarang crawler.

## 2B. Pembacaan flyer/gambar

Saat halaman lowongan dibuka, agent mengambil gambar dari:
- og:image / Twitter image;
- gambar pada HTML dan lazy-loaded image;
- image pada JSON-LD;
- beberapa URL gambar yang ditemukan pada CSS;
- gambar yang tersedia langsung dari halaman platform; tidak ada ketergantungan pada pencarian gambar Bing/Brave.

Gambar lowongan diteruskan ke Gemini sebagai input multimodal. AI diminta membaca semua gambar yang tersedia, mengabaikan logo/icon yang bukan flyer, lalu mengekstrak fakta yang terlihat seperti posisi, perusahaan, deadline, email, WhatsApp, lokasi, benefit, syarat, dan cara melamar.

Hasil ringkasannya disimpan di kolom `flyer_summary`, sedangkan URL gambar yang ditemukan disimpan di `flyer_image_urls`.

## 2. Google Sheets

Sheet utama: Job Applications

Kolom:
job_id | found_at | published_date | deadline_date | age_days | job_title | company | company_tier | category | work_mode | location | source_url | source_domain | application_method | recipient_email | prospect_score | score_reason | candidate_headline | ai_project_note | subject | body | status | sent_at | send_error | notes

prospect_score adalah skor kualitas lowongan 0-100 berdasarkan kebaruan, Gmail, relevansi kategori, kualitas sumber, dan perusahaan terkenal. Ini bukan skor kecocokan CV.

Status:
BARU = baru ditemukan
SIAP_REVIEW = email sudah dibuat AI
KIRIM = kamu memilih lowongan ini untuk dikirim
TERKIRIM = berhasil dikirim
ERROR = pengiriman gagal
WATCHLIST = menarik tetapi tidak ada Gmail

Cara kerja utama: ubah status dari SIAP_REVIEW menjadi KIRIM. Peak Sender akan mengambil baris itu otomatis pada jadwal pengiriman berikutnya.

## 3. Candidate Profile

Sheet kedua: Candidate Profile

Gunakan dua kolom: key dan value.

candidate_name = REYNALDI KURNIA SONJAYA
headline = Leader | Mentor | Marketing Officer | Data Analyst | Digital Marketing | Promotion | Influencer
email = reybyoo@gmail.com
whatsapp = 6287813871926
ai_project = Saat ini saya juga mengembangkan project Agent Agency AI untuk membantu pekerjaan menjadi lebih mudah, terstruktur, dan efisien.

Kamu boleh mengubah headline dan ai_project kapan saja. Run berikutnya AI membaca nilai terbaru dari Sheet.

CV PDF dibaca untuk mengambil pengalaman/skill yang relevan ketika AI menulis lamaran, tetapi CV tidak dipakai untuk membatasi lowongan yang dicari.

## 4. Email AI

AI membuat body berbeda untuk setiap lowongan berdasarkan judul/isi posisi dan profil kandidat.

Contoh subject:
Lamaran [Nama Posisi] | [Nama Kandidat] | WA 6287813871926

Bila relevan, body dapat menyebut project Agent Agency AI sebagai project yang sedang dikembangkan untuk membantu membuat pekerjaan lebih mudah, terstruktur, dan efisien. Tidak boleh diposisikan sebagai pengalaman kerja fiktif.

CV PDF dilampirkan saat email dikirim.

## 5. Peak Sender

GitHub Actions menjalankan pengirim pada window pagi/siang WIB.

Schedule saat ini sekitar 06:30, 07:30, 08:30, 09:30, 10:30, dan 13:30 WIB setiap hari.

Setiap run hanya memproses baris dengan status KIRIM dan recipient_email berakhiran @gmail.com.

## 6. Secrets GitHub

GitHub Actions membatasi ukuran satu Secret. Karena CV PDF kamu menghasilkan Base64 sekitar 284 ribu karakter, konfigurasi ini memakai tujuh Secret untuk CV:
CV_PDF_BASE64_1
CV_PDF_BASE64_2
CV_PDF_BASE64_3
CV_PDF_BASE64_4
CV_PDF_BASE64_5
CV_PDF_BASE64_6
CV_PDF_BASE64_7

Jangan membuat secret CV_PDF_BASE64 berisi seluruh CV karena akan melewati batas ukuran.

Untuk membagi CV secara otomatis:
python scripts/prepare_cv_secret_parts.py /path/to/CV.pdf

Script tersebut membuat cv_secret_part_1.txt sampai cv_secret_part_7.txt. Isi masing-masing file ditempel ke Secret dengan nama yang sesuai. Jangan commit file .txt tersebut ke repository.

Secret lain yang wajib diset:
GEMINI_API_KEY
GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON
GMAIL_APP_PASSWORD

Pengirim: reybyoo@gmail.com
WhatsApp: 6287813871926

Jangan menyimpan password Gmail biasa di repository.