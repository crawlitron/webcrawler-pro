const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export interface Project {
  id: number;
  name: string;
  start_url: string;
  max_urls: number;
  custom_user_agent?: string | null;
  crawl_delay: number;
  include_patterns?: string[] | null;
  exclude_patterns?: string[] | null;
  crawl_external_links: boolean;
  crawl_schedule?: string | null;
  use_js_rendering?: boolean;   // v0.8.0
  js_wait_time?: number;        // v0.8.0
  created_at: string;
  updated_at: string;
  last_crawl_status?: string;
  last_crawl_id?: number;
}

export interface ProjectCreate {
  name: string;
  start_url: string;
  max_urls?: number;
  custom_user_agent?: string | null;
  crawl_delay?: number;
  include_patterns?: string[] | null;
  exclude_patterns?: string[] | null;
  crawl_external_links?: boolean;
  crawl_schedule?: string | null;
  use_js_rendering?: boolean;   // v0.8.0
  js_wait_time?: number;        // v0.8.0
}

export interface ProjectUpdate {
  name?: string;
  start_url?: string;
  max_urls?: number;
  custom_user_agent?: string | null;
  crawl_delay?: number;
  include_patterns?: string[] | null;
  exclude_patterns?: string[] | null;
  crawl_external_links?: boolean;
  crawl_schedule?: string | null;
  use_js_rendering?: boolean;   // v0.8.0
  js_wait_time?: number;        // v0.8.0
}

export interface Crawl {
  id: number;
  project_id: number;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  celery_task_id?: string;
  total_urls: number;
  crawled_urls: number;
  failed_urls: number;
  critical_issues: number;
  warning_issues: number;
  info_issues: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  error_message?: string;
  progress_percent?: number;
}

export interface Page {
  id: number;
  crawl_id: number;
  url: string;
  status_code?: number;
  content_type?: string;
  response_time?: number;
  title?: string;
  meta_description?: string;
  h1?: string;
  h2_count: number;
  canonical_url?: string;
  internal_links_count: number;
  external_links_count: number;
  images_without_alt: number;
  word_count: number;
  is_indexable: boolean;
  redirect_url?: string;
  depth: number;
  crawled_at: string;
  issue_count: number;
  extra_data?: Record<string, unknown>;
  performance_score?: number | null;
}

