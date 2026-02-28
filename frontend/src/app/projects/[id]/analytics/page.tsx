"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

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
  critical: "text-red-700 bg-red-50 border-red-200",
  warning: "text-yellow-700 bg-yellow-50 border-yellow-200",
  info: "text-blue-700 bg-blue-50 border-blue-200",
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

export default function AnalyticsPage() {
  const params = useParams();
  const projectId = Number(params.id);
  const [crawlId, setCrawlId] = useState<number | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [topIssues, setTopIssues] = useState<TopIssue[]>([]);
  const [rtBuckets, setRtBuckets] = useState<RtBucket[]>([]);
  const [rtStats, setRtStats] = useState<{ avg: number; p50: number; p90: number; p95: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const project = await api.getProject(projectId);
        if (!project.last_crawl_id) {
          setError("No crawls found for this project. Start a crawl first.");
          setLoading(false);
          return;
        }
        const cid = project.last_crawl_id;
        setCrawlId(cid);
        const [ov, ti, rt] = await Promise.all([
          api.getAnalyticsOverview(cid),
          api.getTopIssues(cid, 10),
          api.getResponseTimes(cid),
        ]);
        setOverview(ov as Overview);
        setTopIssues(ti as TopIssue[]);
        setRtBuckets((rt as {buckets: RtBucket[]}).buckets ?? []);
        const rta = rt as {avg:number;p50:number;p90:number;p95:number};
        setRtStats({ avg: rta.avg, p50: rta.p50, p90: rta.p90, p95: rta.p95 });
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [projectId]);

  if (loading) return (
    <div className="flex items-center justify-center min-h-96">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  );
  if (error) return (
    <div className="max-w-4xl mx-auto px-6 py-12 text-center">
      <p className="text-gray-500">{error}</p>
      <a href={`/projects/${projectId}`} className="mt-4 inline-block text-blue-600 hover:underline">\u2190 Back</a>
    </div>
  );
  if (!overview) return null;

  const issueTotal = overview.critical_issues + overview.warning_issues + overview.info_issues;
  const statusTotal = Object.values(overview.status_distribution).reduce((a, b) => a + b, 0);
  const maxBucket = rtBuckets.length > 0 ? Math.max(...rtBuckets.map((b) => b.count)) : 1;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <a href={`/projects/${projectId}`} className="text-sm text-blue-600 hover:underline mb-1 inline-block">
            \u2190 Back to Project
          </a>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 text-sm mt-0.5">Crawl #{crawlId} \u2014 Detailed metrics</p>
        </div>
        <a href={`/projects/${projectId}/links`}
          className="text-sm bg-gray-100 hover:bg-gray-200 px-4 py-2 rounded-lg text-gray-700 transition">
          View Links \u2192
        </a>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <StatCard label="Pages Crawled" value={overview.crawled_urls.toLocaleString()} />
        <StatCard label="Critical Issues" value={overview.critical_issues} color="text-red-600" />
        <StatCard label="Warnings" value={overview.warning_issues} color="text-yellow-600" />
        <StatCard label="Avg Response" value={`${overview.avg_response_time_ms}ms`} sub={`${overview.slow_pages} slow`} />
        <StatCard label="Indexable" value={overview.indexable_pages} sub={`${overview.noindex_pages} noindex`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Issue Distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Issue Distribution</h2>
          {issueTotal === 0 ? <p className="text-gray-400 text-sm">No issues found \uD83C\uDF89</p> : (
            <>
              <div className="flex h-4 rounded-full overflow-hidden mb-4">
                {overview.critical_issues > 0 && <div className="bg-red-500" style={{width:`${(overview.critical_issues/issueTotal)*100}%`}} />}
                {overview.warning_issues > 0 && <div className="bg-yellow-400" style={{width:`${(overview.warning_issues/issueTotal)*100}%`}} />}
                {overview.info_issues > 0 && <div className="bg-blue-400" style={{width:`${(overview.info_issues/issueTotal)*100}%`}} />}
              </div>
              <div className="space-y-2">
                {([
                  {label:"Critical",val:overview.critical_issues,color:"bg-red-500"},
                  {label:"Warning",val:overview.warning_issues,color:"bg-yellow-400"},
                  {label:"Info",val:overview.info_issues,color:"bg-blue-400"},
                ] as {label:string;val:number;color:string}[]).map(({label,val,color})=>(
                  <div key={label} className="flex items-center gap-2 text-sm">
                    <span className={`w-3 h-3 rounded-full ${color}`} />
                    <span className="flex-1 text-gray-600">{label}</span>
                    <span className="font-semibold">{val}</span>
                    <span className="text-gray-400 w-10 text-right">{issueTotal>0?Math.round(val/issueTotal*100):0}%</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Status Distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Status Code Distribution</h2>
          <div className="space-y-3">
            {([
              {key:"2xx",label:"2xx OK",color:"bg-green-500"},
              {key:"3xx",label:"3xx Redirect",color:"bg-yellow-400"},
              {key:"4xx",label:"4xx Client Error",color:"bg-orange-500"},
              {key:"5xx",label:"5xx Server Error",color:"bg-red-500"},
            ] as {key:string;label:string;color:string}[]).map(({key,label,color})=>{
              const val = overview.status_distribution[key as keyof typeof overview.status_distribution]??0;
              return (
                <div key={key}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{label}</span>
                    <span className="font-medium">{val}</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className={`h-full ${color} rounded-full`} style={{width:statusTotal>0?`${val/statusTotal*100}%`:"0%"}} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Content Stats */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Content Stats</h2>
          <div className="space-y-3">
            {[
              {label:"Avg. Word Count",value:overview.avg_word_count.toLocaleString(),icon:"\uD83D\uDCDD"},
              {label:"Missing Alt Text",value:overview.images_missing_alt.toLocaleString(),icon:"\uD83D\uDDBC\uFE0F"},
              {label:"Internal Links",value:overview.total_internal_links.toLocaleString(),icon:"\uD83D\uDD17"},
              {label:"External Links",value:overview.total_external_links.toLocaleString(),icon:"\u2197\uFE0F"},
              {label:"Failed URLs",value:overview.failed_urls.toLocaleString(),icon:"\u274C"},
            ].map(({label,value,icon})=>(
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-gray-500">{icon} {label}</span>
                <span className="font-semibold text-gray-800">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Response Time Histogram */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-1">Response Time Distribution</h2>
          {rtStats && (
            <div className="flex gap-4 text-xs text-gray-500 mb-4">
              <span>Avg: <b>{(rtStats.avg*1000).toFixed(0)}ms</b></span>
              <span>P50: <b>{(rtStats.p50*1000).toFixed(0)}ms</b></span>
              <span>P90: <b>{(rtStats.p90*1000).toFixed(0)}ms</b></span>
              <span>P95: <b>{(rtStats.p95*1000).toFixed(0)}ms</b></span>
            </div>
          )}
          {rtBuckets.length>0 ? <BarChart buckets={rtBuckets} maxVal={maxBucket} /> :
            <p className="text-gray-400 text-sm">No response time data available</p>}
        </div>

        {/* Top Issues */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Top 10 Issues</h2>
          {topIssues.length===0 ? <p className="text-gray-400 text-sm">No issues found \uD83C\uDF89</p> : (
            <div className="space-y-2">
              {topIssues.map((issue)=>(
                <div key={`${issue.issue_type}-${issue.severity}`} className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${SEV_DOT[issue.severity]??"bg-gray-400"}`} />
                  <span className="flex-1 text-sm text-gray-700 truncate" title={issue.label}>{issue.label}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${SEV_BADGE[issue.severity]??""}`}>
                    {issue.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
