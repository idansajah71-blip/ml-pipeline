'use client';

import { useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Database,
  Brain,
  FlaskConical,
  Zap,
  Rocket,
  Activity,
  Wand2,
  Globe,
  Store,
  Search,
  LineChart,
  Layers,
  Bell,
  Users,
  DollarSign,
  Gauge,
  History,
  AlertTriangle,
  Settings,
  LogOut,
  Shield,
  Menu,
  X,
  ChevronDown,
  BarChart3,
  Blend,
  FileCheck,
  Target,
  TestTube2,
  Workflow,
  Cpu,
  RefreshCw,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import ThemeToggle from '@/components/ThemeToggle';
import NotificationBell from '@/components/NotificationBell';
import clsx from 'clsx';

// ── Navigation item types ────────────────────────────────────────────────────

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  tour?: string;
  tooltip?: string;
}

interface NavGroup {
  name: string;
  items: NavItem[];
}

type NavEntry = NavItem | NavGroup;

function isGroup(entry: NavEntry): entry is NavGroup {
  return 'items' in entry;
}

// ── Information Architecture ──────────────────────────────────────────────────
// ML Lifecycle: Data → Train → Experiment → Evaluate → Model → Deploy → Predict → Monitor
//
// OLD → NEW mapping (no routes removed, only navigation reorganized):
//
// WORKSPACE:
//   Dasbor         → /                     (top-level)
//   Dataset         → /datasets             → Workspace > Data
//   Data Quality    → /data-quality         → Workspace > Data (sub)
//   Data Validation → /data-validation      → Workspace > Data (sub)
//   Experiments     → /experiments          → Workspace > Experiments
//   Compare         → /experiment-compare   → Workspace > Experiments (sub)
//   Models          → /models               → Workspace > Models
//   Model Versions  → /model-versions       → Workspace > Models (sub)
//   Ensemble        → /ensemble             → Workspace > Models (sub)
//   Explain         → /explain              → Workspace > Models (sub)
//   Benchmark       → /benchmark            → Workspace > Models (sub)
//   Predictions     → /predictions          → Workspace > Predictions
//   Try Predict     → /try-predict          → Workspace > Predictions (sub)
//   Batch Jobs      → /batch-jobs           → Workspace > Predictions (sub)
//   Serving         → /serving              → Workspace > Deployments
//   A/B Testing     → /ab-tests             → Workspace > Deployments (sub)
//   Monitoring      → /monitoring           → Workspace > Monitoring
//   Feature Monit.  → /feature-monitoring   → Workspace > Monitoring (sub)
//
// ML TOOLS:
//   Training Wizard → /training-wizard      → ML Tools > Train Model
//   Panduan Algo    → /panduan-algoritma     → ML Tools > Algorithm Guide
//
// DATA SOURCES:
//   Data Explorer   → /data-explorer        → Data Sources > Online Data
//   Web Scraping    → /scraping             → Data Sources > Web Scraping
//
// INTEGRATIONS:
//   MLflow          → /mlflow               → Integrations > MLflow
//   Feature Store   → /feature-store        → Integrations > Feature Store
//   Webhooks        → /webhooks             → Integrations > Webhooks
//
// EXPLORE:
//   Marketplace     → /marketplace          → Explore > Marketplace
//
// ORGANIZATION:
//   Organizations   → /organizations        → Organization > Team
//   Costs           → /costs                → Organization > Costs
//   Quota API       → /quota                → Organization > API & Quota
//
// SYSTEM:
//   Audit Logs      → /audit-logs           → System > Audit Logs
//   System Health   → /system-health        → System > Health
//   Privacy         → /privacy              → System > Privacy
//   Settings        → /settings             → System > Settings

