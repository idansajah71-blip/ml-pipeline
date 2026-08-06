'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import { HelpCircle, X, Search, MessageCircle, ChevronRight } from 'lucide-react';
import { FAQ_ENTRIES, type FAQEntry } from '@/lib/recommendations';

function simpleScore(query: string, entry: FAQEntry): number {
  if (!query) return 0;
  const q = query.toLowerCase();
  let score = 0;

  if (entry.question.toLowerCase().includes(q)) score += 10;
  if (entry.answer.toLowerCase().includes(q)) score += 5;

  for (const tag of entry.tags) {
    if (tag.includes(q) || q.includes(tag)) score += 8;
  }

  const words = q.split(/\s+/).filter(Boolean);
  for (const word of words) {
    if (entry.question.toLowerCase().includes(word)) score += 3;
    if (entry.tags.some((t) => t.includes(word))) score += 4;
  }

  return score;
}

export default function FAQWidget() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedFAQ, setSelectedFAQ] = useState<FAQEntry | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  const results = useMemo(() => {
    if (!query.trim()) return [];
    return FAQ_ENTRIES
      .map((entry) => ({ entry, score: simpleScore(query, entry) }))
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5)
      .map((r) => r.entry);
  }, [query]);

  const handleClose = () => {
    setOpen(false);
    setQuery('');
    setSelectedFAQ(null);
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 left-6 z-40 flex items-center gap-2 rounded-full bg-white border border-gray-200 px-4 py-3 text-sm font-medium text-gray-700 shadow-lg hover:bg-gray-50 transition-colors dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300"
        aria-label="Bantuan cepat"
      >
        <HelpCircle className="h-4 w-4 text-primary-600" />
        <span className="hidden sm:inline">Tanya Cepat</span>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-start p-6 sm:items-center sm:justify-center">
          <div className="fixed inset-0 bg-black/30" onClick={handleClose} />
          <div className="relative w-full max-w-md rounded-xl bg-white shadow-xl dark:bg-gray-800 max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center gap-2">
                <HelpCircle className="h-5 w-5 text-primary-600" />
                <h3 className="font-semibold text-gray-900 dark:text-white">Tanya Cepat</h3>
              </div>
              <button onClick={handleClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-gray-100 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setSelectedFAQ(null); }}
                  placeholder="Ketik pertanyaan Anda..."
                  className="w-full rounded-lg border border-gray-300 bg-gray-50 py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                />
              </div>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-4">
              {selectedFAQ ? (
                <div>
                  <button
                    onClick={() => setSelectedFAQ(null)}
                    className="mb-3 text-xs text-primary-600 hover:text-primary-700"
                  >
                    ← Kembali ke hasil
                  </button>
                  <h4 className="mb-2 font-semibold text-gray-900 dark:text-white">{selectedFAQ.question}</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{selectedFAQ.answer}</p>
                  <span className="mt-3 inline-block rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-500">
                    {selectedFAQ.category}
                  </span>
                </div>
              ) : results.length > 0 ? (
                <div className="space-y-2">
                  {results.map((entry) => (
                    <button
                      key={entry.id}
                      onClick={() => setSelectedFAQ(entry)}
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-left hover:border-primary-300 hover:bg-primary-50/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{entry.question}</span>
                        <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      </div>
                      <p className="mt-1 text-xs text-gray-500 line-clamp-1">{entry.answer}</p>
                    </button>
                  ))}
                </div>
              ) : query.trim() ? (
                <div className="py-6 text-center">
                  <p className="text-sm text-gray-500">Tidak ditemukan jawaban untuk pertanyaan Anda.</p>
                  <p className="mt-2 text-xs text-gray-400">Coba kata kunci lain atau gunakan feedback untuk bertanya langsung.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="mb-2 text-xs font-medium text-gray-500 uppercase tracking-wide">Pertanyaan Populer</p>
                  {FAQ_ENTRIES.slice(0, 5).map((entry) => (
                    <button
                      key={entry.id}
                      onClick={() => setSelectedFAQ(entry)}
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 p-3 text-left hover:border-primary-300 hover:bg-primary-50/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{entry.question}</span>
                        <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Fallback to feedback */}
            <div className="border-t border-gray-200 dark:border-gray-700 p-4">
              <p className="mb-2 text-xs text-gray-500 text-center">Tidak menemukan jawaban?</p>
              <button
                onClick={handleClose}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
              >
                <MessageCircle className="h-4 w-4" />
                Kirim Feedback
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
