"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type Page, type Issue } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Filters {
  search: string;
  status_class: string;
  content_type: string;
  is_indexable: string;
  has_issues: string;
  sort_by: string;
  sort_dir: string;
}

const INITIAL_FILTERS: Filters = {
  search: "",
  status_class: "",
  content_type: "",
  is_indexable: "",
  has_issues: "",
  sort_by: "depth",
  sort_dir: "asc",
};

const STATUS_CLASSES = [
  { value: "", label: "All statuses" },
  { value: "2xx", label: "2xx OK" },
  { value: "3xx", label: "3xx Redirect" },
  { value: "4xx", label: "4xx Client Error" },
  { value: "5xx", label: "5xx Server Error" },
];
const CONTENT_TYPES = [
  { value: "", label: "All types" },
  { value: "text/html", label: "HTML" },
  { value: "application/pdf", label: "PDF" },
  { value: "application/json", label: "JSON" },
];
const INDEXABLE_OPTIONS = [
  { value: "", label: "All pages" },
  { value: "true", label: "Indexable" },
  { value: "false", label: "Noindex" },
];
const HAS_ISSUES_OPTIONS = [
  { value: "", label: "All pages" },
  { value: "true", label: "Has issues" },
  { value: "false", label: "No issues" },
];
const SORT_OPTIONS = [
  { value: "depth", label: "Depth" },
  { value: "url", label: "URL" },
  { value: "status_code", label: "Status" },
  { value: "response_time", label: "Response Time" },
  { value: "word_count", label: "Word Count" },
  { value: "performance_score", label: "Perf Score" },
  { value: "internal_links_count", label: "Internal Links" },
  { value: "images_without_alt", label: "Images no Alt" },
];

const SEV_COLORS: Record<string, string> = {
  critical: "text-red-700 bg-red-50 border border-red-200",
  warning: "text-yellow-700 bg-yellow-50 border border-yellow-200",
  info: "text-blue-700 bg-blue-50 border border-blue-200",
};

// ─── Status badge helper ──────────────────────────────────────────────────────

