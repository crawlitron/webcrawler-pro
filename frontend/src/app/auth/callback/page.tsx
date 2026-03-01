import { Suspense } from "react";
import AuthCallbackInner from "./AuthCallbackInner";

export default function AuthCallbackPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4 animate-pulse">🔄</div>
        <p className="text-gray-400">Google Login wird verarbeitet...</p>
        <Suspense fallback={null}>
          <AuthCallbackInner />
        </Suspense>
      </div>
    </div>
  );
}
