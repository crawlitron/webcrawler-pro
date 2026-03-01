"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  api,
  type GA4Status,
  type GA4Overview,
  type GA4TopPage,
  type GA4Source,
  type GA4DeviceBreakdown,
  type GA4Conversion,
} from "@/lib/api";

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const formatNumber = (num: number): string => {
  return new Intl.NumberFormat("en-US").format(num);
};

const TrendIndicator = ({ change }: { change: number }) => {
  if (change === 0) return <span className="text-gray-400 text-xs">—</span>;
  const isPositive = change > 0;
  return (
    <span className={`text-xs font-medium ${isPositive ? "text-green-600" : "text-red-600"}`}>
      {isPositive ? "↑" : "↓"} {Math.abs(change).toFixed(1)}%
    </span>
  );
};

export default function GA4AnalyticsPage() {
  const params = useParams();
  const projectId = Number(params.id);

  const [status, setStatus] = useState<GA4Status | null>(null);
  const [overview, setOverview] = useState<GA4Overview | null>(null);
  const [topPages, setTopPages] = useState<GA4TopPage[]>([]);
  const [sources, setSources] = useState<GA4Source[]>([]);
  const [devices, setDevices] = useState<GA4DeviceBreakdown | null>(null);
  const [conversions, setConversions] = useState<GA4Conversion[]>([]);

  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [dateRange] = useState("last30days");

  const loadStatus = useCallback(async () => {
    try {
      const statusData = await api.getGA4Status(projectId);
      setStatus(statusData);
      return statusData;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load GA4 status");
      return null;
    }
  }, [projectId]);

  const loadAllData = useCallback(async () => {
    try {
      setLoading(true);
      const [overviewData, pagesData, sourcesData, devicesData, conversionsData] = await Promise.all([
        api.getGA4Overview(projectId, dateRange),
        api.getGA4TopPages(projectId, { limit: 10, date_range: dateRange }),
        api.getGA4Sources(projectId, dateRange),
        api.getGA4Devices(projectId, dateRange),
        api.getGA4Conversions(projectId, dateRange),
      ]);
      setOverview(overviewData);
      setTopPages(pagesData);
      setSources(sourcesData);
      setDevices(devicesData);
      setConversions(conversionsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load GA4 data");
    } finally {
      setLoading(false);
    }
  }, [projectId, dateRange]);

  useEffect(() => {
    loadStatus().then((statusData) => {
      if (statusData?.connected) {
        loadAllData();
      } else {
        setLoading(false);
      }
    });
  }, [loadStatus, loadAllData]);

  const handleConnect = async () => {
    try {
      const { auth_url } = await api.getGA4AuthUrl(projectId);
      window.location.href = auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to get auth URL");
    }
  };

  const handleDisconnect = async () => {
    if (!confirm("Are you sure you want to disconnect Google Analytics?")) return;
    try {
      await api.disconnectGA4(projectId);
      setStatus({ connected: false });
      setOverview(null);
      setTopPages([]);
      setSources([]);
      setDevices(null);
      setConversions([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to disconnect");
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await api.syncGA4(projectId);
      await loadAllData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to sync data");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    );
  }

  // Not Connected State
  if (!status?.connected) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
          <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
          <span>/</span>
          <span>Google Analytics</span>
        </div>

        <div className="bg-white rounded-xl border-2 border-gray-200 p-12 text-center shadow-sm">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-3">Connect Google Analytics 4</h2>
          <p className="text-gray-600 mb-6 max-w-md mx-auto">
            Link your Google Analytics 4 property to view sessions, pageviews, traffic sources, conversions, and more.
          </p>

          <button
            onClick={handleConnect}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
          >
            <span>🔗</span>
            Connect Google Analytics
          </button>

          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md mx-auto text-left">
            <h3 className="font-semibold text-blue-900 text-sm mb-2">What will be synced:</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>✓ Sessions and pageviews</li>
              <li>✓ Traffic sources and channels</li>
              <li>✓ Device breakdown</li>
              <li>✓ Top pages performance</li>
              <li>✓ Conversion events</li>
              <li>✓ Bounce rate and engagement metrics</li>
            </ul>
          </div>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 max-w-md mx-auto">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Connected State
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Project</Link>
        <span>/</span>
        <span className="text-gray-800 font-medium">Google Analytics</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-3xl">📊</div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Google Analytics 4</h1>
            {status.property_id && (
              <p className="text-sm text-gray-500">
                Property: <span className="font-mono text-xs">{status.property_id}</span>
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status.last_sync && (
            <span className="text-xs text-gray-500">
              Last sync: {new Date(status.last_sync).toLocaleString()}
            </span>
          )}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {syncing ? "Syncing..." : "Sync Now"}
          </button>
          <button
            onClick={handleDisconnect}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
          >
            Disconnect
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* KPI Cards */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Sessions</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(overview.sessions)}</div>
            {overview.trend && <TrendIndicator change={overview.trend.sessions_change} />}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Pageviews</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(overview.pageviews)}</div>
            {overview.trend && <TrendIndicator change={overview.trend.pageviews_change} />}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Bounce Rate</div>
            <div className="text-2xl font-bold text-gray-900">{overview.bounce_rate.toFixed(1)}%</div>
            {overview.trend && <TrendIndicator change={overview.trend.bounce_rate_change} />}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Avg Duration</div>
            <div className="text-2xl font-bold text-gray-900">{formatDuration(overview.avg_session_duration)}</div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="text-xs text-gray-500 mb-1">Conversions</div>
            <div className="text-2xl font-bold text-green-600">{formatNumber(overview.conversions)}</div>
          </div>
        </div>
      )}

      {/* Device Breakdown */}
      {devices && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Device Breakdown</h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Desktop", value: devices.desktop, icon: "💻", color: "bg-blue-500" },
              { label: "Mobile", value: devices.mobile, icon: "📱", color: "bg-green-500" },
              { label: "Tablet", value: devices.tablet, icon: "📱", color: "bg-purple-500" },
            ].map((device) => {
              const total = devices.desktop + devices.mobile + devices.tablet;
              const pct = total > 0 ? Math.round((device.value / total) * 100) : 0;
              return (
                <div key={device.label} className="text-center">
                  <div className="text-3xl mb-2">{device.icon}</div>
                  <div className="text-xl font-bold text-gray-800">{formatNumber(device.value)}</div>
                  <div className="text-xs text-gray-500 mb-2">{device.label}</div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className={`h-2 rounded-full ${device.color}`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{pct}%</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Traffic Sources */}
      {sources.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Traffic Sources</h3>
          <div className="space-y-2">
            {sources.slice(0, 10).map((source, idx) => {
              const maxSessions = Math.max(...sources.map((s) => s.sessions));
              const barWidth = maxSessions > 0 ? (source.sessions / maxSessions) * 100 : 0;

              return (
                <div key={idx} className="flex items-center gap-3">
                  <div className="w-32 truncate text-sm text-gray-700">
                    {source.source} / {source.medium}
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-100 rounded-full h-6 relative">
                      <div
                        className="bg-blue-500 h-6 rounded-full transition-all"
                        style={{ width: `${barWidth}%` }}
                      />
                      <span className="absolute inset-0 flex items-center justify-end pr-2 text-xs font-medium text-gray-700">
                        {formatNumber(source.sessions)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top Pages */}
      {topPages.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700">Top Pages</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Page Path</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Sessions</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Pageviews</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Avg Duration</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Bounce Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {topPages.map((page, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-800 font-mono text-xs truncate max-w-xs">
                      {page.page_path}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatNumber(page.sessions)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatNumber(page.pageviews)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatDuration(page.avg_duration)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{page.bounce_rate.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Conversions */}
      {conversions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Conversion Events</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {conversions.map((conv, idx) => (
              <div key={idx} className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-green-700">{formatNumber(conv.conversions)}</div>
                <div className="text-xs text-green-600 mt-1">{conv.event_name}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