function StatusBadge({ code }: { code?: number }) {
  if (!code) return <span className="text-gray-400 text-xs">—</span>;
  let cls = "text-green-700 bg-green-50 border border-green-200";
  if (code >= 500) cls = "text-red-700 bg-red-50 border border-red-200";
  else if (code >= 400) cls = "text-orange-700 bg-orange-50 border border-orange-200";
  else if (code >= 300) cls = "text-yellow-700 bg-yellow-50 border border-yellow-200";
  return <span className={`text-xs px-1.5 py-0.5 rounded font-mono font-semibold ${cls}`}>{code}</span>;
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

function DetailPanel({ page, crawlId, onClose }: { page: Page; crawlId: number; onClose: () => void }) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loadingIssues, setLoadingIssues] = useState(true);

  useEffect(() => {
    api.getPageIssues(crawlId, page.id)
      .then((data) => setIssues(data as Issue[]))
      .catch(() => setIssues([]))
      .finally(() => setLoadingIssues(false));
  }, [crawlId, page.id]);

  const extra = (page.extra_data ?? {}) as Record<string, unknown>;
  const redirectChain = (extra.redirect_chain ?? []) as { url: string; status_code: number }[];

  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose}>
      <div className="flex-1 bg-black/30" />
      <div
        className="w-full max-w-xl bg-white h-full overflow-y-auto shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-5 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <StatusBadge code={page.status_code} />
              {!page.is_indexable && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 border border-gray-200">noindex</span>
              )}
            </div>
            <p className="text-sm font-semibold text-gray-900 break-all">{page.url}</p>
          </div>
          <button onClick={onClose} className="shrink-0 text-gray-400 hover:text-gray-700 text-xl font-bold mt-0.5">✕</button>
        </div>

        <div className="flex-1 p-5 space-y-6">
          {/* SEO Data */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">SEO Data</h3>
            <dl className="space-y-2 text-sm">
              {[
                ["Title", page.title || <span className="text-red-500 italic">Missing</span>],
                ["Meta Description", page.meta_description || <span className="text-yellow-600 italic">Missing</span>],
                ["H1", page.h1 || <span className="text-red-500 italic">Missing</span>],
                ["H2 Count", page.h2_count],
                ["Canonical", page.canonical_url || "—"],
                ["Content Type", page.content_type || "—"],
                ["Response Time", page.response_time != null ? `${(page.response_time * 1000).toFixed(0)}ms` : "—"],
                ["Word Count", page.word_count],
                ["Depth", page.depth],
                ["Internal Links", page.internal_links_count],
                ["External Links", page.external_links_count],
                ["Images no Alt", page.images_without_alt],
              ].map(([label, val]) => (
                <div key={String(label)} className="flex gap-2">
                  <dt className="w-36 shrink-0 text-gray-500">{label}</dt>
                  <dd className="flex-1 text-gray-900 break-all">{val}</dd>
                </div>
              ))}
            </dl>
          </section>

          {/* Redirect Chain */}
          {redirectChain.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Redirect Chain ({redirectChain.length - 1} hop{redirectChain.length > 2 ? "s" : ""})</h3>
              <ol className="space-y-1">
                {redirectChain.map((hop, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs">
                    <span className="shrink-0 w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center font-bold text-gray-600">{i + 1}</span>
                    <div>
                      <StatusBadge code={hop.status_code} />
                      <span className="ml-1 text-gray-700 break-all">{hop.url}</span>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {/* Open Graph */}
          {(extra.og_title || extra.og_description || extra.og_image) && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">Open Graph</h3>
              <dl className="space-y-2 text-sm">
                {extra.og_title && <div className="flex gap-2"><dt className="w-36 shrink-0 text-gray-500">og:title</dt><dd className="flex-1 text-gray-900">{String(extra.og_title)}</dd></div>}
                {extra.og_description && <div className="flex gap-2"><dt className="w-36 shrink-0 text-gray-500">og:description</dt><dd className="flex-1 text-gray-900">{String(extra.og_description)}</dd></div>}
                {extra.og_image && <div className="flex gap-2"><dt className="w-36 shrink-0 text-gray-500">og:image</dt><dd className="flex-1 text-gray-900 break-all">{String(extra.og_image)}</dd></div>}
                {extra.og_type && <div className="flex gap-2"><dt className="w-36 shrink-0 text-gray-500">og:type</dt><dd className="flex-1 text-gray-900">{String(extra.og_type)}</dd></div>}
              </dl>
            </section>
          )}

          {/* JSON-LD */}
          {extra.has_jsonld && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">Structured Data</h3>
              <div className="flex flex-wrap gap-1">
                {((extra.jsonld_types ?? []) as string[]).map((t) => (
                  <span key={t} className="text-xs px-2 py-0.5 rounded bg-purple-50 border border-purple-200 text-purple-700">{t}</span>
                ))}
                {!((extra.jsonld_types as string[])?.length) && (
                  <span className="text-xs text-gray-500">JSON-LD present</span>
                )}
              </div>
            </section>
          )}

          {/* Issues */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Issues {!loadingIssues && `(${issues.length})`}
            </h3>
            {loadingIssues ? (
              <div className="animate-pulse text-gray-400 text-sm">Loading...</div>
            ) : issues.length === 0 ? (
              <p className="text-green-600 text-sm">✓ No issues found</p>
            ) : (
              <div className="space-y-2">
                {issues.map((iss) => (
                  <div key={iss.id} className={`rounded-lg p-3 text-xs ${SEV_COLORS[iss.severity] ?? "bg-gray-50"}`}>
                    <div className="font-semibold mb-0.5">{iss.issue_type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</div>
                    <div className="text-gray-700 mb-1">{iss.description}</div>
                    {iss.recommendation && (
                      <div className="text-gray-500 italic">💡 {iss.recommendation}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function UrlExplorerPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [crawlId, setCrawlId] = useState<number | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(50);
  const [filters, setFilters] = useState<Filters>(INITIAL_FILTERS);
  const [pendingFilters, setPendingFilters] = useState<Filters>(INITIAL_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [detailPage, setDetailPage] = useState<Page | null>(null);
  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load crawl ID on mount
  useEffect(() => {
    api.getProject(projectId)
      .then((proj) => {
        if (proj.last_crawl_id) setCrawlId(proj.last_crawl_id);
        else setError("No crawls found. Start a crawl first.");
      })
      .catch(() => setError("Failed to load project"))
      .finally(() => setLoading(false));
  }, [projectId]);

  const fetchPages = useCallback(async (cid: number, f: Filters, pg: number) => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = {
        page: pg,
        page_size: pageSize,
        sort_by: f.sort_by,
        sort_dir: f.sort_dir,
      };
      if (f.search) params.search = f.search;
      if (f.status_class) params.status_class = f.status_class;
      if (f.content_type) params.content_type = f.content_type;
      if (f.is_indexable !== "") params.is_indexable = f.is_indexable === "true";
      if (f.has_issues !== "") params.has_issues = f.has_issues === "true";
      const resp = await api.getPages(cid, params as Parameters<typeof api.getPages>[1]);
      setPages(resp.items);
      setTotal(resp.total);
      setTotalPages(resp.total_pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load pages");
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    if (crawlId) fetchPages(crawlId, filters, currentPage);
  }, [crawlId, filters, currentPage, fetchPages]);

  // Debounced search
  const handleSearchChange = (val: string) => {
    setPendingFilters(prev => ({ ...prev, search: val }));
    if (searchRef.current) clearTimeout(searchRef.current);
    searchRef.current = setTimeout(() => {
      setFilters(prev => ({ ...prev, search: val }));
      setCurrentPage(1);
      setSelected(new Set());
    }, 400);
  };

  const applyFilter = (key: keyof Filters, val: string) => {
    const next = { ...pendingFilters, [key]: val };
    setPendingFilters(next);
    setFilters(next);
    setCurrentPage(1);
    setSelected(new Set());
  };

  const toggleSort = (col: string) => {
    const next = { ...pendingFilters };
    if (next.sort_by === col) {
      next.sort_dir = next.sort_dir === "asc" ? "desc" : "asc";
    } else {
      next.sort_by = col;
      next.sort_dir = "asc";
    }
    setPendingFilters(next);
    setFilters(next);
    setCurrentPage(1);
  };

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === pages.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(pages.map(p => p.id)));
    }
  };

  const exportSelected = () => {
    const selectedPages = pages.filter(p => selected.has(p.id));
    const headers = ["URL", "Status", "Response Time", "Title", "H1", "Word Count", "Internal Links", "Indexable", "Perf Score", "Issues"];
    const rows = selectedPages.map(p => [
      p.url,
      p.status_code ?? "",
      p.response_time != null ? (p.response_time * 1000).toFixed(0) + "ms" : "",
      p.title ?? "",
      p.h1 ?? "",
      p.word_count,
      p.internal_links_count,
      p.is_indexable ? "Yes" : "No",
      p.performance_score != null ? p.performance_score : "",
      p.issue_count,
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `selected_urls_crawl_${crawlId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const SortIcon = ({ col }: { col: string }) => {
    if (filters.sort_by !== col) return <span className="text-gray-300 ml-1">↕</span>;
    return <span className="text-blue-600 ml-1">{filters.sort_dir === "asc" ? "↑" : "↓"}</span>;
  };

  if (!crawlId && !loading) return (
    <div className="max-w-2xl mx-auto mt-12 text-center">
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-8">
        <p className="text-yellow-700 font-semibold">{error ?? "No crawl data available."}</p>
        <Link href={`/projects/${projectId}`} className="mt-4 inline-block text-blue-600 underline text-sm">← Back to project</Link>
      </div>
    </div>
  );

  return (
    <div className="max-w-full px-4 py-6 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
            <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
            <span>/</span>
            <span>URL Explorer</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">URL Explorer</h1>
          <p className="text-sm text-gray-500">{total.toLocaleString()} URLs found · Crawl #{crawlId}</p>
        </div>
        <div className="flex gap-2">
          {selected.size > 0 && (
            <button
              onClick={exportSelected}
              className="inline-flex items-center gap-2 bg-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-green-700"
            >
              ⬇ Export {selected.size} Selected
            </button>
          )}
          {crawlId && (
            <a href={api.exportCsv(crawlId)} download
              className="inline-flex items-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700">
              ⬇ Export All CSV
            </a>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <input
            type="text"
            placeholder="Search URL..."
            value={pendingFilters.search}
            onChange={e => handleSearchChange(e.target.value)}
            className="col-span-2 sm:col-span-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select value={pendingFilters.status_class} onChange={e => applyFilter("status_class", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            {STATUS_CLASSES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select value={pendingFilters.content_type} onChange={e => applyFilter("content_type", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            {CONTENT_TYPES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select value={pendingFilters.is_indexable} onChange={e => applyFilter("is_indexable", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            {INDEXABLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select value={pendingFilters.has_issues} onChange={e => applyFilter("has_issues", e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            {HAS_ISSUES_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <button onClick={() => { setFilters(INITIAL_FILTERS); setPendingFilters(INITIAL_FILTERS); setCurrentPage(1); setSelected(new Set()); }}
            className="text-sm text-gray-500 hover:text-red-600 border border-gray-200 rounded-lg px-3 py-2 hover:border-red-300 transition-colors">
            ✕ Reset
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          </div>
        ) : pages.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-4xl mb-3">🔍</p>
            <p className="font-medium">No pages match your filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left w-10">
                    <input type="checkbox"
                      checked={selected.size === pages.length && pages.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-300" />
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">
                    <button onClick={() => toggleSort("url")} className="flex items-center hover:text-blue-600">
                      URL <SortIcon col="url" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-gray-700">
                    <button onClick={() => toggleSort("status_code")} className="flex items-center hover:text-blue-600">
                      Status <SortIcon col="status_code" />
                    </button>
                  </th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-700 hidden md:table-cell">Type</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-700">
                    <button onClick={() => toggleSort("response_time")} className="flex items-center hover:text-blue-600">
                      RT <SortIcon col="response_time" />
                    </button>
                  </th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-700 hidden lg:table-cell">Indexable</th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-700">
                    <button onClick={() => toggleSort("word_count")} className="flex items-center hover:text-blue-600">
                      Words <SortIcon col="word_count" />
                    </button>
                  </th>
                  <th className="px-3 py-3 text-left font-semibold text-gray-700 hidden lg:table-cell">
                    <button onClick={() => toggleSort("performance_score")} className="flex items-center hover:text-blue-600">
                      Perf <SortIcon col="performance_score" />
                    </button>
                  </th>
                  <th className="px-3 py-3 text-right font-semibold text-gray-700">Issues</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {pages.map((p) => (
                  <tr
                    key={p.id}
                    className={`hover:bg-blue-50 cursor-pointer transition-colors ${selected.has(p.id) ? "bg-blue-50" : ""}`}
                    onClick={() => setDetailPage(p)}
                  >
                    <td className="px-4 py-2.5" onClick={e => e.stopPropagation()}>
                      <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleSelect(p.id)} className="rounded border-gray-300" />
                    </td>
                    <td className="px-4 py-2.5 max-w-xs">
                      <p className="truncate text-gray-800 font-medium" title={p.url}>
                        {p.url.replace(/^https?://[^/]+/, "") || "/"}
                      </p>
                      {p.title && <p className="truncate text-xs text-gray-400" title={p.title}>{p.title}</p>}
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge code={p.status_code} /></td>
                    <td className="px-3 py-2.5 hidden md:table-cell">
                      <span className="text-xs text-gray-500 truncate max-w-24 block">
                        {p.content_type?.split(";")[0] ?? "—"}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-xs text-gray-600">
                      {p.response_time != null ? `${(p.response_time * 1000).toFixed(0)}ms` : "—"}
                    </td>
                    <td className="px-3 py-2.5 hidden lg:table-cell">
                      {p.is_indexable
                        ? <span className="text-xs text-green-700 font-medium">✓</span>
                        : <span className="text-xs text-red-600 font-medium">noindex</span>}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-gray-600">{p.word_count || "—"}</td>
                    <td className="px-3 py-2.5 hidden lg:table-cell">
                      {p.performance_score != null ? (
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          p.performance_score >= 80 ? 'bg-green-100 text-green-700'
                          : p.performance_score >= 50 ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                        }`}>{p.performance_score}</span>
                      ) : <span className="text-gray-300 text-xs">—</span>}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {p.issue_count > 0 ? (
                        <span className="inline-block text-xs font-bold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">{p.issue_count}</span>
                      ) : (
                        <span className="text-xs text-green-600">✓</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Page {currentPage} of {totalPages} · {total.toLocaleString()} total
          </p>
          <div className="flex gap-1">
            <button onClick={() => setCurrentPage(1)} disabled={currentPage === 1}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">«</button>
            <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">‹</button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const start = Math.max(1, Math.min(currentPage - 2, totalPages - 4));
              const pg = start + i;
              return (
                <button key={pg} onClick={() => setCurrentPage(pg)}
                  className={`px-3 py-1.5 text-sm border rounded-lg ${pg === currentPage ? "bg-blue-600 text-white border-blue-600" : "border-gray-200 hover:bg-gray-50"}`}>
                  {pg}
                </button>
              );
            })}
            <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">›</button>
            <button onClick={() => setCurrentPage(totalPages)} disabled={currentPage === totalPages}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">»</button>
          </div>
        </div>
      )}

      {/* Detail Panel */}
      {detailPage && crawlId && (
        <DetailPanel page={detailPage} crawlId={crawlId} onClose={() => setDetailPage(null)} />
      )}
    </div>
  );
}
