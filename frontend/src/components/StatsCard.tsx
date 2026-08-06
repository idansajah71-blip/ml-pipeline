import { LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface StatsCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  iconColor?: string;
}

export default function StatsCard({
  title,
  value,
  icon: Icon,
  change,
  changeType = 'neutral',
  iconColor = 'text-primary-600',
}: StatsCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">{value}</p>
          {change && (
            <p
              className={clsx(
                'mt-1 text-sm',
                changeType === 'positive' && 'text-green-600 dark:text-green-400',
                changeType === 'negative' && 'text-red-600 dark:text-red-400',
                changeType === 'neutral' && 'text-gray-500 dark:text-gray-400'
              )}
            >
              {change}
            </p>
          )}
        </div>
        <div className={clsx('rounded-lg bg-gray-50 p-3 dark:bg-gray-700', iconColor)}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}
