'use client';

import { useEffect, useRef, useCallback } from 'react';

export function useAbortController() {
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const getSignal = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();
    return controllerRef.current.signal;
  }, []);

  return { getSignal, abort: () => controllerRef.current?.abort() };
}
