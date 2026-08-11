'use client';

import { useState } from 'react';
import { MessageCircle, X, Send, Star } from 'lucide-react';

export default function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  const handleSubmit = async () => {
    if (!message.trim()) return;
    setSending(true);
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api/v1'}/notifications/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating, message, page: window.location.pathname }),
      });
    } catch {
      // Silently fail — feedback is non-critical
    } finally {
      setSending(false);
      setSubmitted(true);
      setTimeout(() => {
        setOpen(false);
        setSubmitted(false);
        setRating(0);
        setMessage('');
      }, 2000);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-primary-600 px-4 py-3 text-sm font-medium text-white shadow-lg hover:bg-primary-700 transition-colors"
      >
        <MessageCircle className="h-4 w-4" />
        <span className="hidden sm:inline">Bantuan?</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-end p-6 sm:items-center sm:justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <div className="relative w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <button
              onClick={() => setOpen(false)}
              className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>

            {submitted ? (
              <div className="py-8 text-center">
                <div className="mb-3 flex justify-center">
                  <div className="rounded-full bg-green-100 p-3">
                    <Star className="h-6 w-6 text-green-600" />
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900">Terima kasih!</h3>
                <p className="mt-1 text-sm text-gray-500">Feedback Anda telah dikirim.</p>
              </div>
            ) : (
              <>
                <h3 className="mb-1 text-lg font-semibold text-gray-900">Kirim Feedback</h3>
                <p className="mb-4 text-sm text-gray-500">Bantu kami memperbaiki platform ini.</p>

                <div className="mb-4">
                  <p className="mb-2 text-sm font-medium text-gray-700">Rating:</p>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        onClick={() => setRating(n)}
                        className={`h-8 w-8 rounded-lg transition-colors ${
                          n <= rating ? 'bg-yellow-100 text-yellow-500' : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                        }`}
                      >
                        <Star className={`h-4 w-4 mx-auto ${n <= rating ? 'fill-current' : ''}`} />
                      </button>
                    ))}
                  </div>
                </div>

                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Ceritakan masalah atau saran Anda..."
                  rows={4}
                  className="mb-4 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 resize-none"
                />

                <button
                  onClick={handleSubmit}
                  disabled={!message.trim()}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                  Kirim
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
