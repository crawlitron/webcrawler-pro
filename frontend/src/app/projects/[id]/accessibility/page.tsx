"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, type AccessibilityAnalytics, type A11yIssueType } from "@/lib/api";

// ── helpers ───────────────────────────────────────────────────────────────────
function getIssueLevel(issue_type: string): "A" | "AA" | "AAA" | "other" {
  const it = issue_type.toLowerCase();
  if (it.startsWith("wcag_aaa_")) return "AAA";
  if (it.startsWith("wcag_aa_"))  return "AA";
  if (it.startsWith("wcag_a_"))   return "A";
  const legacyAA = new Set(["a11y_viewport_no_scale","a11y_viewport_limited_scale",
    "a11y_vague_link","a11y_empty_link","a11y_icon_link","a11y_missing_captions"]);
  if (legacyAA.has(issue_type)) return "AA";
  if (issue_type.startsWith("a11y_") || issue_type.startsWith("bfsg_")) return "A";
  return "other";
}

function getIssuePrinciple(issue_type: string): string {
  const parts = issue_type.split("_");
  if (parts.length >= 4 && parts[0].toLowerCase() === "wcag") {
    const code = parts[3] ?? "";
    if (code[0] === "1") return "perceivable";
    if (code[0] === "2") return "operable";
    if (code[0] === "3") return "understandable";
    if (code[0] === "4") return "robust";
  }
  const legacy: [string, string][] = [
    ["a11y_missing_alt","perceivable"],["a11y_empty_alt","perceivable"],
    ["a11y_missing_captions","perceivable"],["a11y_missing_lang","perceivable"],
    ["a11y_invalid_lang","perceivable"],["a11y_viewport","perceivable"],
    ["a11y_vague_link","operable"],["a11y_empty_link","operable"],
    ["a11y_icon_link","operable"],["a11y_missing_skip","operable"],
    ["a11y_positive_tabindex","operable"],
    ["a11y_input_missing","understandable"],["a11y_button_missing","understandable"],
    ["a11y_select_missing","understandable"],
    ["a11y_duplicate_ids","robust"],["a11y_missing_title","robust"],
  ];
  for (const [pfx, prin] of legacy) if (issue_type.startsWith(pfx)) return prin;
  return "other";
}

// ── style helpers ─────────────────────────────────────────────────────────────
const SCORE_COLOR = (score: number | null) => {
  if (score === null) return { text:"text-gray-400", bg:"bg-gray-100", bar:"bg-gray-300", label:"N/A" };
  if (score >= 80) return { text:"text-green-600", bg:"bg-green-50", bar:"bg-green-500", label:"Good" };
  if (score >= 50) return { text:"text-yellow-600", bg:"bg-yellow-50", bar:"bg-yellow-500", label:"Needs Improvement" };
  return { text:"text-red-600", bg:"bg-red-50", bar:"bg-red-500", label:"Poor" };
};

const SEV_BADGE = (sev: string) => {
  if (sev === "critical") return "bg-red-100 text-red-700 border border-red-200";
  if (sev === "warning")  return "bg-yellow-100 text-yellow-700 border border-yellow-200";
  return "bg-blue-100 text-blue-700 border border-blue-200";
};

const LEVEL_BADGE: Record<string, string> = {
  A:   "bg-green-100 text-green-800 border border-green-200",
  AA:  "bg-yellow-100 text-yellow-800 border border-yellow-200",
  AAA: "bg-blue-100 text-blue-800 border border-blue-200",
};

const CONFORMANCE: Record<string, { bg:string; text:string; border:string; icon:string; label:string }> = {
  A:   { bg:"bg-green-50",  text:"text-green-800",  border:"border-green-300",  icon:"✅", label:"Konform Level A" },
  AA:  { bg:"bg-yellow-50", text:"text-yellow-800", border:"border-yellow-300", icon:"🏅", label:"Konform Level AA" },
  AAA: { bg:"bg-blue-50",   text:"text-blue-800",   border:"border-blue-300",   icon:"🏆", label:"Konform Level AAA" },
};

