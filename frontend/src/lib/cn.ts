import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

export function twJoin(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
