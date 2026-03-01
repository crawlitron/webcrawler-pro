"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type AccessibilityAnalytics, type A11yIssueType } from "@/lib/api";

const SCORE_COLOR = (score: number | null) => {
  if (score === null) return { text: "text-gray-400", bg: "bg-gray-100", bar: "bg-gray-300", label: "N/A" };
  if (score >= 80) return { text: "text-green-600", bg: "bg-green-50", bar: "bg-green-500", label: "Good" };
  if (score >= 50) return { text: "text-yellow-600", bg: "bg-yellow-50", bar: "bg-yellow-500", label: "Needs Improvement" };
  return { text: "text-red-600", bg: "bg-red-50", bar: "bg-red-500", label: "Poor" };
};

const SEV_BADGE = (sev: string) => {
  if (sev === "critical") return "bg-red-100 text-red-700 border border-red-200";
  if (sev === "warning") return "bg-yellow-100 text-yellow-700 border border-yellow-200";
  return "bg-blue-100 text-blue-700 border border-blue-200";
};

const CAT_ICONS: Record<string, string> = {
  Perceivable: "👁",
  Operable: "⌨️",
  Understandable: "🧠",
  Robust: "🔧",
  BFSG: "🇩🇪",
  Other: "📋",
};

const WCAG_CATEGORIES = ["Perceivable", "Operable", "Understandable", "Robust", "BFSG"];

