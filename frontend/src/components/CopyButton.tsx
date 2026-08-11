'use client';

import { useState, useRef, useEffect } from 'react';
import { Copy, Check } from 'lucide-react';
import clsx from 'clsx';

interface CopyButtonProps {
  text: string;
  className?: string;
  label?: string;
}

export default function CopyButton({ text, className, label }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
        copied
          ? 'bg-green-50 text-green-700'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200',
        className
      )}
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5" />
          {label || 'Copied!'}
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          {label || 'Copy'}
        </>
      )}
    </button>
  );
}
