"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const STEPS = ["Admin-Konto", "E-Mail", "Google APIs", "Allgemein"];

interface AdminData { email: string; password: string; confirmPassword: string; full_name: string; }
interface EmailData { smtp_host: string; smtp_port: string; smtp_user: string; smtp_password: string; smtp_from: string; }
interface GoogleData { google_client_id: string; google_client_secret: string; ga_measurement_id: string; }
interface GeneralData { app_url: string; max_concurrent_crawls: string; }

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [admin, setAdmin] = useState<AdminData>({ email: "", password: "", confirmPassword: "", full_name: "" });
  const [email, setEmail] = useState<EmailData>({ smtp_host: "", smtp_port: "587", smtp_user: "", smtp_password: "", smtp_from: "" });
  const [google, setGoogle] = useState<GoogleData>({ google_client_id: "", google_client_secret: "", ga_measurement_id: "" });
  const [general, setGeneral] = useState<GeneralData>({ app_url: "", max_concurrent_crawls: "3" });

  const inputClass = "w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  async function handleFinish() {
    if (!admin.email || !admin.password) { setError("Email und Passwort sind Pflichtfelder."); return; }
    if (admin.password !== admin.confirmPassword) { setError("Passwörter stimmen nicht überein."); return; }
    if (admin.password.length < 8) { setError("Passwort muss mindestens 8 Zeichen haben."); return; }

    setLoading(true); setError("");
    try {
      const settings: Record<string, string> = {};
      if (email.smtp_host) { Object.assign(settings, { smtp_host: email.smtp_host, smtp_port: email.smtp_port, smtp_user: email.smtp_user, smtp_password: email.smtp_password, smtp_from: email.smtp_from }); }
      if (google.google_client_id) { Object.assign(settings, { google_client_id: google.google_client_id, google_client_secret: google.google_client_secret, ga_measurement_id: google.ga_measurement_id }); }
      if (general.app_url) { Object.assign(settings, { app_url: general.app_url, max_concurrent_crawls: general.max_concurrent_crawls }); }

      const res = await fetch("/api/setup/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin: { email: admin.email, password: admin.password, full_name: admin.full_name }, settings }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data as {detail?: string}).detail || "Setup fehlgeschlagen");
      }
      router.push("/auth/login?setup=done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unbekannter Fehler");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🕷️</div>
          <h1 className="text-2xl font-bold text-gray-900">WebCrawler Pro</h1>
          <p className="text-gray-500 text-sm mt-1">Ersteinrichtung — Schritt {step + 1} von {STEPS.length}</p>
        </div>

        {/* Progress Bar */}
        <div className="flex gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={s} className="flex-1">
              <div className={`h-2 rounded-full transition-colors ${
                i < step ? "bg-blue-500" : i === step ? "bg-blue-400" : "bg-gray-200"
              }`} />
              <p className={`text-xs mt-1 text-center truncate ${
                i === step ? "text-blue-600 font-medium" : "text-gray-400"
              }`}>{s}</p>
            </div>
          ))}
        </div>

        {/* Step 0: Admin */}
        {step === 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">👤 Admin-Konto erstellen</h2>
            <div>
              <label className={labelClass}>E-Mail *</label>
              <input type="email" className={inputClass} placeholder="admin@beispiel.de"
                value={admin.email} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdmin({...admin, email: e.target.value})} />
            </div>
            <div>
              <label className={labelClass}>Name</label>
              <input type="text" className={inputClass} placeholder="Max Mustermann"
                value={admin.full_name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdmin({...admin, full_name: e.target.value})} />
            </div>
            <div>
              <label className={labelClass}>Passwort * (min. 8 Zeichen)</label>
              <input type="password" className={inputClass} placeholder="••••••••"
                value={admin.password} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdmin({...admin, password: e.target.value})} />
            </div>
            <div>
              <label className={labelClass}>Passwort bestätigen *</label>
              <input type="password" className={inputClass} placeholder="••••••••"
                value={admin.confirmPassword} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdmin({...admin, confirmPassword: e.target.value})} />
            </div>
          </div>
        )}

        {/* Step 1: Email */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="flex justify-between items-start">
              <h2 className="text-lg font-semibold text-gray-800">📧 E-Mail Konfiguration</h2>
              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded">Optional</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className={labelClass}>SMTP Host</label>
                <input type="text" className={inputClass} placeholder="smtp.gmail.com"
                  value={email.smtp_host} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail({...email, smtp_host: e.target.value})} />
              </div>
              <div>
                <label className={labelClass}>Port</label>
                <input type="text" className={inputClass} placeholder="587"
                  value={email.smtp_port} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail({...email, smtp_port: e.target.value})} />
              </div>
              <div>
                <label className={labelClass}>SMTP User</label>
                <input type="text" className={inputClass} placeholder="user@gmail.com"
                  value={email.smtp_user} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail({...email, smtp_user: e.target.value})} />
              </div>
              <div className="col-span-2">
                <label className={labelClass}>SMTP Passwort</label>
                <input type="password" className={inputClass} placeholder="••••••••"
                  value={email.smtp_password} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail({...email, smtp_password: e.target.value})} />
              </div>
              <div className="col-span-2">
                <label className={labelClass}>Absender-Email</label>
                <input type="email" className={inputClass} placeholder="noreply@beispiel.de"
                  value={email.smtp_from} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail({...email, smtp_from: e.target.value})} />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Google */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="flex justify-between items-start">
              <h2 className="text-lg font-semibold text-gray-800">🔍 Google Integrationen</h2>
              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded">Optional</span>
            </div>
            <div>
              <label className={labelClass}>Search Console Client ID</label>
              <input type="text" className={inputClass} placeholder="123456789-abc.apps.googleusercontent.com"
                value={google.google_client_id} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGoogle({...google, google_client_id: e.target.value})} />
            </div>
            <div>
              <label className={labelClass}>Search Console Client Secret</label>
              <input type="password" className={inputClass} placeholder="GOCSPX-..."
                value={google.google_client_secret} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGoogle({...google, google_client_secret: e.target.value})} />
            </div>
            <div>
              <label className={labelClass}>Google Analytics Measurement ID</label>
              <input type="text" className={inputClass} placeholder="G-XXXXXXXXXX"
                value={google.ga_measurement_id} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGoogle({...google, ga_measurement_id: e.target.value})} />
            </div>
            <p className="text-xs text-gray-400">Keys werden verschlüsselt in der Datenbank gespeichert (AES-128).</p>
          </div>
        )}

        {/* Step 3: General */}
        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">⚙️ Allgemeine Einstellungen</h2>
            <div>
              <label className={labelClass}>App-URL</label>
              <input type="url" className={inputClass} placeholder="http://meinserver.de:44544"
                value={general.app_url} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGeneral({...general, app_url: e.target.value})} />
              <p className="text-xs text-gray-400 mt-1">Wird für Email-Links und OAuth-Callbacks verwendet.</p>
            </div>
            <div>
              <label className={labelClass}>Max. gleichzeitige Crawls</label>
              <select className={inputClass}
                value={general.max_concurrent_crawls}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setGeneral({...general, max_concurrent_crawls: e.target.value})}>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="5">5</option>
                <option value="10">10</option>
              </select>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex justify-between mt-8">
          <button
            onClick={() => setStep(s => Math.max(0, s - 1))}
            disabled={step === 0}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-30 transition-opacity">
            ← Zurück
          </button>

          <div className="flex gap-3">
            {step > 0 && step < STEPS.length - 1 && (
              <button
                onClick={() => setStep(s => s + 1)}
                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg transition-colors">
                Überspringen
              </button>
            )}

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => { setError(""); setStep(s => s + 1); }}
                className="px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
                Weiter →
              </button>
            ) : (
              <button
                onClick={handleFinish}
                disabled={loading}
                className="px-6 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors">
                {loading ? "Einrichten..." : "✓ Setup abschließen"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