export default function AccessibilityPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [data, setData] = useState<AccessibilityAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "issues" | "bfsg" | "urls">("overview");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const result = await api.getAccessibilityAnalytics(projectId);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load accessibility data");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const filteredIssues = (data?.issues_by_type ?? []).filter((issue: A11yIssueType) => {
    const catMatch = filterCategory === "all" || issue.category === filterCategory;
    const sevMatch = filterSeverity === "all" ||
      (filterSeverity === "critical" && issue.critical > 0) ||
      (filterSeverity === "warning" && issue.warning > 0) ||
      (filterSeverity === "info" && issue.info > 0);
    const searchMatch = searchTerm === "" ||
      issue.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      issue.issue_type.toLowerCase().includes(searchTerm.toLowerCase());
    return catMatch && sevMatch && searchMatch;
  });

  if (loading) return (
    <div className="flex items-center justify-center min-h-96">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  );

  if (error) return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        <p className="font-semibold">Failed to load accessibility data</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    </div>
  );

  if (!data || data.crawl_id === null) return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
        <span>/</span><span>Accessibility</span>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <div className="text-4xl mb-3">♿</div>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">No Crawl Data Yet</h2>
        <p className="text-gray-500 text-sm">Run a crawl first to see accessibility analysis.</p>
        <Link href={`/projects/${projectId}`}
          className="mt-4 inline-block bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          Go to Project
        </Link>
      </div>
    </div>
  );

  const score = data.wcag_score;
  const scoreStyle = SCORE_COLOR(score);
  const bfsg = data.bfsg_checklist;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
        <span>/</span><span className="text-gray-800 font-medium">Accessibility</span>
        <span className="ml-auto text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">WCAG 2.1 AA · BFSG 2025</span>
      </div>

      {/* Score Hero */}
      <div className={`rounded-2xl border p-8 ${scoreStyle.bg} flex flex-col md:flex-row items-center gap-8`}>
        <div className="text-center">
          <div className={`text-7xl font-black ${scoreStyle.text}`}>
            {score !== null ? score : "—"}
          </div>
          <div className={`text-sm font-semibold mt-1 ${scoreStyle.text}`}>{scoreStyle.label}</div>
          <div className="text-xs text-gray-500 mt-0.5">WCAG Score / 100</div>
        </div>
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-2xl font-bold text-gray-800">{data.total_pages}</div>
            <div className="text-xs text-gray-500 mt-1">Pages Analyzed</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-2xl font-bold text-red-600">{data.issues_by_severity.critical}</div>
            <div className="text-xs text-gray-500 mt-1">Critical Issues</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-2xl font-bold text-yellow-600">{data.issues_by_severity.warning}</div>
            <div className="text-xs text-gray-500 mt-1">Warnings</div>
          </div>
          <div className="bg-white rounded-xl p-4 text-center shadow-sm">
            <div className="text-2xl font-bold text-green-600">{bfsg.passed}/{bfsg.total}</div>
            <div className="text-xs text-gray-500 mt-1">BFSG Checks Passed</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px">
          {(["overview", "issues", "bfsg", "urls"] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}>
              {tab === "overview" && "📊 Overview"}
              {tab === "issues" && `🔍 Issues (${data.accessibility_issues})`}
              {tab === "bfsg" && `🇩🇪 BFSG Checklist (${bfsg.compliance_pct}%)`}
              {tab === "urls" && `🌐 Top Affected URLs`}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">WCAG 2.1 Category Scores</h2>
          <div className="grid gap-4">
            {WCAG_CATEGORIES.map(cat => {
              const catData = data.issues_by_category[cat];
              if (!catData) return null;
              const catScore = catData.score ?? 0;
              const catStyle = SCORE_COLOR(catScore);
              return (
                <div key={cat} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{CAT_ICONS[cat] || "📋"}</span>
                      <span className="font-semibold text-gray-800">{cat}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-red-600 font-medium">{catData.critical} critical</span>
                      <span className="text-xs text-yellow-600 font-medium">{catData.warning} warnings</span>
                      <span className="text-xs text-blue-600 font-medium">{catData.info} info</span>
                      <span className={`text-lg font-bold ${catStyle.text}`}>{catScore}</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full transition-all ${catStyle.bar}`}
                      style={{ width: `${catScore}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Crawl info */}
          {data.crawl_completed_at && (
            <p className="text-xs text-gray-400 text-right">
              Analysis from crawl completed {new Date(data.crawl_completed_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* Tab: Issues */}
      {activeTab === "issues" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <input
              type="text"
              placeholder="Search issues..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
            />
            <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="all">All Categories</option>
              {WCAG_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
            <span className="text-sm text-gray-400 py-1.5">{filteredIssues.length} issue type(s)</span>
          </div>

          <div className="space-y-3">
            {filteredIssues.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                No issues match your filters
              </div>
            ) : filteredIssues.map((issue: A11yIssueType) => (
              <div key={issue.issue_type} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-xs font-medium text-gray-500">{CAT_ICONS[issue.category] || ""} {issue.category}</span>
                      {issue.critical > 0 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("critical")}`}>
                          {issue.critical} critical
                        </span>
                      )}
                      {issue.warning > 0 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("warning")}`}>
                          {issue.warning} warnings
                        </span>
                      )}
                      {issue.info > 0 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("info")}`}>
                          {issue.info} info
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-gray-800">{issue.description}</p>
                    {issue.recommendation && (
                      <p className="text-xs text-gray-500 mt-1">💡 {issue.recommendation}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xl font-bold text-gray-700">{issue.total}</div>
                    <div className="text-xs text-gray-400">occurrences</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: BFSG Checklist */}
      {activeTab === "bfsg" && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-blue-900">BFSG Compliance Status</h3>
                <p className="text-sm text-blue-700 mt-0.5">
                  Barrierefreiheitsstärkungsgesetz — gilt für private Unternehmen ab 28. Juni 2025
                </p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-black text-blue-700">{bfsg.compliance_pct}%</div>
                <div className="text-xs text-blue-600">{bfsg.passed}/{bfsg.total} passed</div>
              </div>
            </div>
            <div className="mt-3 w-full bg-blue-200 rounded-full h-3">
              <div className="bg-blue-600 h-3 rounded-full transition-all" style={{ width: `${bfsg.compliance_pct}%` }} />
            </div>
          </div>

          <div className="space-y-2">
            {bfsg.checks.map(check => (
              <div key={check.id}
                className={`flex items-start gap-4 p-4 rounded-xl border ${
                  check.passed
                    ? "bg-green-50 border-green-200"
                    : "bg-red-50 border-red-200"
                }`}>
                <div className={`text-xl mt-0.5 ${check.passed ? "text-green-600" : "text-red-500"}`}>
                  {check.passed ? "✅" : "❌"}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-gray-800">{check.title}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                      {check.wcag} · {check.level}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">{check.description}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-500">
            <strong>Hinweis:</strong> Diese Analyse prüft automatisch erkennbare technische Barrierefreiheits-Kriterien.
            Eine vollständige BFSG-Konformität erfordert zusätzlich manuelle Tests (z.B. Screenreader-Tests, Farbkontrast-Prüfung).
          </div>
        </div>
      )}

      {/* Tab: Top Affected URLs */}
      {activeTab === "urls" && (
        <div className="space-y-3">
          {data.top_affected_urls.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              No pages with accessibility issues found
            </div>
          ) : data.top_affected_urls.map(page => (
            <div key={page.page_id} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {page.title || page.url}
                  </p>
                  <p className="text-xs text-gray-400 truncate mt-0.5">{page.url}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {page.critical > 0 && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("critical")}`}>
                      {page.critical} crit
                    </span>
                  )}
                  {page.warning > 0 && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("warning")}`}>
                      {page.warning} warn
                    </span>
                  )}
                  {page.info > 0 && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("info")}`}>
                      {page.info} info
                    </span>
                  )}
                  <span className="text-sm font-bold text-gray-600 w-8 text-right">{page.total}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
