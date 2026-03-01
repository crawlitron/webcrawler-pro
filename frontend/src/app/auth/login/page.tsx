import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <Suspense
        fallback={
          <div className="w-full max-w-md bg-gray-900 rounded-xl border border-gray-800 p-8 text-center">
            <div className="text-4xl mb-4">🕷️</div>
            <p className="text-gray-400">Laden...</p>
          </div>
        }
      >
        <LoginForm />
      </Suspense>
    </div>
  );
}
