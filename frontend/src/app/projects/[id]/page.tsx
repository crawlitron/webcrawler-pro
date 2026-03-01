import Link from "next/link"


"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api, Project, Crawl, Page, Issue, PageListResponse, IssueListResponse } from "@/lib/api";

const SEVERITY_COLORS = {
  critical: "bg-red-100 text-red-700 border-red-200",
  warning:  "bg-yellow-100 text-yellow-700 border-yellow-200",
  info:     "bg-blue-100 text-blue-700 border-blue-200",
};

const STATUS_COLOR = (code?: number) => {
  if (!code) return "bg-gray-100 text-gray-500";
  if (code < 300) return "bg-green-100 text-green-700";
  if (code < 400) return "bg-blue-100 text-blue-700";
  if (code < 500) return "bg-red-100 text-red-700";
  return "bg-red-200 text-red-800";
};

type Tab = "pages" | "issues";

export default function ProjectPage() {
  const params   = useParams();
  const id       = Number(params.id);

  const [project,   setProject]   = useState<Project | null>(null);
  const [crawl,     setCrawl]     = useState<Crawl | null>(null);
  const [crawls,    setCrawls]    = useState<Crawl[]>([]);
  const [pages,     setPages]     = useState<PageListResponse | null>(null);
  const [issues,    setIssues]    = useState<IssueListResponse | null>(null);
  const [tab,       setTab]       = useState<Tab>("pages");
  const [loading,   setLoading]   = useState(true);
  const [starting,  setStarting]  = useState(false);
  const [error,     setError]     = useState("");

  // Page filters
  const [pageNum,    setPageNum]    = useState(1);
  const [pageSize]                  = useState(50);
  const [searchUrl,  setSearchUrl]  = useState("");
  const [filterCode, setFilterCode] = useState("");

  // Issue filters
  const [issueSeverity, setIssueSeverity] = useState("");

  // ── Loaders ────────────────────────────────────────────────────────────────
  const loadProject = useCallback(async () => {
    const p = await api.getProject(id);
    setProject(p);
    return p;
  }, [id]);

  const loadCrawls = useCallback(async () => {
    const cs = await api.getProjectCrawls(id);
    setCrawls(cs);
    return cs;
  }, [id]);

  const loadPages = useCallback(async (c: Crawl) => {
    if (c.status !== "completed") return;
    const params: Record<string, any> = { page: pageNum, page_size: pageSize };
    if (filterCode) params.status_code = Number(filterCode);
    if (searchUrl)  params.search = searchUrl;
    const data = await api.getPages(c.id, params);
    setPages(data);
  }, [pageNum, pageSize, filterCode, searchUrl]);

  const loadIssues = useCallback(async (c: Crawl) => {
    if (c.status !== "completed") return;
    const data = await api.getIssues(c.id, issueSeverity ? { severity: issueSeverity } : undefined);
    setIssues(data);
  }, [issueSeverity]);

  const loadAll = useCallback(async () => {
    try {
      const [p, cs] = await Promise.all([loadProject(), loadCrawls()]);
      const latest = cs[0] || null;
      setCrawl(latest);
      if (latest) {
        await Promise.all([loadPages(latest), loadIssues(latest)]);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [loadProject, loadCrawls, loadPages, loadIssues]);

  // Initial load
  useEffect(() => { loadAll(); }, [id]);

  // Polling while running/pending
  useEffect(() => {
    if (!crawl || (crawl.status !== "running" && crawl.status !== "pending")) return;
    const timer = setInterval(async () => {
      try {
        const c = await api.getCrawl(crawl.id);
        setCrawl(c);
        if (c.status === "completed" || c.status === "failed") {
          clearInterval(timer);
          if (c.status === "completed") {
            await Promise.all([loadPages(c), loadIssues(c)]);
          }
        }
      } catch { clearInterval(timer); }
    }, 2000);
    return () => clearInterval(timer);
  }, [crawl?.id, crawl?.status]);

  // Reload pages/issues when filters change
  useEffect(() => {
    if (crawl?.status === "completed") loadPages(crawl);
  }, [pageNum, filterCode, searchUrl]);

  useEffect(() => {
    if (crawl?.status === "completed") loadIssues(crawl);
  }, [issueSeverity]);

  // ── Actions ────────────────────────────────────────────────────────────────
  const handleStartCrawl = async () => {
    if (!project) return;
    setStarting(true);
    setError("");
    try {
      const c = await api.startCrawl(id);
      setCrawl(c);
      setPages(null);
      setIssues(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  };

  const handleSelectCrawl = async (c: Crawl) => {
    setCrawl(c);
    if (c.status === "completed") {
      await Promise.all([loadPages(c), loadIssues(c)]);
    }
  };

  // ── Derived ────────────────────────────────────────────────────────────────
  const progress = crawl?.progress_percent ?? 0;
  const isActive = crawl?.status === "running" || crawl?.status === "pending";

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 mb-6">
        <Link href="/" className="hover:text-blue-600">Projects</Link>
        <span>/</span>
        <span className="text-gray-700 font-medium">{project?.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project?.name}</h1>
          {/* v0.4.0 Quick Navigation */}
        <div className="flex flex-wrap gap-2 mb-3">
          <Link href={`/projects/${id}/analytics`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors">
            📊 Analytics
          </Link>
          <Link href={`/projects/${id}/urls`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors">
            🔍 URL Explorer
          </Link>
          <Link href={`/projects/${id}/accessibility`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-green-50 hover:border-green-300 hover:text-green-700 transition-colors">
            ♿ Accessibility
          </Link>
          <Link href={`/projects/${id}/mobile`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-purple-50 hover:border-purple-300 hover:text-purple-700 transition-colors">
            📱 Mobile SEO
          </Link>
          <Link href={`/projects/${id}/analytics/ga4`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-orange-50 hover:border-orange-300 hover:text-orange-700 transition-colors">
            📊 Google Analytics
          </Link>
          <Link href={`/projects/${id}/settings`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 hover:text-gray-900 transition-colors">
            ⚙️ Settings
          </Link>
          <Link href={`/projects/${id}/seo-tools`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 hover:text-gray-900 transition-colors">
            SEO Tools
          </Link>
          <Link href={`/projects/${id}/compare`}
            className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 hover:text-gray-900 transition-colors">
            Vergleich
          </Link>
          <Link href={`/projects/${id}/cwv`}
            className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">
            CWV
          </Link>
          <Link href={`/projects/${id}/rankings`}
            className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">
            Rankings
          </Link>
          <Link href={`/projects/${id}/gsc`}
            className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">
            GSC
          </Link>
        </div>
        <a href={project?.start_url} target="_blank" rel="noopener noreferrer"
            className="text-sm text-blue-500 hover:underline mt-1 inline-block">
            {project?.start_url}
          </a>
        </div>
        <button
          onClick={handleStartCrawl}
          disabled={starting || isActive}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50 transition-colors"
        >
          {starting ? "Starting..." : isActive ? "Crawling..." : "▶ New Crawl"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">{error}</div>
      )}

      {/* Crawl History Selector */}
      {crawls.length > 1 && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-sm text-gray-500 font-medium">Crawl:</span>
          <div className="flex gap-2 flex-wrap">
            {crawls.map((c, i) => (
              <button
                key={c.id}
                onClick={() => handleSelectCrawl(c)}
                className={`text-xs px-3 py-1 rounded-full border font-medium transition-colors ${
                  crawl?.id === c.id
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 hover:border-blue-400"
                }`}
              >
                #{crawls.length - i} — {new Date(c.created_at).toLocaleDateString()} ({c.status})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* No Crawl Yet */}
      {!crawl && (
        <div className="text-center py-20 bg-white rounded-xl border">
          <div className="text-5xl mb-4">🚀</div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No crawls yet</h3>
          <p className="text-gray-400 mb-6">Start a crawl to analyze your website</p>
          <button onClick={handleStartCrawl} disabled={starting}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50">
            {starting ? "Starting..." : "▶ Start Crawl"}
          </button>
        </div>
      )}

      {/* Active Crawl Progress */}
      {crawl && isActive && (
        <div className="bg-white rounded-xl border shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 rounded-full bg-blue-500 animate-pulse" />
              <span className="font-semibold text-gray-800">
                {crawl.status === "pending" ? "Queued — waiting for worker..." : "Crawling in progress..."}
              </span>
            </div>
            <span className="text-sm text-gray-500">{progress.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
            <div
              className="h-3 bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.max(progress, 2)}%` }}
            />
          </div>
          <div className="flex gap-6 mt-4 text-sm text-gray-500">
            <span>📄 Pages crawled: <strong className="text-gray-800">{crawl.crawled_urls}</strong></span>
            <span>❌ Failed: <strong className="text-red-600">{crawl.failed_urls}</strong></span>
            {crawl.total_urls > 0 && <span>🔢 Total found: <strong className="text-gray-800">{crawl.total_urls}</strong></span>}
          </div>
        </div>
      )}

      {/* Crawl Failed */}
      {crawl && crawl.status === "failed" && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <h3 className="font-semibold text-red-700 mb-1">Crawl Failed</h3>
          <p className="text-red-600 text-sm">{crawl.error_message || "Unknown error occurred"}</p>
        </div>
      )}

      {/* Completed Stats */}
      {crawl && crawl.status === "completed" && (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            {[
              { label: "Pages Crawled",    value: crawl.crawled_urls,    color: "text-blue-600" },
              { label: "Failed URLs",       value: crawl.failed_urls,     color: "text-gray-500" },
              { label: "Critical Issues",   value: crawl.critical_issues, color: "text-red-600"  },
              { label: "Warning Issues",    value: crawl.warning_issues,  color: "text-yellow-600" },
              { label: "Info Issues",       value: crawl.info_issues,     color: "text-blue-500" },
              { label: "Total Issues",      value: crawl.critical_issues + crawl.warning_issues + crawl.info_issues, color: "text-gray-700" },
            ].map(s => (
              <div key={s.label} className="bg-white rounded-xl border p-4 text-center">
                <p className={`text-2xl font-bold ${s.color}`}>{s.value.toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Issue Summary Bar */}
          {(crawl.critical_issues + crawl.warning_issues + crawl.info_issues) > 0 && (
            <div className="bg-white rounded-xl border p-4 mb-6">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-medium text-gray-600">Issue Overview:</span>
                {crawl.critical_issues > 0 && (
                  <button onClick={() => { setTab("issues"); setIssueSeverity("critical"); }}
                    className="flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm border border-red-200 hover:bg-red-200">
                    🔴 {crawl.critical_issues} Critical
                  </button>
                )}
                {crawl.warning_issues > 0 && (
                  <button onClick={() => { setTab("issues"); setIssueSeverity("warning"); }}
                    className="flex items-center gap-1 px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm border border-yellow-200 hover:bg-yellow-200">
                    🟡 {crawl.warning_issues} Warnings
                  </button>
                )}
                {crawl.info_issues > 0 && (
                  <button onClick={() => { setTab("issues"); setIssueSeverity("info"); }}
                    className="flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm border border-blue-200 hover:bg-blue-200">
                    🔵 {crawl.info_issues} Info
                  </button>
                )}
                <a
                  href={api.exportCsv(crawl.id)}
                  className="ml-auto px-3 py-1 border rounded-lg text-sm hover:bg-gray-50 font-medium transition-colors"
                  download
                >
                  ⬇ Export CSV
                </a>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="flex border-b mb-6">
            <button
              onClick={() => setTab("pages")}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === "pages" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Pages {pages ? `(${pages.total.toLocaleString()})` : ""}
            </button>
            <button
              onClick={() => setTab("issues")}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === "issues" ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              Issues {issues ? `(${issues.total.toLocaleString()})` : ""}
            </button>
          </div>

          {/* ── PAGES TAB ──────────────────────────────────────────────── */}
          {tab === "pages" && (
            <>
              <div className="flex gap-3 mb-4 flex-wrap">
                <input
                  type="text" placeholder="Search URL..." value={searchUrl}
                  onChange={e => { setSearchUrl(e.target.value); setPageNum(1); }}
                  className="px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 w-72"
                />
                <select
                  value={filterCode}
                  onChange={e => { setFilterCode(e.target.value); setPageNum(1); }}
                  className="px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  <option value="">All Status Codes</option>
                  <option value="200">200 OK</option>
                  <option value="301">301 Redirect</option>
                  <option value="302">302 Redirect</option>
                  <option value="404">404 Not Found</option>
                  <option value="500">500 Server Error</option>
                </select>
                {(searchUrl || filterCode) && (
                  <button onClick={() => { setSearchUrl(""); setFilterCode(""); setPageNum(1); }}
                    className="px-3 py-2 border rounded-lg text-sm hover:bg-gray-50">
                    Clear
                  </button>
                )}
              </div>

              {pages && (
                <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          {["URL","Status","Response","Title","H1","Issues","Depth"].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {pages.items.map(p => (
                          <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3 max-w-xs">
                              <a href={p.url} target="_blank" rel="noopener noreferrer"
                                className="text-blue-600 hover:underline truncate block text-xs" title={p.url}>
                                {p.url.replace(/^https?:\/\/[^/]+/, "") || "/"}
                              </a>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLOR(p.status_code)}`}>
                                {p.status_code ?? "ERR"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                              {p.response_time ? `${p.response_time.toFixed(2)}s` : "—"}
                            </td>
                            <td className="px-4 py-3 max-w-xs">
                              <span className={`truncate block text-xs ${
                                !p.title ? "text-red-400 italic" : "text-gray-700"
                              }`} title={p.title || ""} >
                                {p.title || "(missing)"}
                              </span>
                              {p.title && (
                                <span className={`text-xs ${
                                  p.title.length > 60 ? "text-red-400" : p.title.length < 30 ? "text-yellow-500" : "text-gray-400"
                                }`}>
                                  {p.title.length} chars
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 max-w-xs">
                              <span className={`truncate block text-xs ${
                                !p.h1 ? "text-red-400 italic" : "text-gray-700"
                              }`}>
                                {p.h1 || "(missing)"}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              {p.issue_count > 0
                                ? <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">{p.issue_count}</span>
                                : <span className="text-gray-300 text-xs">—</span>
                              }
                            </td>
                            <td className="px-4 py-3 text-gray-400 text-xs">{p.depth}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {pages.total_pages > 1 && (
                    <div className="px-4 py-3 border-t flex items-center justify-between bg-gray-50">
                      <span className="text-xs text-gray-500">
                        {((pageNum - 1) * pageSize) + 1}–{Math.min(pageNum * pageSize, pages.total)} of {pages.total.toLocaleString()} URLs
                      </span>
                      <div className="flex gap-2">
                        <button disabled={pageNum <= 1} onClick={() => setPageNum(p => p - 1)}
                          className="px-3 py-1 border rounded text-xs disabled:opacity-40 hover:bg-white">
                          ← Prev
                        </button>
                        <span className="px-3 py-1 text-xs text-gray-600">Page {pageNum} / {pages.total_pages}</span>
                        <button disabled={pageNum >= pages.total_pages} onClick={() => setPageNum(p => p + 1)}
                          className="px-3 py-1 border rounded text-xs disabled:opacity-40 hover:bg-white">
                          Next →
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* ── ISSUES TAB ─────────────────────────────────────────────── */}
          {tab === "issues" && (
            <>
              <div className="flex gap-3 mb-4">
                {["", "critical", "warning", "info"].map(s => (
                  <button key={s}
                    onClick={() => setIssueSeverity(s)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                      issueSeverity === s
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-600 hover:border-blue-300"
                    }`}>
                    {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
                    {s === "critical" && issues && ` (${issues.critical})`}
                    {s === "warning"  && issues && ` (${issues.warning})`}
                    {s === "info"     && issues && ` (${issues.info})`}
                  </button>
                ))}
              </div>

              {issues && issues.items.length === 0 && (
                <div className="text-center py-12 bg-white rounded-xl border">
                  <div className="text-4xl mb-3">✅</div>
                  <p className="text-gray-500">No issues found for this filter</p>
                </div>
              )}

              {issues && issues.items.length > 0 && (
                <div className="space-y-2">
                  {issues.items.map(issue => (
                    <div key={issue.id}
                      className={`bg-white rounded-lg border p-4 ${
                        issue.severity === "critical" ? "border-l-4 border-l-red-500" :
                        issue.severity === "warning"  ? "border-l-4 border-l-yellow-500" :
                        "border-l-4 border-l-blue-400"
                      }`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${
                              SEVERITY_COLORS[issue.severity]
                            }`}>
                              {issue.severity.toUpperCase()}
                            </span>
                            <span className="text-xs text-gray-400 font-mono">{issue.issue_type}</span>
                          </div>
                          <p className="text-sm text-gray-800 font-medium">{issue.description}</p>
                          {issue.recommendation && (
                            <p className="text-xs text-gray-500 mt-1">💡 {issue.recommendation}</p>
                          )}
                          {issue.page_url && (
                            <a href={issue.page_url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-blue-500 hover:underline mt-1 block truncate">
                              {issue.page_url}
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
