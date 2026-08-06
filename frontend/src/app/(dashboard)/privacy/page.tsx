'use client';

import { Shield, ArrowLeft, FileText } from 'lucide-react';
import Link from 'next/link';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          <ArrowLeft className="h-4 w-4" /> Kembali ke beranda
        </Link>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-6 flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Kebijakan Privasi</h1>
              <p className="text-sm text-gray-500">Terakhir diperbarui: 6 Agustus 2026</p>
            </div>
          </div>

          <div className="prose prose-sm max-w-none text-gray-700 dark:text-gray-300 space-y-6">
            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">1. Pengumpulan Data</h2>
              <p>ML Pipeline mengumpulkan data berikut saat Anda menggunakan layanan kami:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Data Akun:</strong> Nama, alamat email, dan password (dienkripsi) saat Anda mendaftar.</li>
                <li><strong>Data Dataset:</strong> File dataset yang Anda unggah untuk pelatihan model. Data ini disimpan di server kami dan hanya dapat diakses oleh Anda.</li>
                <li><strong>Data Model:</strong> Model machine learning yang Anda buat, termasuk parameter dan metrik performa.</li>
                <li><strong>Data Penggunaan:</strong> Log penggunaan API, timestamp, dan metadata request untuk keperluan monitoring dan peningkatan layanan.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">2. Penggunaan Data</h2>
              <p>Data Anda digunakan untuk:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Menyediakan dan mengoperasikan layanan ML Pipeline</li>
                <li>Memproses pelatihan model dan prediksi yang Anda minta</li>
                <li>Menampilkan metrik performa dan monitoring model</li>
                <li>Mengirim notifikasi terkait penggunaan layanan</li>
                <li>Meningkatkan kualitas dan keamanan layanan</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">3. Keamanan Data</h2>
              <p>Kami menerapkan langkah-langkah keamanan berikut:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Enkripsi data saat transit (TLS/HTTPS)</li>
                <li>Enkripsi password menggunakan bcrypt</li>
                <li>JWT token untuk autentikasi dengan refresh token rotasi</li>
                <li>Akses data dibatasi per pengguna (multi-tenancy)</li>
                <li>Backup data secara berkala</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">4. Berbagi Data</h2>
              <p>Kami tidak menjual atau membagikan data pribadi Anda kepada pihak ketiga, kecuali:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Anda secara eksplisit membagikan model melalui fitur Marketplace</li>
                <li>Diperlukan oleh hukum atau perintah pengadilan</li>
                <li>Untuk melindungi hak dan keamanan pengguna lain</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">5. Retensi Data</h2>
              <p>Data Anda disimpan berdasarkan tier langganan:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Free:</strong> Dataset 30 hari, Model 60 hari</li>
                <li><strong>Starter:</strong> Dataset 90 hari, Model 180 hari</li>
                <li><strong>Pro:</strong> Dataset 365 hari, Model 730 hari</li>
                <li><strong>Enterprise:</strong> Tanpa batas</li>
              </ul>
              <p>Anda dapat menghapus data kapan saja melalui pengaturan akun.</p>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">6. Hak Anda</h2>
              <p>Anda memiliki hak untuk:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Mengakses semua data yang kami simpan tentang Anda</li>
                <li>Menghapus akun dan semua data terkait</li>
                <li>Mengekspor data Anda dalam format standar</li>
                <li>Membatasi pemrosesan data tertentu</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">7. Cookie</h2>
              <p>ML Pipeline menggunakan cookie yang diperlukan untuk:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Menyimpan sesi login (JWT token)</li>
                <li>Preferensi tema (gelap/terang)</li>
                <li>Status onboarding pengguna baru</li>
              </ul>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">8. Perubahan Kebijakan</h2>
              <p>Kebijakan ini dapat diperbarui sewaktu-waktu. Perubahan signifikan akan diberitahukan melalui email atau notifikasi di aplikasi.</p>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">9. Kontak</h2>
              <p>Jika Anda memiliki pertanyaan tentang kebijakan privasi ini, hubungi kami di:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Email: privacy@mlpipeline.com</li>
                <li>GitHub: github.com/idansajah71-blip/ml-pipeline</li>
              </ul>
            </section>
          </div>
        </div>

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-4 flex items-center gap-3">
            <FileText className="h-6 w-6 text-primary-600" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Syarat & Ketentuan</h2>
          </div>

          <div className="prose prose-sm max-w-none text-gray-700 dark:text-gray-300 space-y-4">
            <section>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">1. Penerimaan Syarat</h3>
              <p>Dengan menggunakan ML Pipeline, Anda menyetujui syarat dan ketentuan ini. Jika Anda tidak setuju, mohon tidak menggunakan layanan ini.</p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">2. Penggunaan Layanan</h3>
              <p>Layanan ini tersedia untuk:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Eksperimen dan penelitian machine learning</li>
                <li>Pembelajaran dan pendidikan</li>
                <li>Pengembangan prototipe model ML</li>
              </ul>
              <p>Dilarang menggunakan layanan ini untuk aktivitas ilegal, menyebarkan malware, atau melakukan serangan terhadap sistem lain.</p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">3. Hak Kekayaan Intelektual</h3>
              <p>Model yang Anda buat menggunakan ML Pipeline adalah milik Anda sepenuhnya. Kami tidak mengklaim hak atas model atau data Anda.</p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">4. Pembatasan Tanggung Jawab</h3>
              <p>Layanan disediakan &quot;sebagaimana adanya&quot; tanpa jaminan. Kami tidak bertanggung jawab atas kerugian yang mungkin timbul dari penggunaan layanan ini.</p>
            </section>

            <section>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">5. Penghentian Layanan</h3>
              <p>Kami berhak menghentikan akses Anda jika melanggar syarat dan ketentuan ini, atau jika terdeteksi aktivitas mencurigakan pada akun Anda.</p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
