import { SWRConfiguration } from 'swr';

export const defaultSWRConfig: SWRConfiguration = {
  revalidateOnFocus: true,
  revalidateOnReconnect: true,
  shouldRetryOnError: true,
  errorRetryCount: 3,
  dedupingInterval: 2000,
  focusThrottleInterval: 5000,
};

export const cacheConfig = {
  dedupingInterval: 5000,
  focusThrottleInterval: 10000,
  refreshInterval: 30000,
  revalidateOnFocus: true,
  revalidateOnReconnect: true,
  revalidateIfStale: true,
};

export const staticConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
  revalidateIfStale: false,
  refreshInterval: 0,
};
