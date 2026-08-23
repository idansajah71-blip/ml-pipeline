'use client';

import { useRouter } from 'next/navigation';
import { Database, Brain, Zap, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const steps = [
  {
    icon: Database,
    title: 'Upload Data',
    description: 'Unggah dataset pertama Anda (CSV/Excel) atau coba dataset contoh.',
    href: '/datasets',
    cta: 'Upload dataset pertama saya',
  },
  {
    icon: Brain,
    title: 'Train Model',
    description: 'Pilih dataset, tentukan kolom target, dan mulai training dengan satu klik.',
    href: '/training-wizard',
    cta: 'Buka Training Wizard',
  },
  {
    icon: Zap,
    title: 'Buat Prediksi',
    description: 'Masukkan data baru ke model yang sudah dilatih dan lihat hasilnya.',
    href: '/try-predict',
    cta: 'Coba prediksi',
  },
];

export default function GettingStartedPage() {
  const router = useRouter();
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Selamat datang, {user?.full_name || user?.username || 'User'}!
        </h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Ikuti 3 langkah berikut untuk memulai dengan ML Pipeline.
        </p>
      </div>

      <div className="space-y-4">
        {steps.map((step, i) => (
          <button
            key={step.href}
            onClick={() => router.push(step.href)}
            className="group w-full rounded-xl border border-gray-200 bg-white p-6 text-left transition-all hover:border-primary-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-primary-600"
          >
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300">
                <span className="text-sm font-bold">{i + 1}</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 dark:text-white">{step.title}</h3>
                  <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-primary-600 dark:text-gray-500" />
                </div>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{step.description}</p>
                <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary-600 dark:text-primary-400">
                  {step.cta}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
        <div className="flex gap-3">
          <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0" />
          <div className="text-sm text-green-700 dark:text-green-300">
            <p className="font-medium">Tips</p>
            <p className="mt-1">
              Setelah menyelesaikan ketiga langkah, Anda bisa menjelajahi fitur lain seperti
              A/B Testing, Monitoring, dan Marketplace.
            </p>
          </div>
        </div>
      </div>

      <button
        onClick={() => router.push('/')}
        className="w-full text-center text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        Lewati, saya akan menjelajahi sendiri
      </button>
    </div>
  );
}
