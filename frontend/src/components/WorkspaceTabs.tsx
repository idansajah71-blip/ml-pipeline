'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';

export interface Tab {
  label: string;
  href: string;
  icon?: LucideIcon;
}

interface WorkspaceTabsProps {
  tabs: Tab[];
  title: string;
  description?: string;
}

export default function WorkspaceTabs({ tabs, title, description }: WorkspaceTabsProps) {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
        {description && (
          <p className="text-gray-500 dark:text-gray-400">{description}</p>
        )}
      </div>

      {/* Tab bar */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex gap-6 overflow-x-auto" aria-label="Tabs">
          {tabs.map((tab) => {
            const isActive = pathname === tab.href || pathname.startsWith(tab.href + '/');
            const Icon = tab.icon;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={clsx(
                  'flex items-center gap-2 whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition-colors',
                  isActive
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
                )}
              >
                {Icon && <Icon className="h-4 w-4" />}
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
