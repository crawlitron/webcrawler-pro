'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { authHeaders } from '../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TeamDetailPage() {
  const { id } = useParams();
  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    const [tRes, mRes, pRes] = await Promise.all([
      fetch(`${API}/api/teams/${id}`, { headers: authHeaders() }),
      fetch(`${API}/api/teams/${id}/members`, { headers: authHeaders() }),
      fetch(`${API}/api/teams/${id}/projects`, { headers: authHeaders() }),
    ]);
    if (tRes.ok) setTeam(await tRes.json());
    if (mRes.ok) setMembers(await mRes.json());
    if (pRes.ok) setProjects(await pRes.json());
    setLoading(false);
  }

  useEffect(() => { load(); }, [id]);

  if (loading) return <div className="min-h-screen bg-gray-950 text-white p-8">Loading…</div>;
  if (!team) return <div className="min-h-screen bg-gray-950 text-white p-8">Team not found</div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <a href="/teams" className="text-gray-400 hover:text-white text-sm">← Teams</a>
            <h1 className="text-2xl font-bold mt-1">{team.name}</h1>
          </div>
          <a href={`/teams/${id}/settings`}
            className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-4 py-2 rounded-lg text-sm transition-colors">
            Settings
          </a>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-2xl font-bold">{team.member_count}</div>
            <div className="text-gray-400 text-sm">Members</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-2xl font-bold">{projects.length}</div>
            <div className="text-gray-400 text-sm">Projects</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-2xl font-bold">{team.max_crawl_urls?.toLocaleString()}</div>
            <div className="text-gray-400 text-sm">Max URLs</div>
          </div>
        </div>
        <h2 className="text-lg font-semibold mb-3">Members</h2>
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-8">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-gray-800">
              <th className="text-left p-3 text-gray-400">Name</th>
              <th className="text-left p-3 text-gray-400">Email</th>
              <th className="text-left p-3 text-gray-400">Role</th>
            </tr></thead>
            <tbody>
              {members.map((m: any) => (
                <tr key={m.id} className="border-b border-gray-800/50">
                  <td className="p-3">{m.full_name || '—'}</td>
                  <td className="p-3 text-gray-300">{m.email}</td>
                  <td className="p-3"><span className="text-xs bg-gray-800 px-2 py-1 rounded">{m.role}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {projects.length > 0 && (<>
          <h2 className="text-lg font-semibold mb-3">Projects</h2>
          <div className="space-y-2">
            {projects.map((p: any) => (
              <a key={p.id} href={`/projects/${p.id}`}
                className="flex items-center justify-between bg-gray-900 border border-gray-800 rounded-xl p-3 hover:border-blue-600 transition-colors">
                <span className="font-medium">{p.name}</span>
                <span className="text-gray-400 text-sm">{p.start_url}</span>
              </a>
            ))}
          </div>
        </>)}
      </div>
    </div>
  );
}
