'use client';

import { useState, useCallback, useEffect } from 'react';

type FavoriteType = 'model' | 'dataset';
const STORAGE_KEY = 'ml_favorites';

interface FavoritesStore {
  model: string[];
  dataset: string[];
}

function loadStore(): FavoritesStore {
  if (typeof window === 'undefined') return { model: [], dataset: [] };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { model: [], dataset: [] };
    return JSON.parse(raw);
  } catch {
    return { model: [], dataset: [] };
  }
}

function saveStore(store: FavoritesStore): void {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(store)); } catch { /* ignore */ }
}

/**
 * Hook for pinning/un-pinning models or datasets.
 * Completely localStorage-based — zero network requests.
 */
export function useFavorites(type: FavoriteType) {
  const [ids, setIds] = useState<string[]>(() => loadStore()[type]);

  // Keep in sync across tabs
  useEffect(() => {
    const handler = () => setIds(loadStore()[type]);
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [type]);

  const toggle = useCallback((id: string) => {
    setIds((prev) => {
      const store = loadStore();
      const list = store[type];
      const next = list.includes(id) ? list.filter((x) => x !== id) : [id, ...list];
      saveStore({ ...store, [type]: next });
      return next;
    });
  }, [type]);

  const isFavorite = useCallback((id: string) => ids.includes(id), [ids]);

  return { favoriteIds: ids, toggle, isFavorite };
}