export interface PageListResponse {
  items: Page[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Issue {
  id: number;
  crawl_id: number;
  page_id: number;
  page_url?: string;
  severity: "critical" | "warning" | "info";
  issue_type: string;
  description: string;
  recommendation?: string;
  category?: string;
}

export interface IssueListResponse {
  items: Issue[];
  total: number;
  critical: number;
  warning: number;
  info: number;
}

export interface AnalyticsOverview {
  crawl_id: number;
  status: string;
  total_pages: number;
  crawled_urls: number;
  failed_urls: number;
  critical_issues: number;
  warning_issues: number;
  info_issues: number;
  total_issues: number;
  avg_response_time_ms: number;
  avg_word_count: number;
  indexable_pages: number;
  noindex_pages: number;
  slow_pages: number;
  images_missing_alt: number;
  total_internal_links: number;
  total_external_links: number;
  status_distribution: { "2xx": number; "3xx": number; "4xx": number; "5xx": number };
}

export interface TopIssue {
  issue_type: string;
  severity: string;
  count: number;
  label: string;
}

export interface TopPage {
  page_id: number;
  url: string;
  status_code?: number;
  title?: string;
  issue_count: number;
  critical: number;
  warning: number;
  info: number;
  depth: number;
}

export interface IssueTrendPoint {
  crawl_id: number;
  started_at?: string;
  completed_at?: string;
  total_pages: number;
  critical_issues: number;
  warning_issues: number;
  info_issues: number;
  total_issues: number;
}

export interface IssuesSummary {
  total_pages: number;
  pages_with_issues: number;
  pages_without_issues: number;
  pct_with_issues: number;
  critical_issues: number;
  warning_issues: number;
  info_issues: number;
}

export interface ResponseTimesData {
  avg: number;
  p50: number;
  p90: number;
  p95: number;
  buckets: { range: string; count: number }[];
}

export interface LinkItem {
  source_url: string;
  target_url: string;
  anchor_text: string;
  link_type: "internal" | "external";
  nofollow: boolean;
  status_code?: number;
}

export interface LinksResponse {
  items: LinkItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// v0.5.0: Accessibility Analytics
export interface BFSGCheckItem {
  id: string;
  title: string;
  description: string;
  passed: boolean;
  wcag: string;
  level: string;
}

export interface BFSGChecklist {
  checks: BFSGCheckItem[];
  passed: number;
  total: number;
  compliance_pct: number;
}

export interface A11yCategoryData {
  critical: number;
  warning: number;
  info: number;
  total: number;
  score: number;
}

export interface A11yIssueType {
  issue_type: string;
  description: string;
  recommendation: string;
  category: string;
  critical: number;
  warning: number;
  info: number;
  total: number;
}

export interface A11yAffectedUrl {
  page_id: number;
  url: string;
  title?: string;
  status_code?: number;
  critical: number;
  warning: number;
  info: number;
  total: number;
}

export interface A11yLevelData {
  count: number;
  critical: number;
  warning: number;
  info: number;
  score: number;
}

export interface AccessibilityAnalytics {
  project_id: number;
  crawl_id: number | null;
  crawl_completed_at?: string;
  wcag_version?: string;
  wcag_score: number | null;
  score_a?: number;
  score_aa?: number;
  score_aaa?: number;
  score_label: "good" | "needs_improvement" | "poor";
  conformance_level?: "A" | "AA" | "AAA" | null;
  bfsg_compliant?: boolean;
  total_pages: number;
  accessibility_issues: number;
  issues_by_severity: { critical: number; warning: number; info: number };
  issues_by_level?: Record<string, A11yLevelData>;
  issues_by_principle?: Record<string, number>;
  issues_by_category: Record<string, A11yCategoryData>;
  issues_by_type: A11yIssueType[];
  top_affected_urls: A11yAffectedUrl[];
  bfsg_checklist: BFSGChecklist;
  message?: string;
}

// v0.5.0: Performance Analytics
export interface PerformanceSlowPage {
  page_id: number;
  url: string;
  title?: string;
  performance_score: number;
  response_time_ms?: number;
}

export interface PerformanceAnalytics {
  crawl_id: number;
  total_scored: number;
  avg_score: number | null;
  score_label?: string;
  distribution: { good: number; ok: number; poor: number };
  distribution_pct: { good: number; ok: number; poor: number };
  slow_pages: PerformanceSlowPage[];
}


// v0.7.0: SEO Tools (robots.txt + sitemap)
export interface RobotsAnalysis {
  found: boolean;
  url: string;
  content: string;
  sitemaps: string[];
  disallowed_paths: string[];
  crawl_delay: number | null;
  user_agents: string[];
  issues: SeoToolIssue[];
}

export interface SitemapAnalysis {
  found: boolean;
  url: string;
  type: 'index' | 'urlset' | 'unknown';
  urls: string[];
  child_sitemaps: string[];
  total_url_count: number;
  issues: SeoToolIssue[];
}

export interface SeoToolIssue {
  severity: 'critical' | 'warning' | 'info';
  type: string;
  description: string;
  recommendation: string;
}

export interface UrlComparison {
  crawled_count: number;
  sitemap_count: number;
  in_both: string[];
  in_both_count: number;
  in_sitemap_not_crawled: string[];
  in_sitemap_not_crawled_count: number;
  crawled_not_in_sitemap: string[];
  crawled_not_in_sitemap_count: number;
  latest_crawl_id: number | null;
}

export interface SeoToolsResult {
  robots: RobotsAnalysis;
  sitemap: SitemapAnalysis;
  url_comparison: UrlComparison;
}

// v0.7.0: Crawl Compare
export interface CrawlSummaryItem {
  id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  url_count: number;
  issue_count: number;
  critical_issues: number;
  warning_issues: number;
  info_issues: number;
}

export interface CrawlDiffSummary {
  new_urls: number;
  removed_urls: number;
  fixed_issues: number;
  new_issues: number;
  improved_pages: number;
  degraded_pages: number;
}

export interface IssueChange {
  url: string;
  type: string;
  severity: string;
  description?: string;
}

export interface StatusChange {
  url: string;
  old_status: number | null;
  new_status: number | null;
}

export interface TitleChange {
  url: string;
  old: string;
  new: string;
}

export interface PerformanceChange {
  url: string;
  old_score: number;
  new_score: number;
}

export interface CrawlDiff {
  crawl_a: CrawlSummaryItem;
  crawl_b: CrawlSummaryItem;
  summary: CrawlDiffSummary;
  new_urls: string[];
  removed_urls: string[];
  new_issues: IssueChange[];
  fixed_issues: IssueChange[];
  status_changes: StatusChange[];
  title_changes: TitleChange[];
  performance_changes: PerformanceChange[];
}

// v0.7.0: Alerts
export interface AlertConfig {
  id: number;
  project_id: number;
  email: string;
  alert_on_critical: boolean;
  alert_on_new_issues: boolean;
  alert_on_crawl_complete: boolean;
  min_severity: string;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_password: string | null;
  enabled: boolean;
  created_at: string;
}

export interface AlertConfigCreate {
  email: string;
  alert_on_critical?: boolean;
  alert_on_new_issues?: boolean;
  alert_on_crawl_complete?: boolean;
  min_severity?: string;
  smtp_host?: string | null;
  smtp_port?: number | null;
  smtp_user?: string | null;
  smtp_password?: string | null;
  enabled?: boolean;
}
export const api = {
  // ---- Projects ----
  getProjects: () => request<Project[]>("/api/projects"),
  getProject: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (data: ProjectCreate) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id: number, data: ProjectUpdate) =>
    request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteProject: (id: number) =>
    request<void>(`/api/projects/${id}`, { method: "DELETE" }),

  // ---- Crawls ----
  startCrawl: (projectId: number) =>
    request<Crawl>(`/api/projects/${projectId}/crawls`, { method: "POST" }),
  getCrawl: (id: number) => request<Crawl>(`/api/crawls/${id}`),
  getProjectCrawls: (projectId: number) =>
    request<Crawl[]>(`/api/projects/${projectId}/crawls`),
  cancelCrawl: (crawlId: number) =>
    request<{ message: string }>(`/api/crawls/${crawlId}/cancel`, { method: "POST" }),

  // ---- Pages ----
  getPages: (
    crawlId: number,
    params?: {
      page?: number;
      page_size?: number;
      status_code?: number;
      status_class?: string;
      content_type?: string;
      is_indexable?: boolean;
      has_issues?: boolean;
      issue_type?: string;
      search?: string;
      sort_by?: string;
      sort_dir?: string;
    }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.status_code) q.set("status_code", String(params.status_code));
    if (params?.status_class) q.set("status_class", params.status_class);
    if (params?.content_type) q.set("content_type", params.content_type);
    if (params?.is_indexable !== undefined) q.set("is_indexable", String(params.is_indexable));
    if (params?.has_issues !== undefined) q.set("has_issues", String(params.has_issues));
    if (params?.issue_type) q.set("issue_type", params.issue_type);
    if (params?.search) q.set("search", params.search);
    if (params?.sort_by) q.set("sort_by", params.sort_by);
    if (params?.sort_dir) q.set("sort_dir", params.sort_dir);
    return request<PageListResponse>(`/api/crawls/${crawlId}/pages?${q}`);
  },
  getPageDetail: (crawlId: number, pageId: number) =>
    request<Page>(`/api/crawls/${crawlId}/pages/${pageId}`),
  getPageIssues: (crawlId: number, pageId: number) =>
    request<Issue[]>(`/api/crawls/${crawlId}/pages/${pageId}/issues`),

  // ---- Issues ----
  getIssues: (crawlId: number, params?: { severity?: string; issue_type?: string; page?: number; page_size?: number }) => {
    const q = new URLSearchParams();
    if (params?.severity) q.set("severity", params.severity);
    if (params?.issue_type) q.set("issue_type", params.issue_type);
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    return request<IssueListResponse>(`/api/crawls/${crawlId}/issues?${q}`);
  },

  // ---- Analytics ----
  getAnalyticsOverview: (crawlId: number) =>
    request<AnalyticsOverview>(`/api/crawls/${crawlId}/analytics/overview`),
  getIssuesByType: (crawlId: number) =>
    request<Record<string, unknown>>(`/api/crawls/${crawlId}/analytics/issues-by-type`),
  getStatusDistribution: (crawlId: number) =>
    request<Record<string, number>>(`/api/crawls/${crawlId}/analytics/status-distribution`),
  getResponseTimes: (crawlId: number) =>
    request<ResponseTimesData>(`/api/crawls/${crawlId}/analytics/response-times`),
  getTopIssues: (crawlId: number, limit = 10) =>
    request<TopIssue[]>(`/api/crawls/${crawlId}/analytics/top-issues?limit=${limit}`),
  getTopPages: (crawlId: number, limit = 10) =>
    request<TopPage[]>(`/api/crawls/${crawlId}/analytics/top-pages?limit=${limit}`),
  getIssueTrend: (projectId: number, limit = 10) =>
    request<IssueTrendPoint[]>(`/api/projects/${projectId}/analytics/issue-trend?limit=${limit}`),
  getIssuesSummary: (crawlId: number) =>
    request<IssuesSummary>(`/api/crawls/${crawlId}/analytics/issues-summary`),
  // v0.5.0
  getAccessibilityAnalytics: (projectId: number, crawlId?: number) => {
    const q = crawlId ? `?crawl_id=${crawlId}` : "";
    return request<AccessibilityAnalytics>(`/api/projects/${projectId}/analytics/accessibility${q}`);
  },
  getPerformanceAnalytics: (crawlId: number) =>
    request<PerformanceAnalytics>(`/api/crawls/${crawlId}/analytics/performance`),

  // ---- Links ----
  getCrawlLinks: (
    crawlId: number,
    params?: Record<string, string | number | boolean>
  ) => {
    const q = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => q.set(k, String(v)));
    }
    return request<LinksResponse>(`/api/crawls/${crawlId}/links?${q}`);
  },

  // ---- Exports ----
  exportCsv: (crawlId: number) => `${API_BASE}/api/crawls/${crawlId}/export/csv`,
  exportJson: (crawlId: number) => `${API_BASE}/api/crawls/${crawlId}/export/json`,
  exportSitemap: (crawlId: number) => `${API_BASE}/api/crawls/${crawlId}/export/sitemap`,

  // ---- v0.7.0: SEO Tools ----
  getRobotsTxt: (projectId: number) =>
    request<RobotsAnalysis>(`/api/projects/${projectId}/robots`),
  getSitemap: (projectId: number) =>
    request<SitemapAnalysis>(`/api/projects/${projectId}/sitemap`),
  getSeoTools: (projectId: number) =>
    request<SeoToolsResult>(`/api/projects/${projectId}/seo-tools`),

  // ---- v0.7.0: Crawl Compare ----
  getProjectCrawlList: (projectId: number) =>
    request<CrawlSummaryItem[]>(`/api/projects/${projectId}/crawls`),
  compareCrawls: (crawlAId: number, crawlBId: number) =>
    request<CrawlDiff>(`/api/compare/${crawlAId}/${crawlBId}`),

  // ---- v0.7.0: PDF Reports ----
  getPdfReportUrl: (crawlId: number) => `${API_BASE}/api/crawls/${crawlId}/report/pdf`,
  getHtmlReportUrl: (crawlId: number) => `${API_BASE}/api/crawls/${crawlId}/report/html`,
  downloadPdfReport: (crawlId: number) => {
    window.open(`${API_BASE}/api/crawls/${crawlId}/report/pdf`, "_blank");
  },

  // ---- v0.7.0: Alerts ----
  getAlerts: (projectId: number) =>
    request<AlertConfig[]>(`/api/projects/${projectId}/alerts`),
  createAlert: (projectId: number, data: AlertConfigCreate) =>
    request<AlertConfig>(`/api/projects/${projectId}/alerts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAlert: (projectId: number, alertId: number, data: Partial<AlertConfigCreate>) =>
    request<AlertConfig>(`/api/projects/${projectId}/alerts/${alertId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteAlert: (projectId: number, alertId: number) =>
    request<{ message: string }>(`/api/projects/${projectId}/alerts/${alertId}`, {
      method: "DELETE",
    }),
  testAlert: (projectId: number) =>
    request<{ message: string }>(`/api/projects/${projectId}/alerts/test`, {
      method: "POST",
    }),

  // ---- v0.9.0: Mobile SEO ----
  getMobileSummary: (projectId: number) =>
    request<MobileSummary>(`/api/mobile/projects/${projectId}/summary`),
  getMobileIssues: (
    projectId: number,
    params?: {
      min_score?: number;
      max_score?: number;
      sort_by?: string;
      order?: string;
      limit?: number;
    }
  ) => {
    const q = new URLSearchParams();
    if (params?.min_score !== undefined) q.set("min_score", String(params.min_score));
    if (params?.max_score !== undefined) q.set("max_score", String(params.max_score));
    if (params?.sort_by) q.set("sort_by", params.sort_by);
    if (params?.order) q.set("order", params.order);
    if (params?.limit) q.set("limit", String(params.limit));
    return request<MobileIssuesResponse>(`/api/mobile/projects/${projectId}/issues?${q}`);
  },

  // ---- v0.9.0: Google Analytics 4 ----
  getGA4Status: (projectId: number) =>
    request<GA4Status>(`/api/projects/${projectId}/ga4/status`),
  getGA4AuthUrl: (projectId: number) =>
    request<{ auth_url: string }>(`/api/integrations/ga4/auth-url?project_id=${projectId}`),
  disconnectGA4: (projectId: number) =>
    request<void>(`/api/projects/${projectId}/integrations/ga4`, { method: "DELETE" }),
  getGA4Overview: (projectId: number, dateRange?: string) => {
    const q = dateRange ? `?date_range=${dateRange}` : "";
    return request<GA4Overview>(`/api/projects/${projectId}/ga4/overview${q}`);
  },
  getGA4TopPages: (
    projectId: number,
    params?: { limit?: number; date_range?: string }
  ) => {
    const q = new URLSearchParams();
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.date_range) q.set("date_range", params.date_range);
    return request<GA4TopPage[]>(`/api/projects/${projectId}/ga4/top-pages?${q}`);
  },
  getGA4Sources: (projectId: number, dateRange?: string) => {
    const q = dateRange ? `?date_range=${dateRange}` : "";
    return request<GA4Source[]>(`/api/projects/${projectId}/ga4/sources${q}`);
  },
  getGA4Devices: (projectId: number, dateRange?: string) => {
    const q = dateRange ? `?date_range=${dateRange}` : "";
    return request<GA4DeviceBreakdown>(`/api/projects/${projectId}/ga4/devices${q}`);
  },
  getGA4Conversions: (projectId: number, dateRange?: string) => {
    const q = dateRange ? `?date_range=${dateRange}` : "";
    return request<GA4Conversion[]>(`/api/projects/${projectId}/ga4/conversions${q}`);
  },
  syncGA4: (projectId: number) =>
    request<void>(`/api/projects/${projectId}/ga4/sync`, { method: "POST" }),

};

