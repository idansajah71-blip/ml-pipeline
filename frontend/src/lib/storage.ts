export const storage = {
  get<T>(key: string, fallback: T): T {
    if (typeof window === 'undefined') return fallback;
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : fallback;
    } catch {
      return fallback;
    }
  },

  set<T>(key: string, value: T): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn(`Failed to save to localStorage key "${key}":`, error);
    }
  },

  remove(key: string): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(key);
  },

  clear(): void {
    if (typeof window === 'undefined') return;
    localStorage.clear();
  },

  has(key: string): boolean {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(key) !== null;
  },
};

export const TOKEN_KEY = 'token';
export const USER_KEY = 'user';

export function getStoredToken(): string | null {
  return storage.get<string | null>(TOKEN_KEY, null);
}

export function getStoredUser() {
  return storage.get('user', null);
}

export function clearAuth(): void {
  storage.remove(TOKEN_KEY);
  storage.remove(USER_KEY);
}
