'use client';

import { useState, useCallback } from 'react';

export function useMap<K, V>(initialEntries: [K, V][] = []) {
  const [map, setMap] = useState<Map<K, V>>(new Map(initialEntries));

  const set = useCallback((key: K, value: V) => {
    setMap((prev) => new Map(prev).set(key, value));
  }, []);

  const remove = useCallback((key: K) => {
    setMap((prev) => {
      const next = new Map(prev);
      next.delete(key);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setMap(new Map());
  }, []);

  const get = useCallback((key: K): V | undefined => {
    return map.get(key);
  }, [map]);

  const has = useCallback((key: K): boolean => {
    return map.has(key);
  }, [map]);

  return {
    map,
    set,
    remove,
    clear,
    get,
    has,
    size: map.size,
    entries: Array.from(map.entries()),
    keys: Array.from(map.keys()),
    values: Array.from(map.values()),
  };
}
