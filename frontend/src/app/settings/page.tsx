
"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const [maxUrls, setMaxUrls] = useState("500");
  const [userAgent, setUserAgent] = useState("WebCrawlerPro/2.0 (+https://webcrawlerpro.io/bot)");
  const [crawlDelay, setCrawlDelay] = useState("100");
  const [saved, setSaved] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleteSuccess, setDeleteSuccess] = useState("");

  const apiKey = typeof window !== "undefined" ? localStorage.getItem("wcp_api_key") || "—" : "—";

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (typeof window !== "undefined") {
      localStorage.setItem("wcp_max_urls", maxUrls);
      localStorage.setItem("wcp_user_agent", userAgent);
      localStorage.setItem("wcp_crawl_delay", crawlDelay);
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  async function handleDeleteAll() {
    if (deleteConfirm !== "DELETE ALL") {
      setDeleteError("Type DELETE ALL to confirm");
      return;
    }
    setDeleting(true);
    setDeleteError("");
    try {
      const projects = await api.getProjects();
      for (const p of projects) {
        await api.deleteProject(p.id);
      }
      setDeleteSuccess(`Deleted ${projects.length} project(s) and all associated data.`);
      setDeleteConfirm("");
    } catch (e: unknown) {
      setDeleteError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure WebCrawler Pro defaults</p>
      </div>

      {/* Crawl Configuration */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Default Crawl Configuration</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Default Max URLs
            </label>
            <input
              type="number"
              min="10"
              max="100000"
              value={maxUrls}
              onChange={(e) => setMaxUrls(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1">Maximum URLs to crawl per project (default: 500)</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              User Agent
            </label>
            <input
              type="text"
              value={userAgent}
              onChange={(e) => setUserAgent(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1">User-Agent string sent with crawl requests</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Crawl Delay (ms)
            </label>
            <input
              type="number"
              min="0"
              max="10000"
              value={crawlDelay}
              onChange={(e) => setCrawlDelay(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400 mt-1">Delay between requests in milliseconds (default: 100ms)</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition"
            >
              Save Settings
            </button>
            {saved && (
              <span className="text-green-600 text-sm font-medium">Settings saved!</span>
            )}
          </div>
        </form>
      </div>

      {/* API Information */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">API Information</h2>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-700">API Base URL</p>
            <div className="flex items-center gap-2 mt-1">
              <code className="flex-1 bg-gray-50 border border-gray-200 rounded px-3 py-2 text-sm text-gray-700 font-mono">
                {API_BASE}
              </code>
              <button
                onClick={() => navigator.clipboard?.writeText(API_BASE)}
                className="text-xs text-gray-500 hover:text-gray-700 px-2 py-2 border border-gray-200 rounded hover:bg-gray-50"
              >
                Copy
              </button>
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Interactive API Docs</p>
            <a
              href={`${API_BASE}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline mt-1 inline-block"
            >
              {API_BASE}/docs (Swagger UI)
            </a>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Health Check</p>
            <a
              href={`${API_BASE}/health`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline mt-1 inline-block"
            >
              {API_BASE}/health
            </a>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-white rounded-xl border-2 border-red-200 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-red-700 mb-2">Danger Zone</h2>
        <p className="text-sm text-gray-600 mb-4">
          Permanently delete all projects and associated crawl data. This action cannot be undone.
        </p>

        {deleteSuccess ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-green-700 text-sm">
            {deleteSuccess}
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Type <strong>DELETE ALL</strong> to confirm:
              </label>
              <input
                type="text"
                value={deleteConfirm}
                onChange={(e) => { setDeleteConfirm(e.target.value); setDeleteError(""); }}
                placeholder="DELETE ALL"
                className="w-full border border-red-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>
            {deleteError && (
              <p className="text-red-600 text-sm">{deleteError}</p>
            )}
            <button
              onClick={handleDeleteAll}
              disabled={deleting}
              className="bg-red-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete All Data"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
