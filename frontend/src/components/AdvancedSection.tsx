'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Settings2 } from 'lucide-react';

interface AdvancedSectionProps {
  label?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

/**
 * Progressive disclosure wrapper.
 * Wraps technical/advanced options behind a collapsible toggle.
 * Collapsed by default to keep the UI clean for beginners.
 */
export default function AdvancedSection({
  label = 'Pengaturan Lanjutan',
  children,
  defaultOpen = false,
  className = '',
}: AdvancedSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`rounded-xl border border-gray-200 dark:border-gray-700 ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          <Settings2 className="h-4 w-4 text-gray-400" />
          {label}
        </span>
        {open
          ? <ChevronUp className="h-4 w-4 text-gray-400" />
          : <ChevronDown className="h-4 w-4 text-gray-400" />}
      </button>

      {open && (
        <div className="border-t border-gray-200 px-4 py-4 dark:border-gray-700">
          {children}
        </div>
      )}
    </div>
  );
}
