'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { ChevronRight, Home } from 'lucide-react';

// ── Route → human-readable label ─────────────────────────────────────────────
const ROUTE_LABELS: Record<string, string> = {
  // Top-level routes
  'datasets':           'Data',
  'models':             'Models',
  'experiments':        'Experiments',
  'predictions':        'Predictions',
  'serving':            'Deployments',
  'monitoring':         'Monitoring',

  // Data sub-features
  'data-quality':       'Quality',
  'data-validation':    'Validation',
  'data-explorer':      'Online Data',
  'data-versions':      'Versions',

  // Model sub-features
  'model-versions':     'Versions',
  'ensemble':           'Ensemble',
  'explain':            'Explainability',
  'benchmark':          'Benchmark',

  // Experiment sub-features
  'experiment-compare': 'Comparison',

  // Prediction sub-features
  'try-predict':        'Playground',
  'batch-jobs':         'Batch Jobs',

  // Deployment sub-features
  'ab-tests':           'A/B Testing',
  'ab-testing':         'A/B Testing',

  // Monitoring sub-features
  'feature-monitoring': 'Feature Drift',
  'system-health':      'System Health',

  // ML Tools
  'training-wizard':    'Train Model',
  'panduan-algoritma':  'Algorithm Guide',

  // Data Sources
  'scraping':           'Web Scraping',

  // Integrations
  'mlflow':             'MLflow',
  'feature-store':      'Feature Store',
  'webhooks':           'Webhooks',

  // Explore
  'marketplace':        'Marketplace',

  // Organization
  'organizations':      'Team',
  'quota':              'API & Quota',
  'costs':              'Costs',

  // System
  'audit-logs':         'Audit Logs',
  'settings':           'Settings',
  'privacy':            'Privacy',
  'profile':            'Profile',
  'trash':              'Trash',
};

// ── Route → parent group label (for breadcrumb context) ──────────────────────
// Maps sub-pages to their parent group in the new IA

const PARENT_MAP: Record<string, string> = {
  'data-quality':       'Data',
  'data-validation':    'Data',
  'data-versions':      'Data',
  'model-versions':     'Models',
  'ensemble':           'Models',
  'explain':            'Models',
  'benchmark':          'Models',
  'experiment-compare': 'Experiments',
  'try-predict':        'Predictions',
  'batch-jobs':         'Predictions',
  'ab-tests':           'Deployments',
  'ab-testing':         'Deployments',
  'feature-monitoring': 'Monitoring',
};

// ── Top-level routes that belong to a group (for hiding redundant crumbs) ────
// If a route IS the parent (e.g. /datasets = "Data"), we skip adding the group label

const GROUP_ROUTES: Record<string, string> = {
  'datasets': 'Data',
  'models': 'Models',
  'experiments': 'Experiments',
  'predictions': 'Predictions',
  'serving': 'Deployments',
  'monitoring': 'Monitoring',
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
    { label: 'Dashboard', href: '/' },
  ];

  let cumPath = '';
  segments.forEach((seg) => {
    cumPath += `/${seg}`;

    // Skip UUIDs — show as "Detail" with parent's context
    if (isUuid(seg)) {
      crumbs.push({ label: 'Detail', href: cumPath });
      return;
    }

    const parentGroup = PARENT_MAP[seg];
    if (parentGroup) {
      // This is a sub-page — find the parent route and add group label
      const parentRoute = Object.entries(GROUP_ROUTES).find(([, name]) => name === parentGroup);
      if (parentRoute) {
        crumbs.push({ label: parentGroup, href: `/${parentRoute[0]}` });
      }
    }

    crumbs.push({ label: labelForSegment(seg), href: cumPath });
  });

  // Only show if there's something beyond the dashboard root
  if (crumbs.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1;
        return (
          <span key={`${crumb.href}-${i}`} className="flex items-center gap-1">
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
