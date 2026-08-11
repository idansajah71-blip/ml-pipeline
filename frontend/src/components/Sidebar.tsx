'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Database,
  Brain,
  Zap,
  FlaskConical,
  BarChart3,
  LogOut,
  Settings,
  UserCircle,
  Menu,
  X,
  Shield,
  Layers,
  History,
  Store,
  Rocket,
  Users,
  GitBranch,
  ArrowRightLeft,
  Activity,
  Bell,
  PieChart,
  Blend,
  DollarSign,
  Wand2,
  Gauge,
  LineChart,
  FileCheck,
  AlertTriangle,
  Globe,
  Sparkles,
  ChevronDown,
  Search,
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
}

interface NavGroup {
  name: string;
  items: NavItem[];
}

type NavEntry = NavItem | NavGroup;

function isGroup(entry: NavEntry): entry is NavGroup {
  return 'items' in entry;
}

// ── New Information Architecture ──────────────────────────────────────────────
// Organized by ML lifecycle: Data → Experiment → Train → Evaluate → Register → Deploy → Predict → Monitor

const navigation: NavEntry[] = [
  // ── PRIMARY: Core workspace ──
  { name: 'Dasbor', href: '/', icon: LayoutDashboard, tour: 'dashboard' },

  // ── WORKSPACE: Main ML lifecycle ──
  {
    name: 'Workspace',
    items: [
      { name: 'Data', href: '/datasets', icon: Database, tour: 'datasets' },
      { name: 'Experiments', href: '/experiments', icon: FlaskConical, tour: 'experiments' },
      { name: 'Models', href: '/models', icon: Brain, tour: 'models' },
      { name: 'Predictions', href: '/predictions', icon: Zap },
      { name: 'Deployments', href: '/serving', icon: Rocket },
      { name: 'Monitoring', href: '/monitoring', icon: Activity },
    ],
  },

  // ── ML TOOLS: Specialized capabilities ──
  {
    name: 'ML Tools',
    items: [
      { name: 'Training Wizard', href: '/training-wizard', icon: Wand2, tour: 'wizard' },
      { name: 'Marketplace', href: '/marketplace', icon: Store },
      { name: 'External Data', href: '/data-explorer', icon: Search },
      { name: 'Web Scraping', href: '/scraping', icon: Globe },
    ],
  },

  // ── INTEGRATIONS: External services ──
  {
    name: 'Integrations',
    items: [
      { name: 'MLflow', href: '/mlflow', icon: LineChart },
      { name: 'Feature Store', href: '/feature-store', icon: Layers },
      { name: 'Webhooks', href: '/webhooks', icon: Bell },
    ],
  },

  // ── ORGANIZATION: Team & usage ──
  {
    name: 'Organization',
    items: [
      { name: 'Team', href: '/organizations', icon: Users },
      { name: 'Usage & API', href: '/quota', icon: Gauge },
      { name: 'Costs', href: '/costs', icon: DollarSign },
    ],
  },

  // ── SYSTEM: Admin & config ──
  {
    name: 'System',
    items: [
      { name: 'Audit Logs', href: '/audit-logs', icon: History },
      { name: 'Health', href: '/system-health', icon: AlertTriangle },
      { name: 'Settings', href: '/settings', icon: Settings },
    ],
  },
];

// ── Helper: check if any item in group is active ─────────────────────────────

function isGroupActive(group: NavGroup, pathname: string): boolean {
  return group.items.some((item) => pathname === item.href || pathname.startsWith(item.href + '/'));
}

// ── Sidebar Component ────────────────────────────────────────────────────────

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  const toggleGroup = useCallback((name: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [name]: !prev[name] }));
  }, []);

  const isActive = (href: string) =>
    pathname === href || (href !== '/' && pathname.startsWith(href + '/'));

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
        {navigation.map((entry) => {
          // ── Single item (Dasbor) ──
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
          const collapsed = collapsedGroups[group.name] ?? false;
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
                    return (
                      <Link
                        key={item.name}
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
                        <span>{item.name}</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

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