const navigation: NavEntry[] = [
  // ── TOP-LEVEL: Dashboard ──
  { name: 'Dashboard', href: '/', icon: LayoutDashboard, tour: 'dashboard' },

  // ── WORKSPACE: Core ML lifecycle ──
  {
    name: 'Workspace',
    items: [
      {
        name: 'Data',
        href: '/datasets',
        icon: Database,
        tour: 'datasets',
      },
      {
        name: 'Models',
        href: '/models',
        icon: Brain,
        tour: 'models',
      },
      {
        name: 'Experiments',
        href: '/experiments',
        icon: FlaskConical,
        tour: 'experiments',
      },
      {
        name: 'Predictions',
        href: '/predictions',
        icon: Zap,
      },
      {
        name: 'Deployments',
        href: '/serving',
        icon: Rocket,
        tooltip: 'Mengaktifkan model agar bisa dipakai dari luar (production)',
      },
      {
        name: 'Monitoring',
        href: '/monitoring',
        icon: Activity,
        tooltip: 'Memantau apakah data nyata mulai berbeda dari data training (drift)',
      },
    ],
  },

  // ── ML TOOLS: Specialized capabilities ──
  {
    name: 'ML Tools',
    items: [
      { name: 'Auto Mode', href: '/auto-mode', icon: Zap, tooltip: 'Mode otomatis: upload data, sistem pandu semua' },
      { name: 'Train Model', href: '/training-wizard', icon: Wand2, tour: 'wizard' },
      { name: 'Algorithm Guide', href: '/panduan-algoritma', icon: FileCheck, tooltip: 'Panduan memilih algoritma ML yang tepat untuk data Anda' },
    ],
  },

  // ── DATA SOURCES: External data acquisition ──
  {
    name: 'Data Sources',
    items: [
      { name: 'Online Data', href: '/data-explorer', icon: Search },
      { name: 'Web Scraping', href: '/scraping', icon: Globe },
    ],
  },

  // ── INTEGRATIONS: External services ──
  {
    name: 'Integrations',
    items: [
      { name: 'MLflow', href: '/mlflow', icon: LineChart, tooltip: 'Tools eksternal untuk mencatat dan membandingkan eksperimen ML' },
      { name: 'Feature Store', href: '/feature-store', icon: Layers, tooltip: 'Tempat menyimpan fitur data yang sudah diproses agar bisa dipakai ulang' },
      { name: 'Webhooks', href: '/webhooks', icon: Bell },
    ],
  },

  // ── EXPLORE: Discovery & community ──
  {
    name: 'Explore',
    items: [
      { name: 'Marketplace', href: '/marketplace', icon: Store },
    ],
  },

  // ── ORGANIZATION: Team & usage ──
  {
    name: 'Organization',
    items: [
      { name: 'Team', href: '/organizations', icon: Users },
      { name: 'Costs', href: '/costs', icon: DollarSign },
      { name: 'API & Quota', href: '/quota', icon: Gauge },
    ],
  },

  // ── SYSTEM: Admin & config ──
  {
    name: 'System',
    items: [
      { name: 'Audit Logs', href: '/audit-logs', icon: History },
      { name: 'Health', href: '/system-health', icon: AlertTriangle },
      { name: 'Privacy', href: '/privacy', icon: Shield },
      { name: 'Settings', href: '/settings', icon: Settings },
    ],
  },
];

// ── Sub-navigation for nested pages ──────────────────────────────────────────
// Maps a parent route to its child pages. When a child route is active,
// the parent is considered active and expanded.

const SUB_NAV: Record<string, { label: string; href: string }[]> = {
  '/datasets': [
    { label: 'Overview', href: '/datasets' },
    { label: 'Quality', href: '/data-quality' },
    { label: 'Validation', href: '/data-validation' },
  ],
  '/models': [
    { label: 'Overview', href: '/models' },
    { label: 'Versions', href: '/model-versions' },
    { label: 'Ensemble', href: '/ensemble' },
    { label: 'Explainability', href: '/explain' },
    { label: 'Benchmark', href: '/benchmark' },
  ],
  '/experiments': [
    { label: 'Overview', href: '/experiments' },
    { label: 'Comparison', href: '/experiment-compare' },
  ],
  '/predictions': [
    { label: 'Overview', href: '/predictions' },
    { label: 'Playground', href: '/try-predict' },
    { label: 'Batch Jobs', href: '/batch-jobs' },
  ],
  '/serving': [
    { label: 'Overview', href: '/serving' },
    { label: 'A/B Testing', href: '/ab-tests' },
  ],
  '/monitoring': [
    { label: 'Overview', href: '/monitoring' },
    { label: 'Feature Drift', href: '/feature-monitoring' },
  ],
};

// ── Helper: check if route matches (exact or prefix) ─────────────────────────

function routeMatch(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(href + '/');
}

// ── Helper: check if any item in group is active ─────────────────────────────

function isGroupActive(group: NavGroup, pathname: string): boolean {
  return group.items.some((item) => {
    if (routeMatch(pathname, item.href)) return true;
    // Also check sub-navigation children
    const subs = SUB_NAV[item.href];
    if (subs) {
      return subs.some((sub) => routeMatch(pathname, sub.href));
    }
    return false;
  });
}

// ── Helper: find which sub-nav item is active ────────────────────────────────

function findActiveSub(parentHref: string, pathname: string): string | null {
  const subs = SUB_NAV[parentHref];
  if (!subs) return null;
  for (const sub of subs) {
    if (routeMatch(pathname, sub.href)) return sub.href;
  }
  return null;
}

// ── Helper: auto-expand groups that contain active route ─────────────────────

function getInitialCollapsedgroups(pathname: string): Record<string, boolean> {
  const result: Record<string, boolean> = {};
  for (const entry of navigation) {
    if (isGroup(entry)) {
      const active = isGroupActive(entry, pathname);
      result[entry.name] = !active;
    }
  }
  return result;
}

// ── Sidebar Component ────────────────────────────────────────────────────────

