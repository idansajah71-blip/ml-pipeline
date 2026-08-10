'use client';

import { useState, useEffect } from 'react';
import { User, Lock, Key, Save, Loader2, Copy, Check, Trophy, Download, Star, MessageSquare, BarChart3 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { auth, marketplaceStats } from '@/lib/api';
import { ContributorStats, ModelUsageStats } from '@/types';

const BADGE_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  'Baru': { label: 'Baru', color: 'text-gray-600', bg: 'bg-gray-100', icon: '🌱' },
  'Pemula': { label: 'Pemula', color: 'text-blue-600', bg: 'bg-blue-100', icon: '⭐' },
  'Kontributor': { label: 'Kontributor', color: 'text-green-600', bg: 'bg-green-100', icon: '🏅' },
  'Kontributor Aktif': { label: 'Kontributor Aktif', color: 'text-purple-600', bg: 'bg-purple-100', icon: '🎖️' },
  'Kontributor Elite': { label: 'Kontributor Elite', color: 'text-yellow-600', bg: 'bg-yellow-100', icon: '👑' },
};

export default function SettingsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'api-key' | 'contributor'>('profile');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const [contributorStats, setContributorStats] = useState<ContributorStats | null>(null);
  const [usageStats, setUsageStats] = useState<ModelUsageStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
    username: user?.username || '',
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });

  const [apiKey, setApiKey] = useState(user?.api_key || '');

  // Fetch contributor stats when tab is active
  useEffect(() => {
    if (activeTab === 'contributor') {
      setStatsLoading(true);
      Promise.all([
        marketplaceStats.contributorStats().catch(() => null),
        marketplaceStats.myModels().catch(() => null),
      ])
        .then(([cs, us]) => {
          if (cs?.data) setContributorStats(cs.data);
          if (us?.data) setUsageStats(us.data);
        })
        .finally(() => setStatsLoading(false));
    }
  }, [activeTab]);

  const handleProfileUpdate = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await auth.me();
      setSuccess('Profile updated successfully');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    if (passwordForm.new_password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api/v1'}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      });
      setSuccess('Password changed successfully');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err: any) {
      setError(err.message || 'Password change failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateApiKey = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || '/api/v1'}/auth/api-key`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await res.json();
      setApiKey(data.api_key);
      setSuccess('API key generated successfully');
    } catch (err: any) {
      setError(err.message || 'API key generation failed');
    } finally {
      setLoading(false);
    }
  };

  const copyApiKey = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const badge = contributorStats?.badge || 'Baru';
  const badgeConfig = BADGE_CONFIG[badge] || BADGE_CONFIG['Baru'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">Manage your account settings and contributor profile</p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="flex border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
          {([
            { key: 'profile', label: 'Profile', icon: User },
            { key: 'password', label: 'Password', icon: Lock },
            { key: 'api-key', label: 'API Key', icon: Key },
            { key: 'contributor', label: 'Kontributor', icon: Trophy },
          ] as const).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium whitespace-nowrap ${
                activeTab === key
                  ? 'border-b-2 border-primary-600 text-primary-600 dark:text-primary-400'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">{error}</div>
          )}
          {success && (
            <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-300">{success}</div>
          )}

          {activeTab === 'profile' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Full Name</label>
                <input
                  type="text"
                  value={profileForm.full_name}
                  onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
                <input
                  type="email"
                  value={profileForm.email}
                  disabled
                  className="mt-1 block w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
                <input
                  type="text"
                  value={profileForm.username}
                  disabled
                  className="mt-1 block w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Role</label>
                <input
                  type="text"
                  value={user?.role || '-'}
                  disabled
                  className="mt-1 block w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm text-gray-500 capitalize dark:border-gray-600 dark:bg-gray-700"
                />
              </div>
              <button
                onClick={handleProfileUpdate}
                disabled={loading}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Changes
              </button>
            </div>
          )}

          {activeTab === 'password' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Current Password</label>
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">New Password</label>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Confirm New Password</label>
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                />
              </div>
              <button
                onClick={handlePasswordChange}
                disabled={loading || !passwordForm.current_password || !passwordForm.new_password}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
                Change Password
              </button>
            </div>
          )}

          {activeTab === 'api-key' && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Use API keys to authenticate requests to the API programmatically.
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Your API Key</label>
                <div className="mt-1 flex gap-2">
                  <input
                    type="text"
                    value={apiKey || 'No API key generated'}
                    readOnly
                    className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-4 py-2.5 text-sm font-mono text-gray-600 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  />
                  {apiKey && (
                    <button
                      onClick={copyApiKey}
                      className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                    >
                      {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                      {copied ? 'Copied' : 'Copy'}
                    </button>
                  )}
                </div>
              </div>
              <button
                onClick={handleGenerateApiKey}
                disabled={loading}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
                {apiKey ? 'Regenerate Key' : 'Generate Key'}
              </button>
              <p className="text-xs text-gray-500 dark:text-gray-500">
                Note: Regenerating will revoke the old key immediately.
              </p>
            </div>
          )}

          {activeTab === 'contributor' && (
            <div className="space-y-6">
              {statsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : (
                <>
                  {/* Badge display */}
                  <div className="flex items-center gap-4 rounded-xl border border-gray-200 bg-gradient-to-r from-gray-50 to-white p-6 dark:border-gray-700 dark:from-gray-800 dark:to-gray-800">
                    <div className={`flex h-16 w-16 items-center justify-center rounded-2xl text-3xl ${badgeConfig.bg}`}>
                      {badgeConfig.icon}
                    </div>
                    <div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Badge Kontributor</p>
                      <p className={`text-xl font-bold ${badgeConfig.color}`}>{badgeConfig.label}</p>
                      <p className="mt-1 text-xs text-gray-400">
                        {badge === 'Baru' && 'Mulai share model untuk dapat badge pertama!'}
                        {badge === 'Pemula' && 'Bagus! Terus tingkatkan kontribusimu.'}
                        {badge === 'Kontributor' && 'Model-mu sudah banyak membantu orang lain.'}
                        {badge === 'Kontributor Aktif' && 'Kontribusi luar biasa! Tinggal sedikit lagi ke Elite.'}
                        {badge === 'Kontributor Elite' && 'Kontributor terbaik di platform ini! 🎉'}
                      </p>
                    </div>
                  </div>

                  {/* Stats cards */}
                  {contributorStats && (
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <BarChart3 className="h-4 w-4" />
                          <span className="text-xs">Model Di-share</span>
                        </div>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{contributorStats.total_models_shared}</p>
                      </div>
                      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <Download className="h-4 w-4" />
                          <span className="text-xs">Total Download</span>
                        </div>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{contributorStats.total_downloads.toLocaleString()}</p>
                      </div>
                      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <Star className="h-4 w-4" />
                          <span className="text-xs">Rating Rata-rata</span>
                        </div>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                          {contributorStats.avg_rating > 0 ? contributorStats.avg_rating.toFixed(1) : '–'}
                        </p>
                      </div>
                      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                          <MessageSquare className="h-4 w-4" />
                          <span className="text-xs">Feedback Diterima</span>
                        </div>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{contributorStats.total_feedback_received}</p>
                      </div>
                    </div>
                  )}

                  {/* Per-model breakdown */}
                  {usageStats && usageStats.models.length > 0 && (
                    <div>
                      <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Statistik per Model</h3>
                      <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
                        <table className="w-full text-left text-sm">
                          <thead className="bg-gray-50 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                            <tr>
                              <th className="px-4 py-2">Model</th>
                              <th className="px-4 py-2 text-center">Download</th>
                              <th className="px-4 py-2 text-center">Rating</th>
                              <th className="px-4 py-2 text-center">Feedback</th>
                              <th className="px-4 py-2 text-center">Prediksi</th>
                              <th className="px-4 py-2 text-center">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                            {usageStats.models.map((m) => (
                              <tr key={m.share_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                <td className="px-4 py-3">
                                  <p className="font-medium text-gray-900 dark:text-white">{m.model_name}</p>
                                  <p className="text-xs text-gray-500 dark:text-gray-400">{m.algorithm}</p>
                                </td>
                                <td className="px-4 py-3 text-center text-gray-700 dark:text-gray-300">{m.downloads}</td>
                                <td className="px-4 py-3 text-center">
                                  {m.rating > 0 ? (
                                    <span className="inline-flex items-center gap-0.5 text-yellow-600 dark:text-yellow-400">
                                      <Star className="h-3 w-3 fill-current" />
                                      {m.rating.toFixed(1)}
                                    </span>
                                  ) : '–'}
                                </td>
                                <td className="px-4 py-3 text-center text-gray-700 dark:text-gray-300">{m.feedback_count}</td>
                                <td className="px-4 py-3 text-center text-gray-700 dark:text-gray-300">{m.prediction_count}</td>
                                <td className="px-4 py-3 text-center">
                                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                                    m.status === 'approved' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                    m.status === 'pending' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                    'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                                  }`}>
                                    {m.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {contributorStats && contributorStats.total_models_shared === 0 && (
                    <div className="rounded-lg border border-dashed border-gray-300 py-8 text-center dark:border-gray-600">
                      <Trophy className="mx-auto mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" />
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Kamu belum share model apa pun ke marketplace.
                      </p>
                      <p className="mt-1 text-xs text-gray-400">
                        Mulai share model dari halaman Model untuk dapat badge dan statistik!
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
