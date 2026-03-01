'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { authHeaders } from '../../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function GSCPage() {
  const { id } = useParams();
  const [analytics, setAnalytics] = useState<any>(null);
  const [coverage, setCoverage] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(28);
  const [notLinked, setNotLinked] = useState(false);

  async function load() {
    setLoading(true);
    const [aRes, cRes] = await Promise.all([
      fetch(`${API}/api/projects/${id}/gsc/analytics?days=${days}`, { headers: authHeaders() }),
      fetch(`${API}/api/projects/${id}/gsc/coverage`, { headers: authHeaders() }),
    ]);
    if (aRes.status === 404) { setNotLinked(true); setLoading(false); return; }
    if (aRes.ok) setAnalytics(await aRes.json());
    if (cRes.ok) setCoverage(await cRes.json());
    setLoading(false);
  }

  useEffect(() => { load(); }, [id, days]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <a href={`/projects/${id}`} className="text-gray-400 hover:text-white text-sm">← Project</a>
            <h1 className="text-2xl font-bold mt-1">Google Search Console</h1>
          </div>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none">
            <option value={7}>Last 7 days</option>
            <option value={28}>Last 28 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
        {notLinked && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-6 text-center">
            <p className="text-yellow-300 font-semibold mb-2">GSC not linked to this project</p>
            <p className="text-yellow-400/70 text-sm mb-4">Connect and link Google Search Console to view search analytics.</p>
            <a href="/settings/integrations" className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg text-sm font-semibold transition-colors">Connect GSC</a>
          </div>
        )}
        {loading && !notLinked && <p className="text-gray-400">Loading…</p>}
        {analytics && (
          <>
            <div className="grid grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-bold text-blue-400">{analytics.total_clicks?.toLocaleString()}</div>
                <div className="text-gray-400 text-sm">Total Clicks</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-bold">{analytics.total_impressions?.toLocaleString()}</div>
                <div className="text-gray-400 text-sm">Impressions</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-bold">{analytics.avg_ctr}%</div>
                <div className="text-gray-400 text-sm">Avg. CTR</div>
              </div>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-bold text-yellow-400">#{analytics.avg_position}</div>
                <div className="text-gray-400 text-sm">Avg. Position</div>
              </div>
            </div>
            <p className="text-gray-400 text-sm mb-4">Site: <span className="text-white">{analytics.site_url}</span> · Period: {analytics.period_days} days</p>
            {analytics.rows?.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-6">
                <div className="p-4 border-b border-gray-800 font-semibold">Top Landing Pages</div>
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-gray-800">
                    <th className="text-left p-3 text-gray-400">Page</th>
                    <th className="text-right p-3 text-gray-400">Clicks</th>
                    <th className="text-right p-3 text-gray-400">Impressions</th>
                    <th className="text-right p-3 text-gray-400">CTR</th>
                  </tr></thead>
                  <tbody>
                    {analytics.rows.slice(0, 20).map((r: any, i: number) => (
                      <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="p-3 text-gray-300 truncate max-w-sm">{r.page || r.date || '—'}</td>
                        <td className="p-3 text-right">{r.clicks?.toLocaleString()}</td>
                        <td className="p-3 text-right">{r.impressions?.toLocaleString()}</td>
                        <td className="p-3 text-right">{r.ctr ? `${(r.ctr * 100).toFixed(1)}%` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
        {coverage && coverage.sitemaps?.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="font-semibold mb-3">Sitemaps</div>
            {coverage.sitemaps.map((s: any, i: number) => (
              <div key={i} className="text-sm text-gray-300 py-1 border-b border-gray-800/50 last:border-0">{s.path || JSON.stringify(s)}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
