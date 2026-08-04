'use client';

import { useCallback, useMemo } from 'react';

export function useStableCallback<T extends (...args: any[]) => any>(callback: T): T {
  const callbackRef = useMemo(() => ({ current: callback }), [callback]);
  callbackRef.current = callback;

  return useCallback(
    (...args: any[]) => callbackRef.current(...args),
    []
  ) as T;
}
