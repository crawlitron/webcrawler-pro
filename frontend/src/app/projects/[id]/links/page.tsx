
"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

interface LinkItem {
  source_url: string;
  target_url: string;
  anchor_text: string;
  link_type: "internal" | "external";
  nofollow: boolean;
  status_code?: number;
}

interface LinksResponse {
  items: LinkItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

const STATUS_COLOR: Record<number, string> = {};
function statusBadge(code?: number) {
  if (!code) return "bg-gray-100 text-gray-500";
  if (code < 300) return "bg-green-100 text-green-700";
  if (code < 400) return "bg-yellow-100 text-yellow-700";
  if (code < 500) return "bg-orange-100 text-orange-700";
  return "bg-red-100 text-red-700";
}

export default function LinksPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [crawlId, setCrawlId] = useState<number | null>(null);
  const [links, setLinks] = useState<LinkItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [linkType, setLinkType] = useState<string>("");
  const [nofollowFilter, setNofollowFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  useEffect(() => {
    api.getProject(projectId).then((p) => {
      if (p.last_crawl_id) setCrawlId(p.last_crawl_id);
      else setError("No crawls found. Start a crawl first.");
      setLoading(false);
    }).catch((e: unknown) => {
      setError(e instanceof Error ? e.message : "Failed to load project");
      setLoading(false);
    });
  }, [projectId]);

  const fetchLinks = useCallback(async () => {
    if (!crawlId) return;
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = { page, page_size: 50 };
      if (linkType) params.link_type = linkType;
      if (nofollowFilter !== "") params.nofollow = nofollowFilter === "true";
      const data = await api.getCrawlLinks(crawlId, params) as LinksResponse;
      // Client-side search filter
      let items = data.items;
      if (search) {
        const q = search.toLowerCase();
        items = items.filter(
          (l) => l.target_url.toLowerCase().includes(q) || l.anchor_text.toLowerCase().includes(q)
        );
      }
      setLinks(items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load links");
    } finally {
      setLoading(false);
    }
  }, [crawlId, page, linkType, nofollowFilter, search]);

  useEffect(() => { fetchLinks(); }, [fetchLinks]);

  const broken = links.filter((l) => l.status_code && l.status_code >= 400);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <a href={`/projects/${projectId}`} className="text-sm text-blue-600 hover:underline mb-1 inline-block">
            Back to Project
          </a>
          <h1 className="text-2xl font-bold text-gray-900">Links Explorer</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total.toLocaleString()} links found
            {broken.length > 0 && (
              <span className="ml-2 text-red-600 font-medium">{broken.length} broken</span>
            )}
          </p>
        </div>
        <a href={`/projects/${projectId}/analytics`}
          className="text-sm bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-lg text-gray-700 transition">
          Analytics
        </a>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 shadow-sm">
        <div className="flex flex-wrap gap-3">
          <select
            value={linkType}
            onChange={(e) => { setLinkType(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Links</option>
            <option value="internal">Internal Only</option>
            <option value="external">External Only</option>
          </select>

          <select
            value={nofollowFilter}
            onChange={(e) => { setNofollowFilter(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Follow + Nofollow</option>
            <option value="false">Follow Only</option>
            <option value="true">Nofollow Only</option>
          </select>

          <div className="flex gap-2 flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search URL or anchor text..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { setSearch(searchInput); setPage(1); } }}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={() => { setSearch(searchInput); setPage(1); }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition"
            >
              Search
            </button>
            {search && (
              <button
                onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
                className="border border-gray-300 text-gray-600 px-3 py-2 rounded-lg text-sm hover:bg-gray-50"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      {error ? (
        <div className="text-center py-12 text-gray-500">{error}</div>
      ) : loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : links.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500">No links found matching your filters.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target URL</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Anchor Text</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rel</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {links.map((link, idx) => (
                  <tr key={idx} className={`hover:bg-gray-50 ${
                    link.status_code && link.status_code >= 400 ? "bg-red-50 hover:bg-red-100" : ""
                  }`}>
                    <td className="px-4 py-3 text-sm max-w-xs">
                      <a href={link.target_url} target="_blank" rel="noopener noreferrer"
                        className="text-blue-600 hover:underline truncate block" title={link.target_url}>
                        {link.target_url.length > 60 ? link.target_url.substring(0, 60) + "..." : link.target_url}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 max-w-[160px] truncate" title={link.anchor_text}>
                      {link.anchor_text || <span className="text-gray-400 italic">no text</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        link.link_type === "internal"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-purple-100 text-purple-700"
                      }`}>
                        {link.link_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {link.status_code ? (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusBadge(link.status_code)}`}>
                          {link.status_code}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {link.nofollow ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">nofollow</span>
                      ) : (
                        <span className="text-gray-400 text-xs">follow</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate" title={link.source_url}>
                      {link.source_url.replace(/^https?:\/\/[^/]+/, "") || "/"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
              <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
