import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Login | ML Pipeline',
  description: 'Sign in to your ML Pipeline account',
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
