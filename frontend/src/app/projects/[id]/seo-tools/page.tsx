"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, SeoToolsResult, SeoToolIssue } from "@/lib/api";

const SEV_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  warning:  "bg-yellow-100 text-yellow-700 border-yellow-200",
  info:     "bg-blue-100 text-blue-700 border-blue-200",
};
const SEV_DOT: Record<string, string> = {
  critical: "bg-red-500",
  warning:  "bg-yellow-400",
  info:     "bg-blue-400",
};

type Tab = "robots" | "sitemap" | "comparison";

function IssueList({ issues }: { issues: SeoToolIssue[] }) {
  if (!issues.length) return <p className="text-sm text-green-600 font-medium">✅ Keine Issues gefunden</p>;
  return (
    <div className="space-y-2">
      {issues.map((iss, i) => (
        <div key={i} className={`border rounded-lg p-3 ${SEV_COLORS[iss.severity] || "bg-gray-50"}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full ${SEV_DOT[iss.severity] || "bg-gray-400"}`} />
            <span className="text-xs font-semibold uppercase tracking-wide">{iss.severity}</span>
            <span className="text-xs font-mono text-gray-500">{iss.type}</span>
          </div>
          <p className="text-sm font-medium">{iss.description}</p>
          {iss.recommendation && <p className="text-xs text-gray-600 mt-1">💡 {iss.recommendation}</p>}
        </div>
      ))}
    </div>
  );
}

