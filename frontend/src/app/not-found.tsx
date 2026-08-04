import Link from 'next/link';
import { Brain, Home, ArrowLeft, Search } from 'lucide-react';

const suggestions = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Datasets', href: '/datasets' },
  { name: 'Models', href: '/models' },
  { name: 'Experiments', href: '/experiments' },
  { name: 'Settings', href: '/settings' },
];

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4">
      <div className="flex flex-col items-center text-center">
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary-600 shadow-lg">
          <Brain className="h-10 w-10 text-white" />
        </div>

        <h1 className="mb-2 text-7xl font-bold text-gray-900">404</h1>
        <h2 className="mb-2 text-xl font-semibold text-gray-700">Page Not Found</h2>
        <p className="mb-8 max-w-md text-gray-500">
          The page you are looking for does not exist or has been moved.
        </p>

        <div className="mb-8 flex gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-primary-700"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>

        <div className="w-full max-w-sm">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-400">Quick Links</p>
          <div className="grid grid-cols-2 gap-2">
            {suggestions.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className="rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-700 shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
              >
                {item.name}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
