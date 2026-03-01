'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { authHeaders } from '../../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TeamSettingsPage() {
  const { id } = useParams();
  const [team, setTeam] = useState<any>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    fetch(`${API}/api/teams/${id}`, { headers: authHeaders() })
      .then(r => r.json()).then(setTeam);
  }, [id]);

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch(`${API}/api/teams/${id}/invite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
    });
    const data = await res.json();
    setMsg(data.message || data.detail || '');
    if (res.ok) setInviteEmail('');
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <a href={`/teams/${id}`} className="text-gray-400 hover:text-white text-sm">← Back to team</a>
        <h1 className="text-2xl font-bold mt-2 mb-8">Team Settings</h1>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Invite Member</h2>
          {msg && <div className="mb-3 p-2 bg-blue-900/40 border border-blue-700 rounded text-blue-200 text-sm">{msg}</div>}
          <form onSubmit={invite} className="space-y-3">
            <input type="email" required value={inviteEmail} onChange={e => setInviteEmail(e.target.value)}
              placeholder="member@example.com"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
            <select value={inviteRole} onChange={e => setInviteRole(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none">
              <option value="viewer">Viewer — read-only</option>
              <option value="editor">Editor — can start crawls</option>
              <option value="admin">Admin — manage members</option>
            </select>
            <button type="submit" className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-semibold transition-colors">Send Invite</button>
          </form>
        </div>
      </div>
    </div>
  );
}
