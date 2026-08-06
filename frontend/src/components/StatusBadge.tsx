import clsx from 'clsx';

type StatusType = 'success' | 'warning' | 'error' | 'info' | 'neutral';

const statusStyles: Record<StatusType, string> = {
  success: 'bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-900/30 dark:text-green-300 dark:ring-green-500/30',
  warning: 'bg-yellow-50 text-yellow-700 ring-yellow-600/20 dark:bg-yellow-900/30 dark:text-yellow-300 dark:ring-yellow-500/30',
  error: 'bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-500/30',
  info: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-900/30 dark:text-blue-300 dark:ring-blue-500/30',
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
