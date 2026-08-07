'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { ChevronRight, Home } from 'lucide-react';

// ── Human-readable route labels ──────────────────────────────────────────────
const ROUTE_LABELS: Record<string, string> = {
  'training-wizard':    'Training Wizard',
  'datasets':           'Dataset',
  'models':             'Model',
  'model-versions':     'Versi Model',
  'experiments':        'Eksperimen',
  'experiment-compare': 'Perbandingan',
  'predictions':        'Prediksi',
  'marketplace':        'Marketplace',
  'serving':            'Serving',
  'monitoring':         'Monitoring',
  'ab-tests':           'A/B Testing',
  'batch-jobs':         'Batch Job',
  'feature-store':      'Feature Store',
  'feature-monitoring': 'Monitoring Fitur',
  'explain':            'Explainability',
  'ensemble':           'Ensemble',
  'mlflow':             'MLflow',
  'benchmark':          'Benchmark',
  'data-quality':       'Kualitas Data',
  'data-validation':    'Validasi Data',
  'audit-logs':         'Log Audit',
  'organizations':      'Organisasi',
  'quota':              'Kuota API',
  'costs':              'Biaya',
  'webhooks':           'Webhook',
  'settings':           'Pengaturan',
  'privacy':            'Kebijakan Privasi',
  'panduan-algoritma':  'Panduan Algoritma',
  'profile':            'Profil',
  'trash':              'Sampah',
  'automl':             'AutoML',
};

function labelForSegment(segment: string): string {
  return ROUTE_LABELS[segment]
    ?? segment.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function isUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s);
}

export default function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  // Don't render on root dashboard
  if (segments.length === 0) return null;

  // Build crumb list
  const crumbs: { label: string; href: string }[] = [
    { label: 'Dasbor', href: '/' },
  ];

  let cumPath = '';
  segments.forEach((seg) => {
    cumPath += `/${seg}`;
    // Skip UUIDs — show as "Detail" with parent's context
    if (isUuid(seg)) {
      crumbs.push({ label: 'Detail', href: cumPath });
    } else {
      crumbs.push({ label: labelForSegment(seg), href: cumPath });
    }
  });

  // Only show if there's something beyond the dashboard root
  if (crumbs.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <span key={crumb.href} className="flex items-center gap-1">
            {i === 0 ? (
              <Link
                href={crumb.href}
                className="flex items-center gap-1 text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200"
              >
                <Home className="h-3.5 w-3.5" />
              </Link>
            ) : isLast ? (
              <span className="font-medium text-gray-700 dark:text-gray-200">{crumb.label}</span>
            ) : (
              <Link
                href={crumb.href}
                className="text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200"
              >
                {crumb.label}
              </Link>
            )}
            {!isLast && <ChevronRight className="h-3.5 w-3.5 text-gray-300 dark:text-gray-600" />}
          </span>
        );
      })}
    </nav>
  );
}
