import clsx from 'clsx';

type StatusType = 'success' | 'warning' | 'error' | 'info' | 'neutral';

const statusStyles: Record<StatusType, string> = {
  success: 'bg-green-50 text-green-700 ring-green-600/20',
  warning: 'bg-yellow-50 text-yellow-700 ring-yellow-600/20',
  error: 'bg-red-50 text-red-700 ring-red-600/20',
  info: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  neutral: 'bg-gray-50 text-gray-700 ring-gray-600/20',
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
