import Link from 'next/link';

export const metadata = {
  title: 'Kebijakan Privasi - ML Pipeline',
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="mb-8">
          <Link href="/login" className="text-sm text-blue-600 hover:text-blue-500">
            &larr; Kembali ke Login
          </Link>
        </div>

        <h1 className="text-3xl font-bold text-zinc-900 dark:text-white mb-2">Kebijakan Privasi</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">Terakhir diperbarui: 5 Agustus 2026</p>

        <div className="prose dark:prose-invert max-w-none space-y-8 text-zinc-700 dark:text-zinc-300">
          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">1. Informasi yang Kami Kumpulkan</h2>
            <p>Kami mengumpulkan informasi berikut saat Anda menggunakan Layanan:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Informasi Akun:</strong> Nama, alamat email, dan kata sandi (dienkripsi)</li>
              <li><strong>Data yang Diupload:</strong> Dataset, model, dan file lain yang Anda unggah</li>
              <li><strong>Data Penggunaan:</strong> Log aktivitas, metadata permintaan API, dan preferensi</li>
              <li><strong>Informasi Sistem:</strong> Alamat IP, jenis browser, dan sistem operasi</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">2. Penggunaan Informasi</h2>
            <p>Kami menggunakan informasi yang dikumpulkan untuk:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Menyediakan dan memelihara Layanan</li>
              <li>Memproses transaksi dan mengirim notifikasi terkait</li>
              <li>Menganalisis penggunaan untuk meningkatkan kualitas Layanan</li>
              <li>Mencegah penyalahgunaan dan menjaga keamanan</li>
              <li>Mematuhi kewajiban hukum</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">3. Penyimpanan dan Keamanan Data</h2>
            <p>
              Data Anda disimpan di server yang aman dengan enkripsi saat transit (TLS) dan saat disimpan (AES-256).
              Kami menerapkan kontrol akses ketat dan melakukan audit keamanan secara berkala. Namun, tidak ada
              metode transmisi atau penyimpanan yang 100% aman, dan kami tidak dapat menjamin keamanan mutlak.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">4. Berbagi Data</h2>
            <p>Kami tidak menjual atau menyewakan data pribadi Anda kepada pihak ketiga. Kami dapat berbagi informasi hanya dalam kasus berikut:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Dengan persetujuan eksplisit dari Anda</li>
              <li>Untuk mematuhi kewajiban hukum atau perintah pengadilan</li>
              <li>Untuk melindungi hak dan keamanan kami atau pengguna lain</li>
              <li>Dengan penyedia layanan yang membantu operasi kami (dikirim secara rahasia)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">5. Hak Anda</h2>
            <p>Anda memiliki hak untuk:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Mengakses data pribadi Anda yang tersimpan</li>
              <li>Memperbaiki data yang tidak akurat</li>
              <li>Meminta penghapusan data pribadi Anda</li>
              <li>Membatasi pemrosesan data Anda</li>
              <li>Meminta portabilitas data</li>
              <li>Menolak pemrosesan data untuk tujuan tertentu</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">6. Retensi Data</h2>
            <p>
              Kami menyimpan data akun Anda selama akun aktif. Dataset dan model dapat dikonfigurasi untuk
              retensi otomatis berdasarkan tier langganan Anda (30 hari untuk Free, 90 hari untuk Starter,
              180 hari untuk Pro, tak terbatas untuk Enterprise).
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">7. Cookie</h2>
            <p>
              Kami menggunakan cookie yang diperlukan untuk autentikasi dan preferensi tema. Kami tidak menggunakan
              cookie pelacakan atau cookie pihak ketiga untuk iklan.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">8. Perubahan Kebijakan</h2>
            <p>
              Kami dapat memperbarui Kebijakan Privasi ini dari waktu ke waktu. Perubahan akan diberitahukan
              melalui email atau notifikasi di Layanan. Penggunaan Layanan setelah perubahan berarti Anda menyetujui
              kebijakan yang diperbarui.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">9. Kontak</h2>
            <p>
              Untuk pertanyaan mengenai Kebijakan Privasi ini, silakan hubungi kami di: privacy@mlpipeline.com
            </p>
          </section>
        </div>

        <div className="mt-12 pt-8 border-t border-zinc-200 dark:border-zinc-800">
          <Link href="/register" className="text-sm text-blue-600 hover:text-blue-500">
            &larr; Kembali ke Pendaftaran
          </Link>
        </div>
      </div>
    </div>
  );
}
