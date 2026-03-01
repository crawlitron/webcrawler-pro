'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { authHeaders } from '../../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function Trend({ current, prev }: { current: number; prev?: number }) {
  if (!prev) return <span className="text-gray-500">—</span>;
  const diff = prev - current; // lower position = better
  if (diff > 0) return <span className="text-green-400">↑ {diff.toFixed(1)}</span>;
  if (diff < 0) return <span className="text-red-400">↓ {Math.abs(diff).toFixed(1)}</span>;
  return <span className="text-gray-500">→</span>;
}

export default function RankingsPage() {
  const { id } = useParams();
  const [keywords, setKeywords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [notConnected, setNotConnected] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/projects/${id}/gsc/keywords?days=90&limit=500`, { headers: authHeaders() })
      .then(r => { if (r.status === 404) { setNotConnected(true); return []; } return r.json(); })
      .then(d => { if (Array.isArray(d)) setKeywords(d); })
      .finally(() => setLoading(false));
  }, [id]);

  const filtered = keywords.filter(k =>
    !search || k.keyword?.toLowerCase().includes(search.toLowerCase())
  );

  const top10 = [...keywords].sort((a, b) => (a.position || 99) - (b.position || 99)).slice(0, 10);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <a href={`/projects/${id}`} className="text-gray-400 hover:text-white text-sm">← Project</a>
            <h1 className="text-2xl font-bold mt-1">Rank Tracking</h1>
          </div>
          <a href="/settings/integrations" className="text-sm text-blue-400 hover:underline">Configure GSC →</a>
        </div>
        {notConnected && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-6 text-center mb-8">
            <p className="text-yellow-300 font-semibold mb-2">Google Search Console not connected</p>
            <p className="text-yellow-400/70 text-sm mb-4">Connect GSC to see keyword rankings, clicks, and impressions.</p>
            <a href="/settings/integrations" className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg text-sm font-semibold transition-colors">Connect GSC</a>
          </div>
        )}
        {!notConnected && !loading && keywords.length > 0 && (
          <div className="grid grid-cols-4 gap-4 mb-8">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="text-2xl font-bold">{keywords.length}</div>
              <div className="text-gray-400 text-sm">Keywords</div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="text-2xl font-bold">{keywords.reduce((s, k) => s + (k.clicks || 0), 0).toLocaleString()}</div>
              <div className="text-gray-400 text-sm">Total Clicks</div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="text-2xl font-bold">{keywords.reduce((s, k) => s + (k.impressions || 0), 0).toLocaleString()}</div>
              <div className="text-gray-400 text-sm">Impressions</div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="text-2xl font-bold">
                {(keywords.reduce((s, k) => s + (k.position || 0), 0) / keywords.length).toFixed(1)}
              </div>
              <div className="text-gray-400 text-sm">Avg. Position</div>
            </div>
          </div>
        )}
        {top10.length > 0 && (
          <div className="grid grid-cols-2 gap-6 mb-8">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h2 className="font-semibold mb-3">🏆 Top 10 Keywords</h2>
              <div className="space-y-2">
                {top10.map((k, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300 truncate max-w-48">{k.keyword}</span>
                    <span className="text-yellow-400 font-bold ml-2">#{k.position?.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h2 className="font-semibold mb-3">📉 Needs Improvement</h2>
              <div className="space-y-2">
                {[...keywords].sort((a, b) => (b.position || 0) - (a.position || 0)).slice(0, 10).map((k, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300 truncate max-w-48">{k.keyword}</span>
                    <span className="text-red-400 font-bold ml-2">#{k.position?.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="mb-4">
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search keywords…"
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm w-64 focus:outline-none focus:border-blue-500" />
        </div>
        {loading ? <p className="text-gray-400">Loading…</p> : filtered.length > 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-800">
                <th className="text-left p-3 text-gray-400">Keyword</th>
                <th className="text-right p-3 text-gray-400">Position</th>
                <th className="text-right p-3 text-gray-400">Clicks</th>
                <th className="text-right p-3 text-gray-400">Impressions</th>
                <th className="text-right p-3 text-gray-400">CTR</th>
                <th className="text-left p-3 text-gray-400">Date</th>
              </tr></thead>
              <tbody>
                {filtered.slice(0, 200).map((k, i) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="p-3 text-white font-medium">{k.keyword}</td>
                    <td className="p-3 text-right text-yellow-400 font-bold">{k.position ? `#${k.position.toFixed(1)}` : '—'}</td>
                    <td className="p-3 text-right">{k.clicks?.toLocaleString()}</td>
                    <td className="p-3 text-right">{k.impressions?.toLocaleString()}</td>
                    <td className="p-3 text-right">{k.ctr ? `${(k.ctr * 100).toFixed(1)}%` : '—'}</td>
                    <td className="p-3 text-gray-400">{k.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : !notConnected && !loading && <p className="text-gray-400 py-12 text-center">No ranking data yet. Data syncs daily from GSC.</p>}
      </div>
    </div>
  );
}