// ============================================================
// v0.8.0 Types — Auth / Teams / CWV / GSC / Rank Tracking
// ============================================================

export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  last_login?: string;
}

export interface Team {
  id: number;
  name: string;
  slug: string;
  owner_id: number;
  max_projects: number;
  max_crawl_urls: number;
  created_at: string;
  member_count?: number;
  my_role?: string;
}

export interface TeamMember {
  id: number;
  user_id: number;
  email: string;
  full_name?: string;
  role: string;
  joined_at: string;
}

export interface CWVPage {
  id: number;
  url: string;
  lcp?: number;
  cls?: number;
  fcp?: number;
  ttfb?: number;
  tbt?: number;
  dom_size?: number;
  cwv_score?: string;
}

export interface CWVSummary {
  pages: CWVPage[];
  avg_lcp?: number;
  avg_cls?: number;
  avg_fcp?: number;
  p75_lcp?: number;
  distribution?: Record<string, Record<string, number>>;
}

export interface KeywordRanking {
  id: number;
  keyword: string;
  date: string;
  position: number;
  clicks: number;
  impressions: number;
  ctr: number;
  url?: string;
}

export interface GSCAnalytics {
  site_url: string;
  period_days: number;
  total_clicks: number;
  total_impressions: number;
  avg_ctr: string;
  avg_position: string;
  rows: Array<{
    page?: string;
    date?: string;
    clicks: number;
    impressions: number;
    ctr: number;
    position: number;
  }>;
}

