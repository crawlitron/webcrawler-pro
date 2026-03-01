"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type MobileSummary, type MobilePageIssue } from "@/lib/api";

// ── Score Color Helpers ───────────────────────────────────────────────────────
const SCORE_COLOR = (score: number | null) => {
  if (score === null) return { text: "text-gray-400", bg: "bg-gray-100", bar: "bg-gray-300", label: "N/A" };
  if (score >= 80) return { text: "text-green-700", bg: "bg-green-50", bar: "bg-green-500", label: "Good" };
  if (score >= 50) return { text: "text-yellow-700", bg: "bg-yellow-50", bar: "bg-yellow-500", label: "Needs Improvement" };
  return { text: "text-red-700", bg: "bg-red-50", bar: "bg-red-500", label: "Poor" };
};

const ISSUE_BADGE_COLOR: Record<string, string> = {
  viewport_missing: "bg-red-100 text-red-700 border-red-200",
  viewport_not_scalable: "bg-yellow-100 text-yellow-700 border-yellow-200",
  small_fonts: "bg-orange-100 text-orange-700 border-orange-200",
  small_touch_targets: "bg-red-100 text-red-700 border-red-200",
  no_media_queries: "bg-yellow-100 text-yellow-700 border-yellow-200",
  non_responsive_images: "bg-blue-100 text-blue-700 border-blue-200",
  horizontal_scroll: "bg-red-100 text-red-700 border-red-200",
  missing_mobile_theme: "bg-gray-100 text-gray-700 border-gray-200",
};

type Tab = "overview" | "issues" | "problems" | "comparison";

