"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type TopPage, type IssueTrendPoint, type IssuesSummary } from "@/lib/api";

interface Overview {
  crawl_id: number; status: string; total_pages: number; crawled_urls: number;
  failed_urls: number; critical_issues: number; warning_issues: number;
  info_issues: number; total_issues: number; avg_response_time_ms: number;
  avg_word_count: number; indexable_pages: number; noindex_pages: number;
  slow_pages: number; images_missing_alt: number;
  total_internal_links: number; total_external_links: number;
  status_distribution: { "2xx": number; "3xx": number; "4xx": number; "5xx": number };
}
interface TopIssue { issue_type: string; severity: string; count: number; label: string; }
interface RtBucket { range: string; count: number; }

const SEV_DOT: Record<string, string> = {
  critical: "bg-red-500", warning: "bg-yellow-500", info: "bg-blue-400",
};
const SEV_BADGE: Record<string, string> = {
  critical: "text-red-700 bg-red-50 border border-red-200",
  warning: "text-yellow-700 bg-yellow-50 border border-yellow-200",
  info: "text-blue-700 bg-blue-50 border border-blue-200",
};

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function BarChart({ buckets, maxVal }: { buckets: RtBucket[]; maxVal: number }) {
  return (
    <div className="space-y-2">
      {buckets.map((b) => (
        <div key={b.range} className="flex items-center gap-3 text-sm">
          <span className="w-16 text-gray-500 text-right text-xs">{b.range}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
            <div className="h-full bg-blue-500 rounded-full"
              style={{ width: maxVal > 0 ? `${(b.count / maxVal) * 100}%` : "0%" }} />
          </div>
          <span className="w-10 text-right font-medium text-gray-700">{b.count}</span>
        </div>
      ))}
    </div>
  );
}

