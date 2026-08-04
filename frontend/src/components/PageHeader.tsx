'use client';

import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import clsx from 'clsx';

interface Breadcrumb {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  breadcrumbs?: Breadcrumb[];
  badge?: { label: string; color?: string };
}

export default function PageHeader({ title, description, action, breadcrumbs, badge }: PageHeaderProps) {
  return (
    <div className="space-y-1">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-sm text-gray-500">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3" />}
              {crumb.href ? (
                <Link href={crumb.href} className="hover:text-gray-700">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-gray-900">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {badge && (
            <span
              className={clsx(
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                badge.color || 'bg-gray-100 text-gray-800'
              )}
            >
              {badge.label}
            </span>
          )}
        </div>
        {action}
      </div>
      {description && <p className="text-gray-500">{description}</p>}
    </div>
  );
}
