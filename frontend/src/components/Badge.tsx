import clsx from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}

const variantStyles = {
  default: 'bg-gray-50 text-gray-700 ring-gray-600/20 dark:bg-gray-700 dark:text-gray-300 dark:ring-gray-500/30',
  success: 'bg-success-50 text-success-700 ring-success-600/20 dark:bg-success-900/30 dark:text-success-300 dark:ring-success-500/30',
  warning: 'bg-warning-50 text-warning-700 ring-warning-600/20 dark:bg-warning-900/30 dark:text-warning-300 dark:ring-warning-500/30',
  danger: 'bg-error-50 text-error-700 ring-error-600/20 dark:bg-error-900/30 dark:text-error-300 dark:ring-error-500/30',
  info: 'bg-info-50 text-info-700 ring-info-600/20 dark:bg-info-900/30 dark:text-info-300 dark:ring-info-500/30',
};

export default function Badge({ children, variant = 'default', size = 'sm' }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium ring-1 ring-inset',
        variantStyles[variant],
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      )}
    >
      {children}
    </span>
  );
}