function TrendChart({ data }: { data: IssueTrendPoint[] }) {
  if (!data.length) return <p className="text-gray-400 text-sm">Not enough crawl data for trend.</p>;
  const maxTotal = Math.max(...data.map(d => d.total_issues), 1);
  return (
    <div className="space-y-3">
      {data.map((point, i) => {
        const label = point.completed_at
          ? new Date(point.completed_at).toLocaleDateString("en", { month: "short", day: "numeric" })
          : `Crawl ${i + 1}`;
        const critW = maxTotal > 0 ? (point.critical_issues / maxTotal) * 100 : 0;
        const warnW = maxTotal > 0 ? (point.warning_issues / maxTotal) * 100 : 0;
        const infoW = maxTotal > 0 ? (point.info_issues / maxTotal) * 100 : 0;
        return (
          <div key={point.crawl_id} className="flex items-center gap-3 text-sm">
            <span className="w-16 text-gray-500 text-right text-xs shrink-0">{label}</span>
            <div className="flex-1 flex h-5 rounded overflow-hidden bg-gray-100">
              {critW > 0 && <div className="bg-red-500 h-full" style={{ width: `${critW}%` }} title={`Critical: ${point.critical_issues}`} />}
              {warnW > 0 && <div className="bg-yellow-400 h-full" style={{ width: `${warnW}%` }} title={`Warning: ${point.warning_issues}`} />}
              {infoW > 0 && <div className="bg-blue-400 h-full" style={{ width: `${infoW}%` }} title={`Info: ${point.info_issues}`} />}
            </div>
            <span className="w-12 text-right font-medium text-gray-700 shrink-0">{point.total_issues}</span>
          </div>
        );
      })}
      <div className="flex gap-4 text-xs text-gray-500 pt-1">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500 inline-block"/>Critical</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-400 inline-block"/>Warning</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-blue-400 inline-block"/>Info</span>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const params = useParams();
  const projectId = Number(params.id);
  const [crawlId, setCrawlId] = useState<number | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [topIssues, setTopIssues] = useState<TopIssue[]>([]);
  const [topPages, setTopPages] = useState<TopPage[]>([]);
  const [trend, setTrend] = useState<IssueTrendPoint[]>([]);
  const [summary, setSummary] = useState<IssuesSummary | null>(null);
  const [rtBuckets, setRtBuckets] = useState<RtBucket[]>([]);
  const [rtStats, setRtStats] = useState<{ avg: number; p50: number; p90: number; p95: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const project = await api.getProject(projectId);
      if (!project.last_crawl_id) {
        setError("No crawls found for this project. Start a crawl first.");
        setLoading(false);
        return;
      }
      const cid = project.last_crawl_id;
      setCrawlId(cid);
      const [ov, ti, rt, tp, tr, sm] = await Promise.all([
        api.getAnalyticsOverview(cid),
        api.getTopIssues(cid, 10),
        api.getResponseTimes(cid),
        api.getTopPages(cid, 10),
        api.getIssueTrend(projectId, 10),
        api.getIssuesSummary(cid),
      ]);
      setOverview(ov as Overview);
      setTopIssues(ti as TopIssue[]);
      setRtBuckets((rt as { buckets: RtBucket[] }).buckets ?? []);
      const rta = rt as { avg: number; p50: number; p90: number; p95: number };
      setRtStats({ avg: rta.avg, p50: rta.p50, p90: rta.p90, p95: rta.p95 });
      setTopPages(tp as TopPage[]);
      setTrend(tr as IssueTrendPoint[]);
      setSummary(sm as IssuesSummary);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="flex items-center justify-center min-h-96">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  );

  if (error) return (
    <div className="max-w-2xl mx-auto mt-12 text-center">
      <div className="bg-red-50 border border-red-200 rounded-xl p-8">
        <p className="text-red-600 font-semibold">{error}</p>
        <Link href={`/projects/${projectId}`} className="mt-4 inline-block text-blue-600 underline text-sm">Back to project</Link>
      </div>
    </div>
  );

  if (!overview) return null;

  const rtMax = Math.max(...rtBuckets.map(b => b.count), 1);
  const sdTotal = Object.values(overview.status_distribution).reduce((a, b) => a + b, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
            <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
            <span>/</span>
            <span>Analytics</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-sm text-gray-500">Crawl #{crawlId} · {overview.crawled_urls} pages</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link
            href={`/projects/${projectId}/urls`}
            className="inline-flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm font-medium hover:bg-gray-50"
          >
            🔍 URL Explorer
          </Link>
          {crawlId && (
            <a
              href={api.exportCsv(crawlId)}
              download
              className="inline-flex items-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700"
            >
              ⬇ Download CSV Report
            </a>
          )}
        </div>
      </div>

      {/* Issues Summary Banner */}
      {summary && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-100 p-6">
          <div className="flex flex-wrap gap-8 items-center">
            <div>
              <p className="text-sm text-gray-600 mb-1">Pages with Issues</p>
              <p className="text-4xl font-bold text-blue-700">{summary.pct_with_issues}%</p>
              <p className="text-xs text-gray-500 mt-1">{summary.pages_with_issues} of {summary.total_pages} pages</p>
            </div>
            <div className="flex-1 min-w-48">
              <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full transition-all"
                  style={{ width: `${summary.pct_with_issues}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0%</span>
                <span>100%</span>
              </div>
            </div>
            <div className="flex gap-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-red-600">{summary.critical_issues}</p>
                <p className="text-xs text-gray-500">Critical</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">{summary.warning_issues}</p>
                <p className="text-xs text-gray-500">Warnings</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600">{summary.info_issues}</p>
                <p className="text-xs text-gray-500">Info</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total Pages" value={overview.total_pages} />
        <StatCard label="Indexable" value={overview.indexable_pages} color="text-green-600" />
        <StatCard label="Noindex" value={overview.noindex_pages} color="text-yellow-600" />
        <StatCard label="Slow Pages" value={overview.slow_pages} sub="> 3s" color={overview.slow_pages > 0 ? "text-orange-600" : undefined} />
        <StatCard label="Images No Alt" value={overview.images_missing_alt} color={overview.images_missing_alt > 0 ? "text-red-600" : undefined} />
        <StatCard label="Avg Response" value={`${Math.round(overview.avg_response_time_ms)}ms`} />
      </div>

      {/* Issue Trend + Top Pages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Issue Trend */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📈 Issue Trend (Last 10 Crawls)</h2>
          <TrendChart data={trend} />
        </div>

        {/* Top Pages by Issues */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">🔥 Top 10 Pages by Issues</h2>
          {topPages.length === 0 ? (
            <p className="text-gray-400 text-sm">No issues found.</p>
          ) : (
            <div className="space-y-2">
              {topPages.map((p) => (
                <div key={p.page_id} className="flex items-center gap-2 text-sm group">
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-gray-800 font-medium group-hover:text-blue-600" title={p.url}>
                      {p.url.split('/').slice(3).join('/') || '/' || "/"}
                    </p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    {p.critical > 0 && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-semibold text-red-700 bg-red-50 border border-red-200">{p.critical}</span>
                    )}
                    {p.warning > 0 && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-semibold text-yellow-700 bg-yellow-50 border border-yellow-200">{p.warning}</span>
                    )}
                    {p.info > 0 && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200">{p.info}</span>
                    )}
                    <span className="px-1.5 py-0.5 rounded text-xs font-bold text-gray-700 bg-gray-100">{p.issue_count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Issue Types + Status Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">⚠️ Top Issue Types</h2>
          {topIssues.length === 0 ? (
            <p className="text-gray-400 text-sm">No issues found — great job! 🎉</p>
          ) : (
            <div className="space-y-2">
              {topIssues.map((issue) => (
                <div key={issue.issue_type} className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${SEV_DOT[issue.severity] ?? "bg-gray-400"}`} />
                  <span className="flex-1 text-sm text-gray-700 truncate">{issue.label}</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded ${SEV_BADGE[issue.severity] ?? "text-gray-600 bg-gray-50"}`}>
                    {issue.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📊 Status Distribution</h2>
          <div className="space-y-3">
            {Object.entries(overview.status_distribution).map(([code, count]) => {
              const colors: Record<string, string> = {
                "2xx": "bg-green-500", "3xx": "bg-yellow-400",
                "4xx": "bg-orange-500", "5xx": "bg-red-500",
              };
              const pct = sdTotal > 0 ? Math.round((count / sdTotal) * 100) : 0;
              return (
                <div key={code} className="flex items-center gap-3 text-sm">
                  <span className="w-10 text-gray-500 text-right font-mono text-xs">{code}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                    <div className={`h-full rounded-full ${colors[code] ?? "bg-gray-400"}`}
                      style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-12 text-right font-medium text-gray-700">{count}</span>
                  <span className="w-10 text-right text-gray-400 text-xs">{pct}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Response Time + Links */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">⚡ Response Time Distribution</h2>
          {rtStats && (
            <div className="flex gap-6 text-xs text-gray-500 mb-4">
              <span>Avg: <b>{(rtStats.avg * 1000).toFixed(0)}ms</b></span>
              <span>p50: <b>{(rtStats.p50 * 1000).toFixed(0)}ms</b></span>
              <span>p90: <b>{(rtStats.p90 * 1000).toFixed(0)}ms</b></span>
              <span>p95: <b>{(rtStats.p95 * 1000).toFixed(0)}ms</b></span>
            </div>
          )}
          <BarChart buckets={rtBuckets} maxVal={rtMax} />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">🔗 Link Summary</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-blue-700">{overview.total_internal_links.toLocaleString()}</p>
              <p className="text-sm text-gray-600 mt-1">Internal Links</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-purple-700">{overview.total_external_links.toLocaleString()}</p>
              <p className="text-sm text-gray-600 mt-1">External Links</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-gray-700">{overview.avg_word_count ? Math.round(Number(overview.avg_word_count)) : 0}</p>
              <p className="text-sm text-gray-600 mt-1">Avg Word Count</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-green-700">{Math.round(overview.avg_response_time_ms)}ms</p>
              <p className="text-sm text-gray-600 mt-1">Avg Response</p>
            </div>
          </div>
        </div>
      </div>

      {/* Exports */}
      {crawlId && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">📥 Export Reports</h2>
          <div className="flex flex-wrap gap-3">
            <a href={api.exportCsv(crawlId)} download
              className="inline-flex items-center gap-2 bg-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-green-700">
              ⬇ CSV Report
            </a>
            <a href={api.exportJson(crawlId)} download
              className="inline-flex items-center gap-2 bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700">
              ⬇ JSON Export
            </a>
            <a href={api.exportSitemap(crawlId)} download
              className="inline-flex items-center gap-2 bg-purple-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-purple-700">
              ⬇ Sitemap XML
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
