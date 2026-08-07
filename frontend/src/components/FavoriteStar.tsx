'use client';

import { Star } from 'lucide-react';
import { useFavorites } from '@/lib/useFavorites';

type FavoriteType = 'model' | 'dataset';

interface FavoriteStarProps {
  id: string;
  type: FavoriteType;
  className?: string;
}

/**
 * A toggle star button for pinning/un-pinning a model or dataset.
 * Purely localStorage-based — no API calls.
 */
export default function FavoriteStar({ id, type, className = '' }: FavoriteStarProps) {
  const { isFavorite, toggle } = useFavorites(type);
  const pinned = isFavorite(id);

  return (
    <button
      onClick={(e) => { e.stopPropagation(); e.preventDefault(); toggle(id); }}
      aria-label={pinned ? 'Lepas dari favorit' : 'Tambah ke favorit'}
      title={pinned ? 'Lepas dari favorit' : 'Tambah ke favorit'}
      className={`rounded p-1 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 ${className}`}
    >
      <Star
        className={`h-4 w-4 transition-colors ${
          pinned
            ? 'fill-yellow-400 text-yellow-400'
            : 'text-gray-300 hover:text-yellow-400 dark:text-gray-600'
        }`}
      />
    </button>
  );
}
