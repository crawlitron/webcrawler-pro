"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, type Project, type ProjectUpdate } from "@/lib/api";

const SCHEDULE_OPTIONS = [
  { value: "", label: "No scheduled crawl" },
  { value: "daily", label: "Daily (every 24 hours)" },
  { value: "weekly", label: "Weekly (every 7 days)" },
  { value: "monthly", label: "Monthly (every 30 days)" },
];

export default function ProjectSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [startUrl, setStartUrl] = useState("");
  const [maxUrls, setMaxUrls] = useState(500);
  const [customUserAgent, setCustomUserAgent] = useState("");
  const [crawlDelay, setCrawlDelay] = useState(0.5);
  const [includePatterns, setIncludePatterns] = useState("");
  const [excludePatterns, setExcludePatterns] = useState("");
  const [crawlExternalLinks, setCrawlExternalLinks] = useState(false);
  const [crawlSchedule, setCrawlSchedule] = useState(""); // v0.5.0

  const load = useCallback(async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
      setName(proj.name);
      setStartUrl(proj.start_url);
      setMaxUrls(proj.max_urls);
      setCustomUserAgent(proj.custom_user_agent ?? "");
      setCrawlDelay(proj.crawl_delay ?? 0.5);
      setIncludePatterns((proj.include_patterns ?? []).join("\n"));
      setExcludePatterns((proj.exclude_patterns ?? []).join("\n"));
      setCrawlExternalLinks(proj.crawl_external_links ?? false);
      setCrawlSchedule(proj.crawl_schedule ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const includePats = includePatterns.split("\n").map(s => s.trim()).filter(Boolean);
      const excludePats = excludePatterns.split("\n").map(s => s.trim()).filter(Boolean);
      const update: ProjectUpdate = {
        name,
        start_url: startUrl,
        max_urls: maxUrls,
        custom_user_agent: customUserAgent || null,
        crawl_delay: crawlDelay,
        include_patterns: includePats.length > 0 ? includePats : null,
        exclude_patterns: excludePats.length > 0 ? excludePats : null,
        crawl_external_links: crawlExternalLinks,
        crawl_schedule: crawlSchedule || null,
      };
      const updated = await api.updateProject(projectId, update);
      setProject(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete project "${project?.name}" and all crawl data? This cannot be undone.`)) return;
    try {
      await api.deleteProject(projectId);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete project");
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-96">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
          <span>/</span>
          <span>Settings</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Project Settings</h1>
        <p className="text-sm text-gray-500">{project?.name}</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error}</div>
      )}
      {saved && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700 text-sm">✓ Settings saved successfully</div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Basic Settings */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-5">
          <h2 className="text-base font-semibold text-gray-900">🌐 Basic Settings</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Project Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} required
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start URL</label>
            <input type="url" value={startUrl} onChange={e => setStartUrl(e.target.value)} required
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max URLs per Crawl
              <span className="text-gray-400 font-normal ml-1">(Default: 500)</span>
            </label>
            <input type="number" min={1} max={50000} value={maxUrls} onChange={e => setMaxUrls(Number(e.target.value))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        {/* Scheduled Crawls — v0.5.0 */}
        <div className="bg-white rounded-xl border border-blue-100 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">📅</span>
            <h2 className="text-base font-semibold text-gray-900">Scheduled Crawls</h2>
            <span className="ml-auto text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">v0.5.0</span>
          </div>
          <p className="text-sm text-gray-500">
            Automatically crawl this project on a recurring schedule. The Celery Beat worker checks for due crawls every hour.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Crawl Schedule</label>
            <select
              value={crawlSchedule}
              onChange={e => setCrawlSchedule(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {SCHEDULE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          {crawlSchedule && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
              ℹ️ This project will be automatically re-crawled{" "}
              {crawlSchedule === "daily" ? "every 24 hours" :
               crawlSchedule === "weekly" ? "every 7 days" : "every 30 days"}.
              The first scheduled crawl will trigger immediately if no previous crawl exists.
            </div>
          )}
        </div>

        {/* Advanced Crawl Settings */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-5">
          <h2 className="text-base font-semibold text-gray-900">⚙️ Advanced Crawl Configuration</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Custom User-Agent
              <span className="text-gray-400 font-normal ml-1">(leave blank for default bot)</span>
            </label>
            <input type="text" value={customUserAgent} onChange={e => setCustomUserAgent(e.target.value)}
              placeholder="WebCrawlerPro/2.0 (+https://webcrawlerpro.io/bot)"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Crawl Delay (seconds)
              <span className="text-gray-400 font-normal ml-1">(Default: 0.5s — be respectful to servers)</span>
            </label>
            <input type="number" min={0} max={60} step={0.1} value={crawlDelay}
              onChange={e => setCrawlDelay(parseFloat(e.target.value))}
              className="w-48 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="crawl-external" checked={crawlExternalLinks}
              onChange={e => setCrawlExternalLinks(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
            <label htmlFor="crawl-external" className="text-sm font-medium text-gray-700">
              Crawl External Links
              <span className="text-gray-400 font-normal ml-1">(follow links to other domains)</span>
            </label>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              URL Include Patterns
              <span className="text-gray-400 font-normal ml-1">(one regex per line)</span>
            </label>
            <textarea value={includePatterns} onChange={e => setIncludePatterns(e.target.value)}
              placeholder={`/blog/\n/products/`} rows={3}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-y" />
            <p className="text-xs text-gray-400 mt-1">Leave empty to crawl all URLs on the domain</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              URL Exclude Patterns
              <span className="text-gray-400 font-normal ml-1">(one regex per line)</span>
            </label>
            <textarea value={excludePatterns} onChange={e => setExcludePatterns(e.target.value)}
              placeholder={`/wp-admin/\n/tag/`} rows={3}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-y" />
          </div>
        </div>

        {/* Save Button */}
        <button type="submit" disabled={saving}
          className="w-full bg-blue-600 text-white rounded-xl py-3 font-semibold text-sm hover:bg-blue-700 disabled:opacity-60 transition-colors">
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </form>

      {/* Danger Zone */}
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-red-700">⚠️ Danger Zone</h2>
        <p className="text-sm text-gray-600">
          Permanently delete this project and all associated crawl data. This action cannot be undone.
        </p>
        <button onClick={handleDelete}
          className="bg-red-600 text-white rounded-lg px-5 py-2 text-sm font-medium hover:bg-red-700 transition-colors">
          Delete Project
        </button>
      </div>
    </div>
  );
}
