import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/lib/auth';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns initial state with loading true', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.loading).toBe(true);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it('loads user from localStorage on mount', () => {
    const mockUser = { id: '1', email: 'test@test.com', username: 'test', role: 'admin' };
    const mockToken = 'test-token-123';
    localStorage.setItem('user', JSON.stringify(mockUser));
    localStorage.setItem('token', mockToken);

    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.token).toBe(mockToken);
  });

  it('clears user on logout', () => {
    const mockUser = { id: '1', email: 'test@test.com', username: 'test', role: 'admin' };
    localStorage.setItem('user', JSON.stringify(mockUser));
    localStorage.setItem('token', 'test-token');

    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
  });
});
