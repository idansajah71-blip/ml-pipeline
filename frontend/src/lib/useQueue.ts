'use client';

import { useState, useCallback } from 'react';

export function useQueue<T>(initialItems: T[] = []) {
  const [items, setItems] = useState<T[]>(initialItems);

  const enqueue = useCallback((item: T) => {
    setItems((prev) => [...prev, item]);
  }, []);

  const dequeue = useCallback((): T | undefined => {
    let dequeuedItem: T | undefined;
    setItems((prev) => {
      const [first, ...rest] = prev;
      dequeuedItem = first;
      return rest;
    });
    return dequeuedItem;
  }, []);

  const peek = useCallback((): T | undefined => {
    return items[0];
  }, [items]);

  const clear = useCallback(() => {
    setItems([]);
  }, []);

  return {
    items,
    enqueue,
    dequeue,
    peek,
    clear,
    size: items.length,
    isEmpty: items.length === 0,
  };
}
