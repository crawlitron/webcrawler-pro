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
  created_at: string;
  updated_at: string;
  last_crawl_status?: string;
  last_crawl_id?: number;
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

export const api = {
  // ---- Projects ----
  getProjects: () => request<Project[]>("/api/projects"),
  getProject: (id: number) => request<Project>(`/api/projects/${id}`),
  createProject: (data: { name: string; start_url: string; max_urls: number }) =>
    request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
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
    params?: { page?: number; page_size?: number; status_code?: number; issue_type?: string; search?: string }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    if (params?.status_code) q.set("status_code", String(params.status_code));
    if (params?.issue_type) q.set("issue_type", params.issue_type);
    if (params?.search) q.set("search", params.search);
    return request<PageListResponse>(`/api/crawls/${crawlId}/pages?${q}`);
  },

  // ---- Issues ----
  getIssues: (crawlId: number, severity?: string, issue_type?: string) => {
    const q = new URLSearchParams();
    if (severity) q.set("severity", severity);
    if (issue_type) q.set("issue_type", issue_type);
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
};
