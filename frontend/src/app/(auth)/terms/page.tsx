import Link from 'next/link';

export const metadata = {
  title: 'Syarat & Ketentuan - ML Pipeline',
};

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="mb-8">
          <Link href="/login" className="text-sm text-blue-600 hover:text-blue-500">
            &larr; Kembali ke Login
          </Link>
        </div>

        <h1 className="text-3xl font-bold text-zinc-900 dark:text-white mb-2">Syarat & Ketentuan</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">Terakhir diperbarui: 5 Agustus 2026</p>

        <div className="prose dark:prose-invert max-w-none space-y-8 text-zinc-700 dark:text-zinc-300">
          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">1. Penerimaan Syarat</h2>
            <p>
              Dengan mengakses dan menggunakan ML Pipeline (&quot;Layanan&quot;), Anda menyetujui untuk terikat oleh
              Syarat dan Ketentuan ini. Jika Anda tidak menyetujui syarat-syarat ini, mohon untuk tidak menggunakan Layanan.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">2. Deskripsi Layanan</h2>
            <p>
              ML Pipeline adalah platform manajemen pipeline machine learning yang menyediakan fitur untuk:
            </p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Upload dan manajemen dataset</li>
              <li>Training model machine learning</li>
              <li>Eksperimen dan perbandingan model</li>
              <li>Deploy model ke production</li>
              <li>Monitoring kinerja model</li>
              <li>Kolaborasi tim dalam proyek ML</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">3. Akun Pengguna</h2>
            <p>
              Anda bertanggung jawab untuk menjaga kerahasiaan kredensial akun Anda. Anda harus segera memberi tahu
              kami jika Anda mencurigai adanya penggunaan akun Anda yang tidak sah. Kami tidak bertanggung jawab atas
              kerugian yang timbul dari penggunaan akun Anda yang tidak sah.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">4. Penggunaan yang Diperbolehkan</h2>
            <p>Anda setuju untuk:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Menggunakan Layanan sesuai dengan hukum yang berlaku</li>
              <li>Tidak menggunakan Layanan untuk aktivitas ilegal atau merugikan pihak lain</li>
              <li>Tidak mencoba mengakses sistem atau data yang tidak berwenang</li>
              <li>Tidak mengganggu atau membebani infrastruktur Layanan</li>
              <li>Menghormati hak kekayaan intelektual pengguna lain</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">5. Data dan Model</h2>
            <p>
              Anda mempertahankan kepemilikan penuh atas data dan model yang Anda upload ke Layanan. Kami tidak
              akan menggunakan data atau model Anda untuk tujuan selain menyediakan Layanan kepada Anda, kecuali
              Anda memberikan persetujuan eksplisit.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">6. Batasan Tanggung Jawab</h2>
            <p>
              Layanan disediakan &quot;sebagaimana adanya&quot; tanpa jaminan apapun. Kami tidak menjamin bahwa
              Layanan akan selalu tersedia, aman, atau bebas dari kesalahan. Kami tidak bertanggung jawab atas
              kerugian tidak langsung, insidental, atau konsekuensial yang timbul dari penggunaan Layanan.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">7. Perubahan Ketentuan</h2>
            <p>
              Kami berhak untuk mengubah Syarat dan Ketentuan ini kapan saja. Perubahan akan berlaku efektif
              setelah dipublikasikan di halaman ini. Penggunaan Layanan setelah perubahan berarti Anda menyetujui
              ketentuan yang diperbarui.
            </p>

          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">8. Hukum yang Berlaku</h2>
            <p>
              Syarat dan Ketentuan ini tunduk pada hukum Negara Republik Indonesia. Setiap sengketa akan
              diselesaikan melalui pengadilan yang berwenang di wilayah Republik Indonesia.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-white">9. Kontak</h2>
            <p>
              Jika Anda memiliki pertanyaan mengenai Syarat dan Ketentuan ini, silakan hubungi kami melalui
              email: legal@mlpipeline.com
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
