'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { authHeaders } from '../../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function ScoreCard({ label, value, unit, score }: { label: string; value: number | null; unit: string; score: string }) {
  const color = score === 'good' ? 'text-green-400 border-green-600' : score === 'needs_improvement' ? 'text-yellow-400 border-yellow-600' : score === 'poor' ? 'text-red-400 border-red-600' : 'text-gray-400 border-gray-700';
  const bg = score === 'good' ? 'bg-green-900/20' : score === 'needs_improvement' ? 'bg-yellow-900/20' : score === 'poor' ? 'bg-red-900/20' : 'bg-gray-800/50';
  return (
    <div className={`${bg} border ${color} rounded-xl p-6 text-center`}>
      <div className={`text-3xl font-bold ${color}`}>{value != null ? value.toFixed(0) : '—'}<span className="text-lg ml-1">{unit}</span></div>
      <div className="text-white font-semibold mt-1">{label}</div>
      <div className={`text-sm mt-1 capitalize ${color}`}>{score || 'unknown'}</div>
    </div>
  );
}

export default function CWVPage() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    fetch(`${API}/api/projects/${id}/cwv/pages`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : null).then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  async function triggerCWV() {
    setTriggering(true);
    const res = await fetch(`${API}/api/projects/${id}/cwv/measure`, { method: 'POST', headers: authHeaders() });
    const d = await res.json();
    setMsg(d.message || 'CWV measurement started!');
    setTriggering(false);
  }

  const pages = data?.pages || [];
  const avgLcp = pages.filter((p: any) => p.lcp).reduce((s: number, p: any) => s + p.lcp, 0) / (pages.filter((p: any) => p.lcp).length || 1);
  const avgCls = pages.filter((p: any) => p.cls != null).reduce((s: number, p: any) => s + p.cls, 0) / (pages.filter((p: any) => p.cls != null).length || 1);
  const avgFcp = pages.filter((p: any) => p.fcp).reduce((s: number, p: any) => s + p.fcp, 0) / (pages.filter((p: any) => p.fcp).length || 1);

  function lcpScore(v: number) { return v <= 2500 ? 'good' : v <= 4000 ? 'needs_improvement' : 'poor'; }
  function clsScore(v: number) { return v <= 0.1 ? 'good' : v <= 0.25 ? 'needs_improvement' : 'poor'; }
  function fcpScore(v: number) { return v <= 1800 ? 'good' : v <= 3000 ? 'needs_improvement' : 'poor'; }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <a href={`/projects/${id}`} className="text-gray-400 hover:text-white text-sm">← Project</a>
            <h1 className="text-2xl font-bold mt-1">Core Web Vitals</h1>
          </div>
          <button onClick={triggerCWV} disabled={triggering}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded-lg font-semibold text-sm transition-colors">
            {triggering ? 'Starting…' : '▶ Measure CWV'}
          </button>
        </div>
        {msg && <div className="mb-6 p-3 bg-blue-900/40 border border-blue-700 rounded text-blue-200 text-sm">{msg}</div>}
        {loading ? <p className="text-gray-400">Loading…</p> : (
          <>
            <div className="grid grid-cols-3 gap-4 mb-8">
              <ScoreCard label="LCP" value={pages.length ? avgLcp : null} unit="ms" score={pages.length ? lcpScore(avgLcp) : '' } />
              <ScoreCard label="CLS" value={pages.length ? avgCls : null} unit="" score={pages.length ? clsScore(avgCls) : '' } />
              <ScoreCard label="FCP" value={pages.length ? avgFcp : null} unit="ms" score={pages.length ? fcpScore(avgFcp) : '' } />
            </div>
            {pages.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-gray-800">
                    <th className="text-left p-3 text-gray-400">URL</th>
                    <th className="text-right p-3 text-gray-400">LCP</th>
                    <th className="text-right p-3 text-gray-400">CLS</th>
                    <th className="text-right p-3 text-gray-400">FCP</th>
                    <th className="text-right p-3 text-gray-400">Score</th>
                  </tr></thead>
                  <tbody>
                    {pages.map((p: any, i: number) => (
                      <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="p-3 text-gray-300 max-w-xs truncate">{p.url}</td>
                        <td className="p-3 text-right">{p.lcp ? `${p.lcp.toFixed(0)}ms` : '—'}</td>
                        <td className="p-3 text-right">{p.cls != null ? p.cls.toFixed(3) : '—'}</td>
                        <td className="p-3 text-right">{p.fcp ? `${p.fcp.toFixed(0)}ms` : '—'}</td>
                        <td className="p-3 text-right">
                          <span className={`text-xs px-2 py-1 rounded font-medium ${
                            p.cwv_score === 'good' ? 'bg-green-900 text-green-300'
                            : p.cwv_score === 'needs_improvement' ? 'bg-yellow-900 text-yellow-300'
                            : p.cwv_score === 'poor' ? 'bg-red-900 text-red-300' : 'bg-gray-800 text-gray-400'}`}>
                            {p.cwv_score || '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {pages.length === 0 && <p className="text-gray-400 text-center py-12">No CWV data yet. Click "Measure CWV" to start measurement.</p>}
          </>
        )}
      </div>
    </div>
  );
}
