'use client';

import { useState, useEffect } from 'react';
import { Users, Plus, Trash2, UserPlus, Crown } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useToast } from '@/components/Toast';
import { organizations } from '@/lib/api';

export default function OrganizationsPage() {
  const { toast } = useToast();
  const [orgs, setOrgs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newOrg, setNewOrg] = useState({ name: '', slug: '' });
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [showAddMember, setShowAddMember] = useState(false);
  const [newMember, setNewMember] = useState({ user_id: '', role: 'member' });

  useEffect(() => {
    loadOrgs();
  }, []);

  const loadOrgs = async () => {
    setLoading(true);
    try {
      const res = await organizations.list();
      setOrgs(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const loadMembers = async (orgId: string) => {
    setSelectedOrg(orgId);
    try {
      const res = await organizations.listMembers(orgId);
      setMembers(res.data);
    } catch (err) { console.error(err); }
  };

  const createOrg = async () => {
    if (!newOrg.name || !newOrg.slug) return;
    try {
      await organizations.create(newOrg);
      setShowCreate(false);
      setNewOrg({ name: '', slug: '' });
      loadOrgs();
    } catch (err) { toast('error', 'Gagal membuat organisasi'); }
  };

  const addMember = async () => {
    if (!selectedOrg || !newMember.user_id) return;
    try {
      await organizations.addMember(selectedOrg, newMember.user_id, newMember.role);
      setShowAddMember(false);
      setNewMember({ user_id: '', role: 'member' });
      loadMembers(selectedOrg);
    } catch (err) { toast('error', 'Gagal menambahkan anggota'); }
  };

  const removeMember = async (userId: string) => {
    if (!selectedOrg || !confirm('Remove this member?')) return;
    try {
      await organizations.removeMember(selectedOrg, userId);
      loadMembers(selectedOrg);
    } catch (err) { toast('error', 'Gagal menghapus anggota'); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Organizations</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage multi-tenant organizations and members</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700">
          <Plus className="h-4 w-4" /> New Organization
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create Organization</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input placeholder="Organization Name" value={newOrg.name} onChange={e => setNewOrg({...newOrg, name: e.target.value})}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400" />
            <input placeholder="Slug (e.g. my-org)" value={newOrg.slug} onChange={e => setNewOrg({...newOrg, slug: e.target.value})}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400" />
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={createOrg} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Create</button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Organizations</h2>
          {loading ? <LoadingSpinner size="sm" /> : (
            <div className="space-y-2">
              {orgs.map(org => (
                <div key={org.id} className={`rounded-lg px-3 py-2 ${selectedOrg === org.id ? 'bg-primary-50 dark:bg-primary-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                  <button onClick={() => loadMembers(org.id)} className="w-full text-left">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{org.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">/{org.slug} - {org.plan}</p>
                  </button>
                </div>
              ))}
              {orgs.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">No organizations yet</p>}
            </div>
          )}
        </div>

        {selectedOrg && (
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Members</h2>
              <button onClick={() => setShowAddMember(true)} className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">
                <UserPlus className="h-4 w-4" /> Add Member
              </button>
            </div>

            {showAddMember && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-700/50">
                <div className="flex gap-3">
                  <input placeholder="User ID" value={newMember.user_id} onChange={e => setNewMember({...newMember, user_id: e.target.value})}
                    className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400" />
                  <select value={newMember.role} onChange={e => setNewMember({...newMember, role: e.target.value})}
                    className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white">
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                  </select>
                  <button onClick={addMember} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Add</button>
                  <button onClick={() => setShowAddMember(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</button>
                </div>
              </div>
            )}

            <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                    <th className="px-6 py-4">User ID</th>
                    <th className="px-6 py-4">Role</th>
                    <th className="px-6 py-4">Joined</th>
                    <th className="px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4">
                        <p className="font-mono text-sm text-gray-900 dark:text-white">{String(member.user_id).slice(0, 8)}...</p>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          {member.role === 'admin' && <Crown className="h-4 w-4 text-yellow-500" />}
                          <span className="text-sm capitalize text-gray-700 dark:text-gray-300">{member.role}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                        {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : '-'}
                      </td>
                      <td className="px-6 py-4">
                        <button onClick={() => removeMember(member.user_id)} className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {members.length === 0 && (
                    <tr><td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">No members</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
