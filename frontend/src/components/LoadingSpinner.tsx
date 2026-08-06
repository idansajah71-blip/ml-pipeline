import clsx from 'clsx';

export default function LoadingSpinner({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  return (
    <div
      className={clsx(
        'animate-spin rounded-full border-2 border-gray-300 border-t-primary-600 dark:border-gray-600 dark:border-t-primary-500',
        size === 'sm' && 'h-4 w-4',
        size === 'md' && 'h-8 w-8',
        size === 'lg' && 'h-12 w-12',
        className
      )}
    />
  );
}
