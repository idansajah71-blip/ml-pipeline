'use client';

import { useEffect, useCallback, useRef } from 'react';

const DRAFT_KEY = 'ml_wizard_draft';
const DRAFT_VERSION = 1;

export interface WizardDraft {
  version: number;
  savedAt: number;
  currentStep: string;
  state: {
    datasetId: string | null;
    datasetName: string;
    targetColumn: string;
    predictionType: 'number' | 'category' | null;
    mode: 'simple' | 'advanced';
    algorithm: string;
  };
}

/** Serialize the parts of WizardState that can be restored (not File objects or training results). */
export function saveDraft(step: string, state: WizardDraft['state']): void {
  if (typeof window === 'undefined') return;
  // Don't save trivial progress (nothing useful yet)
  if (!state.datasetId && !state.datasetName) return;
  const draft: WizardDraft = {
    version: DRAFT_VERSION,
    savedAt: Date.now(),
    currentStep: step,
    state,
  };
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // quota exceeded or private mode — ignore
  }
}

export function loadDraft(): WizardDraft | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const draft: WizardDraft = JSON.parse(raw);
    if (draft.version !== DRAFT_VERSION) { clearDraft(); return null; }
    // Expire drafts older than 7 days
    if (Date.now() - draft.savedAt > 7 * 24 * 60 * 60 * 1000) { clearDraft(); return null; }
    return draft;
  } catch {
    return null;
  }
}

export function clearDraft(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(DRAFT_KEY);
}

/** Hook: auto-saves draft on every meaningful state change (debounced 800ms). */
export function useWizardDraft(
  currentStep: string,
  state: WizardDraft['state'],
  active: boolean, // don't save during training/results
) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!active) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      saveDraft(currentStep, state);
    }, 800);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [currentStep, state, active]);

  const discard = useCallback(() => clearDraft(), []);
  return { discard };
}
