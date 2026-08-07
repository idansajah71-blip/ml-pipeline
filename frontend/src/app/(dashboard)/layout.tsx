'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import LoadingSpinner from '@/components/LoadingSpinner';
import OnboardingTour from '@/components/OnboardingTour';
import FeedbackButton from '@/components/FeedbackButton';
import FAQWidget from '@/components/FAQWidget';
import GlobalSearch from '@/components/GlobalSearch';
import Breadcrumb from '@/components/Breadcrumb';
import { useAuth } from '@/lib/auth';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:rounded-lg focus:bg-primary-600 focus:px-4 focus:py-2 focus:text-white focus:shadow-lg"
      >
        Loncat ke konten
      </a>

      <Sidebar />

      {/* Top bar: GlobalSearch lives here, always visible */}
      <div className="fixed left-0 right-0 top-0 z-30 flex h-14 items-center justify-end border-b border-gray-200 bg-white px-4 lg:left-64 dark:border-gray-700 dark:bg-gray-900">
        <GlobalSearch />
      </div>

      <main id="main-content" className="flex-1 p-4 pt-16 lg:ml-64 lg:p-8 lg:pt-8">
        {/* Breadcrumb: appears on every page below the top bar */}
        <Breadcrumb />
        {children}
      </main>

      <OnboardingTour />
      <FAQWidget />
      <FeedbackButton />
    </div>
  );
}
