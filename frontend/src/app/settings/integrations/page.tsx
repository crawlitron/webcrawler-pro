'use client';
import { useEffect, useState } from 'react';
import { authHeaders } from '../../../lib/auth';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function IntegrationsPage() {
  const [status, setStatus] = useState<any>(null);
  const [sites, setSites] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  async function load() {
    const res = await fetch(`${API}/api/integrations/gsc/status`, { headers: authHeaders() });
    if (res.ok) {
      const s = await res.json();
      setStatus(s);
      if (s.connected) {
        const sRes = await fetch(`${API}/api/integrations/gsc/sites`, { headers: authHeaders() });
        if (sRes.ok) { const d = await sRes.json(); setSites(d.sites || []); }
      }
    }
    setLoading(false);
  }

  async function connectGSC() {
    const res = await fetch(`${API}/api/integrations/gsc/auth-url`, { headers: authHeaders() });
    if (res.ok) { const d = await res.json(); window.location.href = d.auth_url; }
    else setMsg('Failed to get auth URL — check GOOGLE_CLIENT_ID in .env');
  }

  async function disconnect() {
    await fetch(`${API}/api/integrations/gsc/disconnect`, { method: 'DELETE', headers: authHeaders() });
    setStatus(null); setSites([]); setMsg('GSC disconnected');
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-8">Integrations</h1>
        {msg && <div className="mb-4 p-3 bg-blue-900/40 border border-blue-700 rounded text-blue-200 text-sm">{msg}</div>}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center text-lg">G</div>
            <div>
              <h2 className="font-semibold">Google Search Console</h2>
              <p className="text-gray-400 text-sm">Import keyword rankings, coverage issues, and search analytics</p>
            </div>
            <div className="ml-auto">
              {loading ? <span className="text-gray-500 text-sm">Loading…</span>
              : status?.connected ? (
                <span className="text-green-400 text-sm font-medium">● Connected</span>
              ) : (
                <span className="text-gray-500 text-sm">Not connected</span>
              )}
            </div>
          </div>
          {!loading && !status?.connected && (
            <button onClick={connectGSC}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-semibold transition-colors text-sm">
              Connect Google Search Console
            </button>
          )}
          {!loading && status?.connected && (
            <div className="space-y-3">
              <p className="text-sm text-gray-300">Connected site: <span className="text-white font-medium">{status.site_url || '(none selected)'}</span></p>
              {sites.length > 0 && (
                <div>
                  <p className="text-sm text-gray-400 mb-2">Available sites:</p>
                  <ul className="space-y-1">
                    {sites.map((s: any, i: number) => (
                      <li key={i} className="text-sm text-gray-300 bg-gray-800 rounded px-3 py-1">{s.siteUrl || s.site_url || JSON.stringify(s)}</li>
                    ))}
                  </ul>
                </div>
              )}
              <button onClick={disconnect}
                className="bg-red-900/50 hover:bg-red-800 border border-red-700 px-4 py-2 rounded-lg text-sm text-red-300 transition-colors">
                Disconnect
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
