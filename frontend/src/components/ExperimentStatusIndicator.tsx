'use client';

import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import clsx from 'clsx';

interface ExperimentStatusIndicatorProps {
  status: 'pending' | 'running' | 'completed' | 'failed';
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  pollInterval?: number;
}

const statusConfig = {
  pending: {
    icon: Clock,
    label: 'Pending',
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    dot: 'bg-yellow-400',
  },
  running: {
    icon: Loader2,
    label: 'Running',
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    dot: 'bg-blue-400',
  },
  completed: {
    icon: CheckCircle,
    label: 'Completed',
    color: 'text-green-600',
    bg: 'bg-green-50',
    dot: 'bg-green-400',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    color: 'text-red-600',
    bg: 'bg-red-50',
    dot: 'bg-red-400',
  },
};

export default function ExperimentStatusIndicator({
  status,
  showLabel = true,
  size = 'md',
  pollInterval,
}: ExperimentStatusIndicatorProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  const dotSizeClasses = {
    sm: 'h-1.5 w-1.5',
    md: 'h-2 w-2',
    lg: 'h-2.5 w-2.5',
  };

  return (
    <div className={clsx('inline-flex items-center gap-2 rounded-full px-3 py-1.5', config.bg)}>
      <span className="relative flex items-center">
        <span className={clsx('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', config.dot, status !== 'running' && 'hidden')} />
        <span className={clsx('relative inline-flex rounded-full', dotSizeClasses[size], config.dot)} />
      </span>
      <Icon
        className={clsx(
          sizeClasses[size],
          config.color,
          status === 'running' && 'animate-spin'
        )}
      />
      {showLabel && (
        <span className={clsx('text-sm font-medium', config.color)}>
          {config.label}
        </span>
      )}
    </div>
  );
}
