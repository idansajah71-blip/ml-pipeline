'use client';

import { useState, useRef, Children, cloneElement, isValidElement, ReactNode, KeyboardEvent, FocusEvent } from 'react';
import clsx from 'clsx';

interface TooltipProps {
  content: string;
  children: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
}

const positionStyles = {
  top: 'bottom-full left-1/2 mb-2 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-2 -translate-x-1/2',
  left: 'right-full top-1/2 mr-2 -translate-y-1/2',
  right: 'left-full top-1/2 ml-2 -translate-y-1/2',
};

export default function Tooltip({ content, children, position = 'top', className }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);

  const showTooltip = () => setVisible(true);
  const hideTooltip = () => setVisible(false);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      hideTooltip();
    }
  };

  const handleFocus = (e: FocusEvent) => {
    // Only show on keyboard focus, not mouse focus
    if (e.relatedTarget === null) {
      showTooltip();
    }
  };

  const handleBlur = (e: FocusEvent) => {
    // Small delay to allow click events on tooltip content
    setTimeout(hideTooltip, 100);
  };

  // Wrap children in a focusable element if it's not already interactive
  const child = Children.only(children);
  const isInteractive =
    isValidElement(child) &&
    (['button', 'a', 'input', 'select', 'textarea'].includes(child.type as string) ||
      (child.props && (child.props.onClick || child.props.href || child.props.tabIndex !== undefined)));

  const triggerProps = isInteractive ? {} : { tabIndex: 0, role: 'button' };

  return (
    <div className="relative inline-flex">
      <div
        ref={triggerRef}
        {...triggerProps}
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="inline-flex"
      >
        {isValidElement(child)
          ? cloneElement(child, {
              ...triggerProps,
            })
          : child}
      </div>
      {visible && (
        <div
          ref={tooltipRef}
          className={clsx(
            'absolute z-50 whitespace-nowrap rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white shadow-lg',
            'animate-fade-in',
            positionStyles[position],
            className
          )}
          role="tooltip"
          onMouseEnter={showTooltip}
          onMouseLeave={hideTooltip}
        >
          {content}
        </div>
      )}
    </div>
  );
}
