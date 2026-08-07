'use client';

import { useCallback, useRef } from 'react';
import api from './api';

export interface FunnelEvent {
  funnel: string;         // e.g. "training-wizard"
  step: string;           // e.g. "upload", "target"
  action: 'enter' | 'complete' | 'abandon';
  duration_ms?: number;   // time spent on this step before moving
  metadata?: Record<string, any>;
}

/**
 * Lightweight funnel drop-off tracker.
 * Fires-and-forgets POST to /api/v1/analytics/funnel.
 * Falls back silently if the endpoint is unavailable.
 */
export function useFunnelTracker(funnelName: string) {
  const stepStartRef = useRef<number>(Date.now());
  const lastStepRef = useRef<string>('');

  const track = useCallback(
    (step: string, action: FunnelEvent['action'], metadata?: Record<string, any>) => {
      const now = Date.now();
      const duration_ms = action !== 'enter' ? now - stepStartRef.current : undefined;
      if (action === 'enter') stepStartRef.current = now;
      lastStepRef.current = step;

      const event: FunnelEvent = { funnel: funnelName, step, action, duration_ms, metadata };

      // Fire and forget — never block the UI
      api.post('/analytics/funnel', event).catch(() => {/* silently ignore */});
    },
    [funnelName],
  );

  /** Call on every step transition: tracks complete on old step + enter on new step. */
  const transition = useCallback(
    (fromStep: string, toStep: string, metadata?: Record<string, any>) => {
      track(fromStep, 'complete', metadata);
      track(toStep, 'enter');
    },
    [track],
  );

  /** Call when user navigates away mid-funnel. */
  const abandon = useCallback(
    (step: string, metadata?: Record<string, any>) => {
      track(step, 'abandon', metadata);
    },
    [track],
  );

  return { track, transition, abandon };
}