const ADVANCED_GROUPS = ['Integrations', 'Explore', 'Organization', 'System'];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [showAdvanced, setShowAdvanced] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('sidebar_advanced') === 'true';
    }
    return false;
  });

  const toggleAdvanced = useCallback(() => {
    setShowAdvanced((prev) => {
      const next = !prev;
      localStorage.setItem('sidebar_advanced', String(next));
      return next;
    });
  }, []);

  // Auto-expand groups when route changes
  useEffect(() => {
    setCollapsedGroups((prev) => {
      const next = { ...prev };
      for (const entry of navigation) {
        if (isGroup(entry)) {
          const active = isGroupActive(entry, pathname);
          if (active) next[entry.name] = false;
        }
      }
      return next;
    });
  }, [pathname]);

  const toggleGroup = useCallback((name: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [name]: !prev[name] }));
  }, []);

  const isActive = (href: string) => routeMatch(pathname, href);

  const SidebarContent = () => (
    <>
      {/* ── Logo & Controls ── */}
      <div className="flex h-16 items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6">
        <Link href="/" className="flex items-center gap-2">
          <Brain className="h-8 w-8 text-primary-600" />
          <span className="text-xl font-bold text-gray-900 dark:text-white">ML Pipeline</span>
        </Link>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <NotificationBell />
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 p-2 rounded-lg min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Tutup menu navigasi"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1" aria-label="Navigasi utama">
        {navigation
          .filter((entry) => {
            if (!isGroup(entry)) return true;
            if (ADVANCED_GROUPS.includes(entry.name) && !showAdvanced) return false;
            return true;
          })
          .map((entry) => {
          // ── Single item (Dashboard) ──
          if (!isGroup(entry)) {
            const active = isActive(entry.href);
            return (
              <Link
                key={entry.name}
                href={entry.href}
                onClick={() => setMobileOpen(false)}
                className={clsx(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  active
                    ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
                )}
              >
                <entry.icon className={clsx('h-5 w-5', active ? 'text-primary-600' : 'text-gray-400 dark:text-gray-500')} />
                <span data-tour={entry.tour}>{entry.name}</span>
              </Link>
            );
          }

          // ── Collapsible group ──
          const group = entry as NavGroup;
          const collapsed = collapsedGroups[group.name] ?? true;
          const groupActive = isGroupActive(group, pathname);

          return (
            <div key={group.name} className="pt-2">
              {/* Group header */}
              <button
                onClick={() => toggleGroup(group.name)}
                className={clsx(
                  'flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors',
                  groupActive
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300'
                )}
              >
                <span>{group.name}</span>
                <ChevronDown
                  className={clsx(
                    'h-3.5 w-3.5 transition-transform duration-200',
                    collapsed && '-rotate-90'
                  )}
                />
              </button>

              {/* Group items */}
              {!collapsed && (
                <div className="mt-0.5 space-y-0.5">
                  {group.items.map((item) => {
                    const active = isActive(item.href);
                    const activeSub = findActiveSub(item.href, pathname);
                    const hasSubNav = SUB_NAV[item.href];

                    return (
                      <div key={item.name}>
                        <Link
                          href={item.href}
                          onClick={() => setMobileOpen(false)}
                          className={clsx(
                            'flex items-center gap-3 rounded-lg py-2 pl-9 pr-3 text-sm font-medium transition-colors',
                            active
                              ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
                          )}
                        >
                          <item.icon className={clsx('h-4 w-4', active ? 'text-primary-600' : 'text-gray-400 dark:text-gray-500')} />
                          <span title={item.tooltip}>{item.name}</span>
                        </Link>

                        {/* Sub-navigation (shown when parent is active and has sub-pages) */}
                        {active && hasSubNav && (
                          <div className="ml-9 mt-0.5 space-y-0.5 border-l border-gray-200 dark:border-gray-700 pl-3">
                            {SUB_NAV[item.href].map((sub) => {
                              const subActive = routeMatch(pathname, sub.href);
                              return (
                                <Link
                                  key={sub.href}
                                  href={sub.href}
                                  onClick={() => setMobileOpen(false)}
                                  className={clsx(
                                    'flex items-center rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                                    subActive
                                      ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                                  )}
                                >
                                  {sub.label}
                                </Link>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* ── Advanced Mode Toggle ── */}
      <div className="px-3 pb-2">
        <button
          onClick={toggleAdvanced}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          <ChevronDown className={clsx('h-3.5 w-3.5 transition-transform', !showAdvanced && '-rotate-90')} />
          {showAdvanced ? 'Sembunyikan fitur lanjutan' : 'Tampilkan fitur lanjutan'}
        </button>
      </div>

      {/* ── User & Logout ── */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900/50 text-sm font-medium text-primary-700 dark:text-primary-300">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 truncate">
            <p className="truncate text-sm font-medium text-gray-900 dark:text-white">{user?.full_name || user?.username}</p>
            <p className="truncate text-xs text-gray-500 dark:text-gray-400">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 min-h-[44px]"
          aria-label="Keluar dari akun"
        >
          <LogOut className="h-4 w-4" />
          Keluar
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-50 rounded-lg bg-white dark:bg-gray-800 p-2 shadow-md lg:hidden min-h-[44px] min-w-[44px] flex items-center justify-center"
        aria-label="Buka menu navigasi"
        aria-expanded={mobileOpen}
      >
        <Menu className="h-5 w-5 text-gray-600 dark:text-gray-400" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed left-0 top-0 z-40 h-screen w-64 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 transition-transform lg:translate-x-0 flex flex-col',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <SidebarContent />
      </aside>
    </>
  );
}