const CAT_ICONS: Record<string, string> = {
  Perceivable:"👁", Operable:"⌨️", Understandable:"🧠", Robust:"🔧", BFSG:"🇩🇪", Other:"📋",
};
const PRIN_ICONS: Record<string, string> = {
  perceivable:"👁", operable:"⌨️", understandable:"🧠", robust:"🔧", other:"📋",
};

const WCAG_CATS   = ["Perceivable","Operable","Understandable","Robust","BFSG"];
const PRINCIPLES  = ["perceivable","operable","understandable","robust"];
const LEVELS      = ["A","AA","AAA"] as const;

// ── component ─────────────────────────────────────────────────────────────────
export default function AccessibilityPage() {
  const params    = useParams();
  const projectId = Number(params.id);

  const [data,    setData]    = useState<AccessibilityAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");

  const [activeTab,       setActiveTab]       = useState<"overview"|"issues"|"bfsg"|"urls">("overview");
  const [filterLevel,     setFilterLevel]     = useState("all");
  const [filterPrinciple, setFilterPrinciple] = useState("all");
  const [filterCategory,  setFilterCategory]  = useState("all");
  const [filterSeverity,  setFilterSeverity]  = useState("all");
  const [searchTerm,      setSearchTerm]      = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setData(await api.getAccessibilityAnalytics(projectId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const filteredIssues = (data?.issues_by_type ?? []).filter((iss: A11yIssueType) => {
    if (filterLevel     !== "all" && getIssueLevel(iss.issue_type)     !== filterLevel)     return false;
    if (filterPrinciple !== "all" && getIssuePrinciple(iss.issue_type) !== filterPrinciple) return false;
    if (filterCategory  !== "all" && iss.category !== filterCategory)  return false;
    if (filterSeverity === "critical" && iss.critical === 0) return false;
    if (filterSeverity === "warning"  && iss.warning  === 0) return false;
    if (filterSeverity === "info"     && iss.info     === 0) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      if (!iss.description.toLowerCase().includes(q) && !iss.issue_type.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  if (loading) return (
    <div className="flex items-center justify-center min-h-96">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  );
  if (error) return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        <p className="font-semibold">Fehler beim Laden</p><p className="text-sm mt-1">{error}</p>
      </div>
    </div>
  );
  if (!data || data.crawl_id === null) return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-6">
        <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Projekt</Link>
        <span>/</span><span>Accessibility</span>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
        <div className="text-4xl mb-3">♿</div>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Noch keine Crawl-Daten</h2>
        <p className="text-gray-500 text-sm">Führen Sie zuerst einen Crawl durch.</p>
        <Link href={`/projects/${projectId}`}
          className="mt-4 inline-block bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          Zum Projekt
        </Link>
      </div>
    </div>
  );

  const score     = data.wcag_score;
  const ss        = SCORE_COLOR(score);
  const bfsg      = data.bfsg_checklist;
  const confLevel = data.conformance_level ?? null;
  const wcagVer   = data.wcag_version ?? "2.1";

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link href={`/projects/${projectId}`} className="hover:text-blue-600">← Projekt</Link>
        <span>/</span>
        <span className="text-gray-800 font-medium">Accessibility</span>
        <span className="ml-auto flex items-center gap-2">
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">WCAG {wcagVer}</span>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">A · AA · AAA · BFSG 2025</span>
        </span>
      </div>

      {/* Conformance Banner */}
      {confLevel && CONFORMANCE[confLevel] ? (
        <div className={`rounded-xl border-2 ${CONFORMANCE[confLevel].border} ${CONFORMANCE[confLevel].bg} px-6 py-4 flex items-center gap-4`}>
          <span className="text-3xl">{CONFORMANCE[confLevel].icon}</span>
          <div className="flex-1">
            <div className={`font-bold text-lg ${CONFORMANCE[confLevel].text}`}>{CONFORMANCE[confLevel].label}</div>
            <p className={`text-sm ${CONFORMANCE[confLevel].text} opacity-80`}>
              Keine kritischen oder Warnungs-Issues auf diesem Level oder darunter erkannt.
            </p>
          </div>
          {data.bfsg_compliant && (
            <span className="text-xs bg-green-100 text-green-800 border border-green-200 px-3 py-1 rounded-full font-semibold whitespace-nowrap">
              🇩🇪 BFSG Konform
            </span>
          )}
        </div>
      ) : (
        <div className="rounded-xl border-2 border-red-200 bg-red-50 px-6 py-4 flex items-center gap-4">
          <span className="text-3xl">⚠️</span>
          <div>
            <div className="font-bold text-lg text-red-800">Nicht Konform (Level A)</div>
            <p className="text-sm text-red-700 opacity-80">
              Es bestehen kritische oder Warnungs-Issues auf Level A. Bitte beheben Sie diese zuerst.
            </p>
          </div>
        </div>
      )}

      {/* Score Hero */}
      <div className={`rounded-2xl border p-6 ${ss.bg}`}>
        <div className="flex flex-col md:flex-row items-center gap-6">
          {/* Overall */}
          <div className="text-center shrink-0">
            <div className={`text-7xl font-black ${ss.text}`}>{score ?? "—"}</div>
            <div className={`text-sm font-semibold mt-1 ${ss.text}`}>{ss.label}</div>
            <div className="text-xs text-gray-500 mt-0.5">Gesamt-Score</div>
          </div>
          {/* Per-level */}
          <div className="flex-1 grid grid-cols-3 gap-3">
            {LEVELS.map(lvl => {
              const ls_val = lvl === "A" ? (data.score_a ?? null) : lvl === "AA" ? (data.score_aa ?? null) : (data.score_aaa ?? null);
              const ls = SCORE_COLOR(ls_val);
              return (
                <div key={lvl} className="bg-white rounded-xl p-4 shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${LEVEL_BADGE[lvl]}`}>{lvl}</span>
                    <span className={`text-2xl font-black ${ls.text}`}>{ls_val ?? "—"}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${ls.bar}`} style={{ width: `${ls_val ?? 0}%` }} />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{ls.label}</div>
                </div>
              );
            })}
          </div>
          {/* Stats */}
          <div className="grid grid-cols-2 gap-3 shrink-0">
            <div className="bg-white rounded-xl p-3 text-center shadow-sm">
              <div className="text-xl font-bold text-gray-800">{data.total_pages}</div>
              <div className="text-xs text-gray-500">Seiten</div>
            </div>
            <div className="bg-white rounded-xl p-3 text-center shadow-sm">
              <div className="text-xl font-bold text-red-600">{data.issues_by_severity.critical}</div>
              <div className="text-xs text-gray-500">Kritisch</div>
            </div>
            <div className="bg-white rounded-xl p-3 text-center shadow-sm">
              <div className="text-xl font-bold text-yellow-600">{data.issues_by_severity.warning}</div>
              <div className="text-xs text-gray-500">Warnungen</div>
            </div>
            <div className="bg-white rounded-xl p-3 text-center shadow-sm">
              <div className="text-xl font-bold text-green-600">{bfsg.passed}/{bfsg.total}</div>
              <div className="text-xs text-gray-500">BFSG ✓</div>
            </div>
          </div>
        </div>
      </div>

      {/* Level breakdown */}
      {data.issues_by_level && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Issues nach WCAG-Level</h3>
          <div className="grid grid-cols-3 gap-4">
            {LEVELS.map(lvl => {
              const ld = data.issues_by_level?.[lvl];
              if (!ld) return null;
              return (
                <div key={lvl} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${LEVEL_BADGE[lvl]}`}>{lvl}</span>
                    <span className="text-xs text-gray-500 font-medium">{ld.count} Issues · Score {ld.score}</span>
                  </div>
                  <div className="flex gap-3 text-xs">
                    <span className="text-red-600">{ld.critical} krit.</span>
                    <span className="text-yellow-600">{ld.warning} warn.</span>
                    <span className="text-blue-600">{ld.info} info</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div className={`h-1.5 rounded-full ${SCORE_COLOR(ld.score).bar}`}
                      style={{ width: `${ld.score}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Principle breakdown */}
      {data.issues_by_principle && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Issues nach WCAG-Prinzip</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {PRINCIPLES.map(prin => {
              const count = data.issues_by_principle?.[prin] ?? 0;
              const pct   = data.accessibility_issues > 0 ? Math.round(count / data.accessibility_issues * 100) : 0;
              return (
                <div key={prin} className="text-center">
                  <div className="text-2xl mb-1">{PRIN_ICONS[prin]}</div>
                  <div className="text-lg font-bold text-gray-800">{count}</div>
                  <div className="text-xs text-gray-500 capitalize">{prin}</div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5 mt-2">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {(["overview","issues","bfsg","urls"] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}>
              {tab === "overview" && "📊 Übersicht"}
              {tab === "issues"   && `🔍 Issues (${data.accessibility_issues})`}
              {tab === "bfsg"     && `🇩🇪 BFSG (${bfsg.compliance_pct}%)`}
              {tab === "urls"     && "🌐 Top URLs"}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Overview ── */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">WCAG Kategorie-Scores</h2>
          <div className="grid gap-3">
            {WCAG_CATS.map(cat => {
              const cd = data.issues_by_category[cat];
              if (!cd) return null;
              const cs = SCORE_COLOR(cd.score ?? 0);
              return (
                <div key={cat} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span>{CAT_ICONS[cat] || "📋"}</span>
                      <span className="font-semibold text-gray-800 text-sm">{cat}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-red-600 font-medium">{cd.critical} krit.</span>
                      <span className="text-yellow-600 font-medium">{cd.warning} warn.</span>
                      <span className="text-blue-600 font-medium">{cd.info} info</span>
                      <span className={`text-base font-bold ${cs.text}`}>{cd.score ?? 0}</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className={`h-2 rounded-full transition-all ${cs.bar}`} style={{ width: `${cd.score ?? 0}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          {data.crawl_completed_at && (
            <p className="text-xs text-gray-400 text-right">
              Analyse vom {new Date(data.crawl_completed_at).toLocaleString("de-DE")}
            </p>
          )}
        </div>
      )}

      {/* ── Issues ── */}
      {activeTab === "issues" && (
        <div className="space-y-4">
          {/* Filter bar */}
          <div className="flex flex-wrap gap-2 items-center bg-gray-50 rounded-xl p-3 border border-gray-200">
            <input type="text" placeholder="Issues suchen..."
              value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-44 bg-white" />

            {/* Level pills */}
            <div className="flex gap-1 flex-wrap">
              <button onClick={() => setFilterLevel("all")}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  filterLevel === "all" ? "bg-gray-800 text-white border-gray-800" : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
                }`}>Alle Level</button>
              {LEVELS.map(lvl => (
                <button key={lvl} onClick={() => setFilterLevel(lvl)}
                  className={`px-3 py-1 rounded-full text-xs font-bold border transition-colors ${
                    filterLevel === lvl ? "bg-gray-800 text-white border-gray-800" : LEVEL_BADGE[lvl] + " hover:opacity-80"
                  }`}>{lvl}</button>
              ))}
            </div>

            <select value={filterPrinciple} onChange={e => setFilterPrinciple(e.target.value)}
              className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="all">Alle Prinzipien</option>
              {PRINCIPLES.map(p => <option key={p} value={p}>{PRIN_ICONS[p]} {p.charAt(0).toUpperCase()+p.slice(1)}</option>)}
            </select>

            <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}
              className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="all">Alle Schweregrade</option>
              <option value="critical">Kritisch</option>
              <option value="warning">Warnung</option>
              <option value="info">Info</option>
            </select>

            <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}
              className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="all">Alle Kategorien</option>
              {WCAG_CATS.map(c => <option key={c} value={c}>{c}</option>)}
            </select>

            <span className="text-xs text-gray-400 ml-auto">{filteredIssues.length} Typ(en)</span>
          </div>

          <div className="space-y-3">
            {filteredIssues.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                Keine Issues entsprechen den Filtern
              </div>
            ) : filteredIssues.map((iss: A11yIssueType) => {
              const lvl  = getIssueLevel(iss.issue_type);
              const prin = getIssuePrinciple(iss.issue_type);
              return (
                <div key={iss.issue_type} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap mb-2">
                        {lvl !== "other" && (
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${LEVEL_BADGE[lvl]}`}>
                            WCAG {lvl}
                          </span>
                        )}
                        <span className="text-xs text-gray-500">
                          {PRIN_ICONS[prin] ?? ""} {prin !== "other" ? prin.charAt(0).toUpperCase()+prin.slice(1) : iss.category}
                        </span>
                        {iss.critical > 0 && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("critical")}`}>{iss.critical} kritisch</span>}
                        {iss.warning  > 0 && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("warning")}`}>{iss.warning} warnungen</span>}
                        {iss.info     > 0 && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("info")}`}>{iss.info} info</span>}
                      </div>
                      <p className="text-sm font-medium text-gray-800">{iss.description}</p>
                      {iss.recommendation && <p className="text-xs text-gray-500 mt-1">💡 {iss.recommendation}</p>}
                      <p className="text-xs text-gray-300 mt-1 font-mono">{iss.issue_type}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xl font-bold text-gray-700">{iss.total}</div>
                      <div className="text-xs text-gray-400">Vorkomm.</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── BFSG ── */}
      {activeTab === "bfsg" && (
        <div className="space-y-4">
          <div className={`rounded-xl border-2 p-5 ${data.bfsg_compliant ? "bg-green-50 border-green-300" : "bg-yellow-50 border-yellow-300"}`}>
            <div className="flex items-center justify-between">
              <div>
                <h3 className={`font-semibold ${data.bfsg_compliant ? "text-green-900" : "text-yellow-900"}`}>
                  {data.bfsg_compliant ? "🇩🇪 BFSG Konform" : "🇩🇪 BFSG Nicht Konform"}
                </h3>
                <p className={`text-sm mt-0.5 ${data.bfsg_compliant ? "text-green-700" : "text-yellow-700"}`}>
                  Barrierefreiheitsstärkungsgesetz — gilt für private Unternehmen ab 28. Juni 2025
                </p>
              </div>
              <div className="text-right">
                <div className={`text-3xl font-black ${data.bfsg_compliant ? "text-green-700" : "text-yellow-700"}`}>{bfsg.compliance_pct}%</div>
                <div className={`text-xs ${data.bfsg_compliant ? "text-green-600" : "text-yellow-600"}`}>{bfsg.passed}/{bfsg.total} bestanden</div>
              </div>
            </div>
            <div className={`mt-3 w-full rounded-full h-3 ${data.bfsg_compliant ? "bg-green-200" : "bg-yellow-200"}`}>
              <div className={`h-3 rounded-full transition-all ${data.bfsg_compliant ? "bg-green-600" : "bg-yellow-500"}`}
                style={{ width: `${bfsg.compliance_pct}%` }} />
            </div>
          </div>
          <div className="space-y-2">
            {bfsg.checks.map((chk: {id:string;title:string;description:string;passed:boolean;wcag:string;level:string}) => (
              <div key={chk.id}
                className={`flex items-start gap-4 p-4 rounded-xl border ${chk.passed ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                <div className={`text-xl mt-0.5 ${chk.passed ? "text-green-600" : "text-red-500"}`}>
                  {chk.passed ? "✅" : "❌"}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-gray-800">{chk.title}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{chk.wcag} · {chk.level}</span>
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">{chk.description}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-500">
            <strong>Hinweis:</strong> Automatische Analyse erkennt technische Kriterien. Vollständige BFSG-Konformität erfordert zusätzlich manuelle Tests (Screenreader, Farbkontrast).
          </div>
        </div>
      )}

      {/* ── URLs ── */}
      {activeTab === "urls" && (
        <div className="space-y-3">
          {data.top_affected_urls.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">Keine betroffenen Seiten gefunden</div>
          ) : data.top_affected_urls.map(pg => (
            <div key={pg.page_id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{pg.title || pg.url}</p>
                  <p className="text-xs text-gray-400 truncate mt-0.5">{pg.url}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {pg.critical > 0 && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("critical")}`}>{pg.critical} krit.</span>}
                  {pg.warning  > 0 && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("warning")}`}>{pg.warning} warn.</span>}
                  {pg.info     > 0 && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEV_BADGE("info")}`}>{pg.info} info</span>}
                  <span className="text-sm font-bold text-gray-600">{pg.total}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}
