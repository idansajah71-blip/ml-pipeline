import Link from 'next/link';
import { Brain } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100">
      <div className="flex flex-col items-center">
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary-600">
          <Brain className="h-10 w-10 text-white" />
        </div>
        <h1 className="mb-2 text-6xl font-bold text-gray-900">404</h1>
        <p className="mb-8 text-lg text-gray-600">Page not found</p>
        <Link
          href="/"
          className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-medium text-white hover:bg-primary-700"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
