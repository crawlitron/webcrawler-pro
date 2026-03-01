"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CrawlSummaryItem, CrawlDiff } from "@/lib/api";

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  warning: "bg-yellow-100 text-yellow-700",
  info: "bg-blue-100 text-blue-700",
};

type DiffTab = "urls" | "status" | "issues" | "performance" | "content";

export default function ComparePage() {
  const params = useParams();
  const id = Number(params.id);
  const [crawls, setCrawls] = useState<CrawlSummaryItem[]>([]);
  const [crawlAId, setCrawlAId] = useState<number | "">("");
  const [crawlBId, setCrawlBId] = useState<number | "">("");
  const [diff, setDiff] = useState<CrawlDiff | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<DiffTab>("urls");

  useEffect(() => {
    api.getProjectCrawlList(id)
      .then(data => setCrawls(data.filter(c => c.status === "completed")))
      .catch(e => setError(e.message));
  }, [id]);

  const handleCompare = async () => {
    if (!crawlAId || !crawlBId) return;
    if (crawlAId === crawlBId) { setError("Bitte zwei verschiedene Crawls auswaehlen."); return; }
    setError(""); setLoading(true); setDiff(null);
    try {
      const result = await api.compareCrawls(Number(crawlAId), Number(crawlBId));
      setDiff(result); setTab("urls");
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const fmt = (dt: string | null) => dt
    ? new Date(dt).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "--";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
          <Link href="/" className="hover:text-blue-600">Projects</Link>
          <span>/</span>
          <Link href={`/projects/${id}`} className="hover:text-blue-600">Project #{id}</Link>
          <span>/</span>
          <span className="text-gray-800 font-medium">Crawl-Vergleich</span>
        </nav>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Crawl-Vergleich</h1>
        <p className="text-sm text-gray-500 mb-6">Vergleiche zwei Crawls und erkenne Veraenderungen</p>
        {error && <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm mb-4">{error}</div>}

        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Crawl A (aelter)</label>
              <select value={crawlAId} onChange={e => setCrawlAId(Number(e.target.value) || "")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">-- Crawl auswaehlen --</option>
                {crawls.map(c => (
                  <option key={c.id} value={c.id}>#{c.id} -- {fmt(c.started_at)} -- {c.url_count} URLs, {c.critical_issues} kritisch</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Crawl B (neuer)</label>
              <select value={crawlBId} onChange={e => setCrawlBId(Number(e.target.value) || "")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">-- Crawl auswaehlen --</option>
                {crawls.map(c => (
                  <option key={c.id} value={c.id}>#{c.id} -- {fmt(c.started_at)} -- {c.url_count} URLs, {c.critical_issues} kritisch</option>
                ))}
              </select>
            </div>
          </div>
          <button onClick={handleCompare} disabled={!crawlAId || !crawlBId || loading}
            className="mt-4 bg-blue-600 text-white rounded-lg px-6 py-2 text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {loading ? "Vergleiche..." : "Vergleichen"}
          </button>
        </div>

        {loading && <div className="text-center py-16 text-gray-500">Analysiere Unterschiede...</div>}

        {diff && (
          <>
            <div className="grid grid-cols-2 gap-4 mb-6">
              {[diff.crawl_a, diff.crawl_b].map((c, idx) => (
                <div key={idx} className={`rounded-xl border p-4 ${idx === 0 ? "bg-gray-50 border-gray-200" : "bg-blue-50 border-blue-200"}`}>
                  <div className="text-xs font-semibold text-gray-500 mb-1">{idx === 0 ? "Crawl A" : "Crawl B (neu)"}</div>
                  <div className="text-lg font-bold text-gray-800">Crawl #{c.id}</div>
                  <div className="text-xs text-gray-500">{fmt(c.started_at)}</div>
                  <div className="flex gap-3 mt-2 text-xs">
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{c.url_count} URLs</span>
                    <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded">{c.critical_issues} kritisch</span>
                    <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{c.issue_count} gesamt</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-blue-700">{diff.summary.new_urls}</div>
                <div className="text-xs text-gray-500 mt-1">Neue URLs</div>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-gray-600">{diff.summary.removed_urls}</div>
                <div className="text-xs text-gray-500 mt-1">Entfernte URLs</div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-green-700">{diff.summary.fixed_issues}</div>
                <div className="text-xs text-gray-500 mt-1">Behobene Issues</div>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-red-700">{diff.summary.new_issues}</div>
                <div className="text-xs text-gray-500 mt-1">Neue Issues</div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-green-700">{diff.summary.improved_pages}</div>
                <div className="text-xs text-gray-500 mt-1">Verbesserte Seiten</div>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                <div className="text-2xl font-bold text-red-700">{diff.summary.degraded_pages}</div>
                <div className="text-xs text-gray-500 mt-1">Verschlechterte Seiten</div>
              </div>
            </div>

            <div className="flex gap-2 mb-4 border-b border-gray-200 overflow-x-auto">
              {([["urls","URL-Aenderungen"],["status","Status"],["issues","Issues-Diff"],["performance","Performance"],["content","Content"]] as [DiffTab, string][]).map(([t, label]) => (
                <button key={t} onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 whitespace-nowrap transition-colors ${tab === t ? "border-blue-600 text-blue-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                  {label}
                </button>
              ))}
            </div>

            {tab === "urls" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-blue-200 p-5">
                  <h3 className="font-semibold text-blue-700 mb-3">Neue URLs ({diff.new_urls.length})</h3>
                  {diff.new_urls.length === 0 ? <p className="text-sm text-gray-500">Keine neuen URLs</p> : (
                    <div className="space-y-1 max-h-80 overflow-auto">
                      {diff.new_urls.map((url, i) => <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="block text-xs text-blue-600 hover:underline truncate">{url}</a>)}
                    </div>
                  )}
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="font-semibold text-gray-600 mb-3">Entfernte URLs ({diff.removed_urls.length})</h3>
                  {diff.removed_urls.length === 0 ? <p className="text-sm text-gray-500">Keine entfernten URLs</p> : (
                    <div className="space-y-1 max-h-80 overflow-auto">
                      {diff.removed_urls.map((url, i) => <span key={i} className="block text-xs text-gray-400 line-through truncate">{url}</span>)}
                    </div>
                  )}
                </div>
              </div>
            )}

            {tab === "status" && (
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-800 mb-3">HTTP Status-Aenderungen ({diff.status_changes.length})</h3>
                {diff.status_changes.length === 0 ? <p className="text-sm text-gray-500">Keine Status-Aenderungen</p> : (
                  <table className="w-full text-xs">
                    <thead><tr className="bg-gray-50"><th className="text-left p-2">URL</th><th className="text-center p-2">Alt</th><th className="text-center p-2">Neu</th></tr></thead>
                    <tbody>
                      {diff.status_changes.map((sc, i) => (
                        <tr key={i} className="border-t border-gray-100">
                          <td className="p-2 truncate max-w-xs"><a href={sc.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{sc.url}</a></td>
                          <td className="p-2 text-center"><span className={`px-2 py-0.5 rounded font-mono ${sc.old_status && sc.old_status < 400 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>{sc.old_status ?? "--"}</span></td>
                          <td className="p-2 text-center"><span className={`px-2 py-0.5 rounded font-mono ${sc.new_status && sc.new_status < 400 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>{sc.new_status ?? "--"}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {tab === "issues" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-green-200 p-5">
                  <h3 className="font-semibold text-green-700 mb-3">Behobene Issues ({diff.fixed_issues.length})</h3>
                  {diff.fixed_issues.length === 0 ? <p className="text-sm text-gray-500">Keine behobenen Issues</p> : (
                    <div className="space-y-2 max-h-80 overflow-auto">
                      {diff.fixed_issues.map((iss, i) => (
                        <div key={i} className="bg-green-50 rounded p-2">
                          <div className="flex gap-2 items-center mb-0.5">
                            <span className={`text-xs px-1.5 py-0.5 rounded ${SEV_BADGE[iss.severity] || "bg-gray-100"}`}>{iss.severity}</span>
                            <span className="text-xs font-mono text-gray-500">{iss.type}</span>
                          </div>
                          <div className="text-xs text-gray-600 truncate">{iss.url}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="bg-white rounded-xl border border-red-200 p-5">
                  <h3 className="font-semibold text-red-700 mb-3">Neue Issues ({diff.new_issues.length})</h3>
                  {diff.new_issues.length === 0 ? <p className="text-sm text-gray-500">Keine neuen Issues</p> : (
                    <div className="space-y-2 max-h-80 overflow-auto">
                      {diff.new_issues.map((iss, i) => (
                        <div key={i} className="bg-red-50 rounded p-2">
                          <div className="flex gap-2 items-center mb-0.5">
                            <span className={`text-xs px-1.5 py-0.5 rounded ${SEV_BADGE[iss.severity] || "bg-gray-100"}`}>{iss.severity}</span>
                            <span className="text-xs font-mono text-gray-500">{iss.type}</span>
                          </div>
                          <div className="text-xs text-gray-600 truncate">{iss.url}</div>
                          {iss.description && <div className="text-xs text-gray-500 mt-0.5">{iss.description}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {tab === "performance" && (
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-800 mb-3">Performance-Aenderungen ({diff.performance_changes.length})</h3>
                {diff.performance_changes.length === 0 ? <p className="text-sm text-gray-500">Keine Performance-Aenderungen</p> : (
                  <table className="w-full text-xs">
                    <thead><tr className="bg-gray-50"><th className="text-left p-2">URL</th><th className="text-center p-2">Alt</th><th className="text-center p-2">Neu</th><th className="text-center p-2">Delta</th></tr></thead>
                    <tbody>
                      {diff.performance_changes.map((pc, i) => {
                        const delta = pc.new_score - pc.old_score;
                        return (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="p-2 truncate max-w-xs text-blue-600">{pc.url}</td>
                            <td className="p-2 text-center font-mono">{pc.old_score}</td>
                            <td className="p-2 text-center font-mono">{pc.new_score}</td>
                            <td className={`p-2 text-center font-bold ${delta > 0 ? "text-green-600" : "text-red-600"}`}>{delta > 0 ? "+" : ""}{delta}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {tab === "content" && (
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-800 mb-3">Titel-Aenderungen ({diff.title_changes.length})</h3>
                {diff.title_changes.length === 0 ? <p className="text-sm text-gray-500">Keine Titel-Aenderungen</p> : (
                  <div className="space-y-3 max-h-96 overflow-auto">
                    {diff.title_changes.map((tc, i) => (
                      <div key={i} className="border border-gray-100 rounded-lg p-3">
                        <div className="text-xs text-blue-600 truncate mb-1">{tc.url}</div>
                        <div className="text-xs"><span className="text-gray-400">Alt:</span> <span className="text-red-600 line-through">{tc.old || "(leer)"}</span></div>
                        <div className="text-xs"><span className="text-gray-400">Neu:</span> <span className="text-green-600">{tc.new || "(leer)"}</span></div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}