import clsx from 'clsx';

type StatusType = 'success' | 'warning' | 'error' | 'info' | 'neutral';

const statusStyles: Record<StatusType, string> = {
  // WCAG AA compliant: 4.5:1 contrast ratio on both light/dark backgrounds
  success: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-900/30 dark:text-success-300 dark:ring-success-500/30',
  warning: 'bg-warning-50 text-warning-700 ring-warning-600/20 dark:bg-warning-900/30 dark:text-warning-300 dark:ring-warning-500/30',
  error: 'bg-error-50 text-error-700 ring-error-600/20 dark:bg-error-900/30 dark:text-error-300 dark:ring-error-500/30',
  info: 'bg-info-50 text-info-700 ring-info-600/20 dark:bg-info-900/30 dark:text-info-300 dark:ring-info-500/30',
  neutral: 'bg-gray-50 text-gray-700 ring-gray-600/20 dark:bg-gray-700 dark:text-gray-300 dark:ring-gray-500/30',
};

function getStatusType(status: string): StatusType {
  const s = status.toLowerCase();
  if (['deployed', 'completed', 'success', 'active'].includes(s)) return 'success';
  if (['training', 'running', 'pending', 'draft'].includes(s)) return 'warning';
  if (['failed', 'error', 'archived'].includes(s)) return 'error';
  if (['trained', 'paused'].includes(s)) return 'info';
  return 'neutral';
}

export default function StatusBadge({ status }: { status: string }) {
  const type = getStatusType(status);
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        statusStyles[type]
      )}
    >
      {status}
    </span>
  );
}