export default function MobileSeoPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [summary, setSummary] = useState<MobileSummary | null>(null);
  const [issues, setIssues] = useState<MobilePageIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [scoreFilter, setScoreFilter] = useState<[number, number]>([0, 100]);
  const [searchUrl, setSearchUrl] = useState("");
  const [sortBy, setSortBy] = useState<"score" | "issues">("score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryData, issuesData] = await Promise.all([
        api.getMobileSummary(projectId),
        api.getMobileIssues(projectId, { limit: 100 }),
      ]);
      setSummary(summaryData);
      setIssues(issuesData.pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load mobile data");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  // Filter and sort issues
  const filteredIssues = issues
    .filter((page) => {
      if (page.mobile_score < scoreFilter[0] || page.mobile_score > scoreFilter[1]) return false;
      if (searchUrl && !page.url.toLowerCase().includes(searchUrl.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => {
      const direction = sortOrder === "asc" ? 1 : -1;
      if (sortBy === "score") {
        return (a.mobile_score - b.mobile_score) * direction;
      }
      return (a.issues_count - b.issues_count) * direction;
    });

  const topProblems = [...issues]
    .sort((a, b) => a.mobile_score - b.mobile_score)
    .slice(0, 10);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
          <p className="font-semibold">Error loading mobile data</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!summary || summary.crawl_id === null) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
          <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
          <span>/</span>
          <span>Mobile SEO</span>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
          <div className="text-4xl mb-3">📱</div>
          <h2 className="text-xl font-semibold text-gray-700 mb-2">No Crawl Data</h2>
          <p className="text-gray-500 text-sm">Run a crawl first to analyze mobile SEO.</p>
          <Link
            href={`/projects/${projectId}`}
            className="mt-4 inline-block bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Go to Project
          </Link>
        </div>
      </div>
    );
  }

  const avgScore = summary.average_score;
  const scoreColor = SCORE_COLOR(avgScore);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
        <span>/</span>
        <span className="text-gray-800 font-medium">Mobile SEO</span>
      </div>

      {/* Hero Score Card */}
      <div className={`rounded-2xl border p-6 ${scoreColor.bg}`}>
        <div className="flex flex-col md:flex-row items-center gap-6">
          <div className="text-center shrink-0">
            <div className={`text-7xl font-black ${scoreColor.text}`}>
              {Math.round(avgScore)}
            </div>
            <div className={`text-sm font-semibold mt-1 ${scoreColor.text}`}>{scoreColor.label}</div>
            <div className="text-xs text-gray-500 mt-0.5">Mobile Score</div>
          </div>

          <div className="flex-1 w-full">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                <div className="text-xl font-bold text-gray-800">{summary.total_pages}</div>
                <div className="text-xs text-gray-500">Pages</div>
              </div>
              <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                <div className="text-xl font-bold text-red-600">{summary.pages_with_issues}</div>
                <div className="text-xs text-gray-500">With Issues</div>
              </div>
              <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                <div className="text-xl font-bold text-green-600">
                  {summary.total_pages - summary.pages_with_issues}
                </div>
                <div className="text-xs text-gray-500">Clean</div>
              </div>
              <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                <div className="text-xl font-bold text-gray-800">
                  {summary.total_pages > 0
                    ? Math.round(((summary.total_pages - summary.pages_with_issues) / summary.total_pages) * 100)
                    : 0}%
                </div>
                <div className="text-xs text-gray-500">Pass Rate</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Score Distribution */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Score Distribution</h3>
        <div className="grid grid-cols-5 gap-3">
          {Object.entries(summary.score_distribution).map(([range, count]) => {
            const pct = summary.total_pages > 0 ? Math.round((count / summary.total_pages) * 100) : 0;
            let color = "bg-red-500";
            if (range === "81-100") color = "bg-green-500";
            else if (range === "61-80") color = "bg-yellow-500";
            else if (range === "41-60") color = "bg-orange-500";
            else if (range === "21-40") color = "bg-red-400";

            return (
              <div key={range} className="text-center">
                <div className="text-2xl font-bold text-gray-800">{count}</div>
                <div className="text-xs text-gray-500 mb-2">{range}</div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
                </div>
                <div className="text-xs text-gray-400 mt-1">{pct}%</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {(["overview", "issues", "problems"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab === "overview" && "📊 Overview"}
              {tab === "issues" && `🔍 Issues (${issues.length})`}
              {tab === "problems" && "⚠️ Top Problems"}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Mobile Optimization Checks</h2>
          <div className="grid gap-3">
            {[
              { key: "viewport_meta", label: "Viewport Meta Tag", weight: 15 },
              { key: "viewport_scalable", label: "Viewport Scalable", weight: 10 },
              { key: "font_size_readable", label: "Readable Font Sizes", weight: 10 },
              { key: "tap_targets_ok", label: "Touch Targets Properly Sized", weight: 15 },
              { key: "media_queries_detected", label: "Media Queries Detected", weight: 15 },
              { key: "responsive_images", label: "Responsive Images", weight: 10 },
              { key: "mobile_meta_theme", label: "Mobile Theme Color", weight: 5 },
              { key: "no_horizontal_scroll", label: "No Horizontal Scroll", weight: 10 },
              { key: "amp_page", label: "AMP Support", weight: 5 },
              { key: "structured_nav", label: "Structured Navigation", weight: 5 },
            ].map((check) => {
              const passCount = issues.filter(
                (p) => p.mobile_check && (p.mobile_check as any)[check.key] === true
              ).length;
              const passRate = issues.length > 0 ? Math.round((passCount / issues.length) * 100) : 0;
              const color = passRate >= 80 ? "bg-green-500" : passRate >= 50 ? "bg-yellow-500" : "bg-red-500";

              return (
                <div key={check.key} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-800">{check.label}</span>
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                        {check.weight} pts
                      </span>
                    </div>
                    <div className="text-sm font-medium text-gray-600">
                      {passCount}/{issues.length} ({passRate}%)
                    </div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className={`h-2 rounded-full transition-all ${color}`} style={{ width: `${passRate}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Issues Tab */}
      {activeTab === "issues" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3 items-center bg-gray-50 rounded-xl p-3 border border-gray-200">
            <input
              type="text"
              placeholder="Search URLs..."
              value={searchUrl}
              onChange={(e) => setSearchUrl(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            />

            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-600">Score Range:</label>
              <input
                type="number"
                min={0}
                max={100}
                value={scoreFilter[0]}
                onChange={(e) => setScoreFilter([Number(e.target.value), scoreFilter[1]])}
                className="border border-gray-200 rounded px-2 py-1 text-sm w-16 bg-white"
              />
              <span className="text-xs text-gray-400">to</span>
              <input
                type="number"
                min={0}
                max={100}
                value={scoreFilter[1]}
                onChange={(e) => setScoreFilter([scoreFilter[0], Number(e.target.value)])}
                className="border border-gray-200 rounded px-2 py-1 text-sm w-16 bg-white"
              />
            </div>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "score" | "issues")}
              className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white"
            >
              <option value="score">Sort by Score</option>
              <option value="issues">Sort by Issues Count</option>
            </select>

            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}
              className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white"
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>

            <span className="text-xs text-gray-400 ml-auto">{filteredIssues.length} pages</span>
          </div>

          {/* Issues Table */}
          <div className="space-y-2">
            {filteredIssues.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                No pages match the filters
              </div>
            ) : (
              filteredIssues.map((page) => {
                const sc = SCORE_COLOR(page.mobile_score);
                return (
                  <div key={page.page_id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{page.url}</p>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {page.mobile_issues.slice(0, 5).map((issue, idx) => (
                            <span
                              key={idx}
                              className={`text-xs px-2 py-0.5 rounded-full border ${
                                ISSUE_BADGE_COLOR[issue] || "bg-gray-100 text-gray-700 border-gray-200"
                              }`}
                            >
                              {issue.replace(/_/g, " ")}
                            </span>
                          ))}
                          {page.mobile_issues.length > 5 && (
                            <span className="text-xs text-gray-400">+{page.mobile_issues.length - 5} more</span>
                          )}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className={`text-2xl font-bold ${sc.text}`}>{Math.round(page.mobile_score)}</div>
                        <div className="text-xs text-gray-500">{page.issues_count} issues</div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Top Problems Tab */}
      {activeTab === "problems" && (
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-gray-800">Worst-Scoring Pages (Bottom 10)</h2>
          {topProblems.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              No problematic pages found
            </div>
          ) : (
            topProblems.map((page, idx) => {
              const sc = SCORE_COLOR(page.mobile_score);
              return (
                <div key={page.page_id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                  <div className="flex items-start gap-4">
                    <div className={`text-2xl font-bold ${sc.text} shrink-0`}>#{idx + 1}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{page.url}</p>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {page.mobile_issues.map((issue, i) => (
                          <span
                            key={i}
                            className={`text-xs px-2 py-0.5 rounded-full border ${
                              ISSUE_BADGE_COLOR[issue] || "bg-gray-100 text-gray-700 border-gray-200"
                            }`}
                          >
                            {issue.replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className={`text-3xl font-black ${sc.text} shrink-0`}>
                      {Math.round(page.mobile_score)}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