export interface GSCStatus {
  connected: boolean;
  site_url?: string;
  token_expiry?: string;
}

// ============================================================
// v0.9.0 Types — Mobile SEO & GA4 Analytics
// ============================================================

export interface MobileCheck {
  viewport_meta: boolean;
  viewport_scalable: boolean;
  font_size_readable: boolean;
  tap_targets_ok: boolean;
  touch_targets_count: number;
  small_touch_targets: number;
  media_queries_detected: boolean;
  responsive_images: boolean;
  mobile_meta_theme: boolean;
  no_horizontal_scroll: boolean;
  amp_page: boolean;
  structured_nav: boolean;
  mobile_score: number;
  mobile_issues: string[];
}

export interface MobileSummary {
  project_id: number;
  crawl_id: number | null;
  total_pages: number;
  pages_with_issues: number;
  average_score: number;
  score_distribution: {
    '0-20': number;
    '21-40': number;
    '41-60': number;
    '61-80': number;
    '81-100': number;
  };
}

export interface MobilePageIssue {
  page_id: number;
  url: string;
  mobile_score: number;
  issues_count: number;
  mobile_issues: string[];
  mobile_check: MobileCheck;
}

export interface MobileIssuesResponse {
  crawl_id: number;
  pages: MobilePageIssue[];
  total_count: number;
}

export interface GA4Status {
  connected: boolean;
  property_id?: string;
  last_sync?: string;
}

export interface GA4Overview {
  sessions: number;
  pageviews: number;
  bounce_rate: number;
  avg_session_duration: number;
  conversions: number;
  trend?: {
    sessions_change: number;
    pageviews_change: number;
    bounce_rate_change: number;
  };
}

export interface GA4TopPage {
  page_path: string;
  sessions: number;
  pageviews: number;
  avg_duration: number;
  bounce_rate: number;
}

export interface GA4Source {
  source: string;
  medium: string;
  sessions: number;
  new_users: number;
}

export interface GA4DeviceBreakdown {
  desktop: number;
  mobile: number;
  tablet: number;
}

export interface GA4Conversion {
  event_name: string;
  conversions: number;
}
