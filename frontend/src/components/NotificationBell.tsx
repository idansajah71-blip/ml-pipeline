'use client';

import { useState, useEffect, useRef } from 'react';
import { Bell, Check, CheckCheck, Trash2, X } from 'lucide-react';
import { inAppNotifications } from '@/lib/api';
import { Notification } from '@/types';
import clsx from 'clsx';

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Poll unread count every 30s
  useEffect(() => {
    const fetchCount = async () => {
      try {
        const res = await inAppNotifications.unreadCount();
        setUnreadCount(res.data.unread_count);
      } catch {}
    };
    fetchCount();
    const interval = setInterval(fetchCount, 30000);
    return () => clearInterval(interval);
  }, []);

  // Load notifications when panel opens
  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    inAppNotifications
      .list({ limit: 20 })
      .then((res) => {
        setItems(res.data.notifications);
        setUnreadCount(res.data.unread_count);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isOpen]);

  // Close on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [isOpen]);

  const handleMarkAllRead = async () => {
    try {
      await inAppNotifications.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {}
  };

  const handleMarkRead = async (id: string) => {
    try {
      await inAppNotifications.markRead(id);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {}
  };

  const handleDelete = async (id: string) => {
    try {
      await inAppNotifications.delete(id);
      setItems((prev) => prev.filter((n) => n.id !== id));
      const wasUnread = items.find((n) => n.id === id && !n.is_read);
      if (wasUnread) setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {}
  };

  const typeIcon = (type: string) => {
    switch (type) {
      case 'training_complete': return '✅';
      case 'training_failed': return '❌';
      case 'feedback_received': return '💬';
      case 'model_downloaded': return '📥';
      default: return '🔔';
    }
  };

  const timeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Baru saja';
    if (mins < 60) return `${mins}m lalu`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}j lalu`;
    const days = Math.floor(hrs / 24);
    return `${days}h lalu`;
  };

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 min-h-[44px] min-w-[44px] flex items-center justify-center"
        aria-label="Notifikasi"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Notifikasi</h3>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="rounded p-1 text-xs text-primary-600 hover:bg-primary-50 dark:text-primary-400"
                  title="Tandai semua sudah dibaca"
                >
                  <CheckCheck className="h-4 w-4" />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8 text-sm text-gray-400">Memuat...</div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center py-8 text-gray-400">
                <Bell className="mb-2 h-8 w-8" />
                <p className="text-sm">Belum ada notifikasi</p>
              </div>
            ) : (
              items.map((notif) => (
                <div
                  key={notif.id}
                  className={clsx(
                    'group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50',
                    !notif.is_read && 'bg-primary-50/50 dark:bg-primary-900/10'
                  )}
                >
                  <span className="mt-0.5 text-base">{typeIcon(notif.type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className={clsx(
                      'text-sm leading-tight',
                      notif.is_read ? 'text-gray-600 dark:text-gray-400' : 'font-medium text-gray-900 dark:text-white'
                    )}>
                      {notif.title}
                    </p>
                    <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-500 line-clamp-2">
                      {notif.message}
                    </p>
                    <p className="mt-1 text-[10px] text-gray-400">{timeAgo(notif.created_at)}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {!notif.is_read && (
                      <button
                        onClick={() => handleMarkRead(notif.id)}
                        className="rounded p-1 text-gray-400 hover:text-green-600"
                        title="Tandai sudah dibaca"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(notif.id)}
                      className="rounded p-1 text-gray-400 hover:text-red-500"
                      title="Hapus"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
