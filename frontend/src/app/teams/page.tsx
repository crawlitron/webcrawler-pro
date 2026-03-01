'use client';
import { useEffect, useState } from 'react';
import { authHeaders } from '../../lib/auth';
import { useAuth } from '../../components/AuthProvider';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TeamsPage() {
  const { user } = useAuth();
  const [teams, setTeams] = useState<any[]>([]);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    const res = await fetch(`${API}/api/teams`, { headers: authHeaders() });
    if (res.ok) setTeams(await res.json());
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function createTeam(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    await fetch(`${API}/api/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ name: newName }),
    });
    setNewName('');
    setCreating(false);
    load();
  }

  const roleColor = (role: string) => ({
    owner: 'bg-purple-900 text-purple-200',
    admin: 'bg-blue-900 text-blue-200',
    editor: 'bg-green-900 text-green-200',
    viewer: 'bg-gray-700 text-gray-300',
  }[role] || 'bg-gray-700 text-gray-300');

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Teams</h1>
        <form onSubmit={createTeam} className="flex gap-3 mb-8">
          <input value={newName} onChange={e => setNewName(e.target.value)} required
            placeholder="New team name…"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
          <button type="submit" disabled={creating || !newName.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg font-semibold transition-colors">
            {creating ? 'Creating…' : '+ Create Team'}
          </button>
        </form>
        {loading ? <p className="text-gray-400">Loading…</p> : teams.length === 0 ? (
          <p className="text-gray-400">No teams yet. Create your first team above.</p>
        ) : (
          <div className="space-y-3">
            {teams.map((t: any) => (
              <a key={t.id} href={`/teams/${t.id}`}
                className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-blue-600 transition-colors">
                <div>
                  <span className="font-semibold text-lg">{t.name}</span>
                  <span className="ml-3 text-gray-400 text-sm">{t.member_count} member{t.member_count !== 1 ? 's' : '' }</span>
                </div>
                <span className={`text-xs px-2 py-1 rounded font-medium ${roleColor(t.my_role)}`}>
                  {t.my_role}
                </span>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
