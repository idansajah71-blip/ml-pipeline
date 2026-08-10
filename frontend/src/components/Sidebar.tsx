'use client';

import { useState } from 'react';
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
  BarChart,
  Search,
  Globe,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import ThemeToggle from '@/components/ThemeToggle';
import NotificationBell from '@/components/NotificationBell';
import clsx from 'clsx';

const navigation = [
  { name: 'Dasbor', href: '/', icon: LayoutDashboard, tour: 'dashboard' },
  { name: 'Training Wizard', href: '/training-wizard', icon: Wand2, tour: 'wizard' },
  { name: 'Cari Data Online', href: '/data-explorer', icon: Search },
  { name: 'Web Scraping', href: '/scraping', icon: Globe },
  { name: 'Dataset', href: '/datasets', icon: Database, tour: 'datasets' },
  { name: 'Model', href: '/models', icon: Brain, tour: 'models' },
  { name: 'Versi Model', href: '/model-versions', icon: GitBranch },
  { name: 'Ensemble', href: '/ensemble', icon: Blend },
  { name: 'Explainability', href: '/explain', icon: PieChart },
  { name: 'Eksperimen', href: '/experiments', icon: FlaskConical, tour: 'experiments' },
  { name: 'Perbandingan', href: '/experiment-compare', icon: ArrowRightLeft },
  { name: 'Marketplace', href: '/marketplace', icon: Store },
  { name: 'Prediksi', href: '/predictions', icon: Zap },
  { name: 'Coba Prediksi', href: '/try-predict', icon: Sparkles },
  { name: 'A/B Testing', href: '/ab-tests', icon: BarChart3 },
  { name: 'Kualitas Data', href: '/data-quality', icon: Shield },
  { name: 'Batch Job', href: '/batch-jobs', icon: Layers },
  { name: 'Feature Store', href: '/feature-store', icon: Store },
  { name: 'Monitoring Fitur', href: '/feature-monitoring', icon: Activity },
  { name: 'Serving', href: '/serving', icon: Rocket },
  { name: 'Webhook', href: '/webhooks', icon: Bell },
  { name: 'Organisasi', href: '/organizations', icon: Users },
  { name: 'Biaya', href: '/costs', icon: DollarSign },
  { name: 'Kuota API', href: '/quota', icon: Gauge },
  { name: 'MLflow', href: '/mlflow', icon: LineChart },
  { name: 'Benchmark', href: '/benchmark', icon: BarChart },
  { name: 'Panduan Algoritma', href: '/panduan-algoritma', icon: Wand2 },
  { name: 'Validasi Data', href: '/data-validation', icon: FileCheck },
  { name: 'Kesehatan Sistem', href: '/system-health', icon: Activity },
  { name: 'Monitoring', href: '/monitoring', icon: Settings },
  { name: 'Log Audit', href: '/audit-logs', icon: History },
  { name: 'Kebijakan Privasi', href: '/privacy', icon: Shield },
  { name: 'Pengaturan', href: '/settings', icon: UserCircle },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const SidebarContent = () => (
    <>
      <div className="flex h-16 items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6">
        <div className="flex items-center gap-2">
          <Brain className="h-8 w-8 text-primary-600" />
          <span className="text-xl font-bold text-gray-900 dark:text-white">ML Pipeline</span>
        </div>
        <div className="flex items-center gap-2">
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

      <nav className="space-y-1 px-3 py-4" aria-label="Navigasi utama">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'
              )}
            >
              <item.icon className={clsx('h-5 w-5', isActive ? 'text-primary-600' : 'text-gray-400 dark:text-gray-500')} />
              <span data-tour={item.tour}>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-0 left-0 right-0 border-t border-gray-200 dark:border-gray-700 p-4">
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
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-50 rounded-lg bg-white dark:bg-gray-800 p-2 shadow-md lg:hidden min-h-[44px] min-w-[44px] flex items-center justify-center"
        aria-label="Buka menu navigasi"
        aria-expanded={mobileOpen}
      >
        <Menu className="h-5 w-5 text-gray-600 dark:text-gray-400" />
      </button>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={clsx(
          'fixed left-0 top-0 z-40 h-screen w-64 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 transition-transform lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <SidebarContent />
      </aside>
    </>
  );
}