export default function SeoToolsPage() {
  const params = useParams();
  const id = Number(params.id);
  const [data, setData]       = useState<SeoToolsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");
  const [tab, setTab]         = useState<Tab>("robots");

  useEffect(() => {
    api.getSeoTools(id)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
          <Link href="/" className="hover:text-blue-600">Projects</Link>
          <span>/</span>
          <Link href={`/projects/${id}`} className="hover:text-blue-600">Project #{id}</Link>
          <span>/</span>
          <span className="text-gray-800 font-medium">SEO Tools</span>
        </nav>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">🤖 SEO Tools</h1>
        <p className="text-sm text-gray-500 mb-6">robots.txt & sitemap.xml Analyse</p>

        {loading && <div className="text-center py-16 text-gray-500">Analysiere robots.txt und sitemap.xml…</div>}
        {error && <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">{error}</div>}

        {data && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className={`rounded-xl p-4 border ${data.robots.found ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                <div className="text-xs text-gray-500 mb-1">robots.txt</div>
                <div className={`text-lg font-bold ${data.robots.found ? "text-green-700" : "text-red-700"}`}>
                  {data.robots.found ? "✅ Gefunden" : "❌ Nicht gefunden"}
                </div>
                <div className="text-xs text-gray-500 mt-1">{data.robots.issues.length} Issues</div>
              </div>
              <div className={`rounded-xl p-4 border ${data.sitemap.found ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                <div className="text-xs text-gray-500 mb-1">sitemap.xml</div>
                <div className={`text-lg font-bold ${data.sitemap.found ? "text-green-700" : "text-red-700"}`}>
                  {data.sitemap.found ? "✅ Gefunden" : "❌ Nicht gefunden"}
                </div>
                <div className="text-xs text-gray-500 mt-1">{data.sitemap.total_url_count.toLocaleString()} URLs</div>
              </div>
              <div className="rounded-xl p-4 border bg-blue-50 border-blue-200">
                <div className="text-xs text-gray-500 mb-1">URL-Abdeckung</div>
                <div className="text-lg font-bold text-blue-700">
                  {data.url_comparison.in_both_count.toLocaleString()} / {data.url_comparison.sitemap_count.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500 mt-1">in Sitemap gecrawlt</div>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 mb-4 border-b border-gray-200">
              {(["robots", "sitemap", "comparison"] as Tab[]).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${tab === t ? "border-blue-600 text-blue-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                  {t === "robots" ? "🤖 robots.txt" : t === "sitemap" ? "🗺️ Sitemap" : "🔍 URL-Vergleich"}
                </button>
              ))}
            </div>

            {/* Tab: robots.txt */}
            {tab === "robots" && (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h2 className="font-semibold text-gray-800 mb-3">Metadaten</h2>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-gray-500">URL:</span> <code className="text-xs bg-gray-100 px-1 rounded">{data.robots.url}</code></div>
                    <div><span className="text-gray-500">Crawl-Delay:</span> {data.robots.crawl_delay ?? "nicht gesetzt"}</div>
                    <div><span className="text-gray-500">User-Agents:</span> {data.robots.user_agents.join(", ") || "—"}</div>
                    <div><span className="text-gray-500">Sitemap-Verweise:</span> {data.robots.sitemaps.length}</div>
                  </div>
                  {data.robots.disallowed_paths.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-gray-500 mb-1">Disallowed Paths ({data.robots.disallowed_paths.length})</div>
                      <div className="flex flex-wrap gap-1">
                        {data.robots.disallowed_paths.slice(0, 30).map((p, i) => (
                          <code key={i} className="text-xs bg-gray-100 px-2 py-0.5 rounded border">{p}</code>
                        ))}
                        {data.robots.disallowed_paths.length > 30 && <span className="text-xs text-gray-400">+{data.robots.disallowed_paths.length - 30} weitere</span>}
                      </div>
                    </div>
                  )}
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h2 className="font-semibold text-gray-800 mb-3">Issues</h2>
                  <IssueList issues={data.robots.issues} />
                </div>
                {data.robots.content && (
                  <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <h2 className="font-semibold text-gray-800 mb-3">Inhalt</h2>
                    <pre className="text-xs bg-gray-50 p-3 rounded border overflow-auto max-h-64 whitespace-pre-wrap">{data.robots.content}</pre>
                  </div>
                )}
              </div>
            )}

            {/* Tab: sitemap */}
            {tab === "sitemap" && (
              <div className="space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h2 className="font-semibold text-gray-800 mb-3">Metadaten</h2>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-gray-500">URL:</span> <code className="text-xs bg-gray-100 px-1 rounded">{data.sitemap.url}</code></div>
                    <div><span className="text-gray-500">Typ:</span> <span className="font-medium">{data.sitemap.type}</span></div>
                    <div><span className="text-gray-500">URLs gesamt:</span> <span className="font-bold">{data.sitemap.total_url_count.toLocaleString()}</span></div>
                    <div><span className="text-gray-500">Kind-Sitemaps:</span> {data.sitemap.child_sitemaps.length}</div>
                  </div>
                  {data.sitemap.child_sitemaps.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-gray-500 mb-1">Kind-Sitemaps</div>
                      <div className="space-y-1">
                        {data.sitemap.child_sitemaps.map((url, i) => (
                          <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                            className="block text-xs text-blue-600 hover:underline truncate">{url}</a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <h2 className="font-semibold text-gray-800 mb-3">Issues</h2>
                  <IssueList issues={data.sitemap.issues} />
                </div>
                {data.sitemap.urls.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <h2 className="font-semibold text-gray-800 mb-3">URLs (erste 100)</h2>
                    <div className="space-y-1 max-h-80 overflow-auto">
                      {data.sitemap.urls.slice(0, 100).map((url, i) => (
                        <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                          className="block text-xs text-blue-600 hover:underline truncate">{url}</a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab: URL comparison */}
            {tab === "comparison" && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-green-700">{data.url_comparison.in_both_count.toLocaleString()}</div>
                    <div className="text-xs text-gray-500 mt-1">✅ In Sitemap & gecrawlt</div>
                  </div>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-700">{data.url_comparison.in_sitemap_not_crawled_count.toLocaleString()}</div>
                    <div className="text-xs text-gray-500 mt-1">⚠️ In Sitemap, nicht gecrawlt</div>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
                    <div className="text-2xl font-bold text-blue-700">{data.url_comparison.crawled_not_in_sitemap_count.toLocaleString()}</div>
                    <div className="text-xs text-gray-500 mt-1">🔵 Gecrawlt, nicht in Sitemap</div>
                  </div>
                </div>

                {data.url_comparison.in_sitemap_not_crawled.length > 0 && (
                  <div className="bg-white rounded-xl border border-yellow-200 p-6">
                    <h2 className="font-semibold text-gray-800 mb-3">⚠️ In Sitemap, aber nicht gecrawlt ({data.url_comparison.in_sitemap_not_crawled_count.toLocaleString()})</h2>
                    <div className="space-y-1 max-h-64 overflow-auto">
                      {data.url_comparison.in_sitemap_not_crawled.map((url, i) => (
                        <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                          className="block text-xs text-yellow-700 hover:underline truncate">{url}</a>
                      ))}
                    </div>
                  </div>
                )}

                {data.url_comparison.crawled_not_in_sitemap.length > 0 && (
                  <div className="bg-white rounded-xl border border-blue-200 p-6">
                    <h2 className="font-semibold text-gray-800 mb-3">🔵 Gecrawlt, aber nicht in Sitemap ({data.url_comparison.crawled_not_in_sitemap_count.toLocaleString()})</h2>
                    <div className="space-y-1 max-h-64 overflow-auto">
                      {data.url_comparison.crawled_not_in_sitemap.map((url, i) => (
                        <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                          className="block text-xs text-blue-700 hover:underline truncate">{url}</a>
                      ))}
                    </div>
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
