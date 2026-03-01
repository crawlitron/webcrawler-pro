"use client";
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken, storeUser } from "../../../lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const token = params.get("token");
    const email = params.get("email") ?? "";
    const name = params.get("name") ?? "";
    const error = params.get("error");

    if (error) {
      router.replace(`/auth/login?error=${error}`);
      return;
    }
    if (!token) {
      router.replace("/auth/login?error=no_token");
      return;
    }

    setToken(token);
    storeUser({
      id: 0,
      email,
      full_name: name,
      is_active: true,
      is_admin: false,
      created_at: new Date().toISOString(),
    });
    router.replace("/");
  }, [params, router]);

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4 animate-pulse">🔄</div>
        <p className="text-gray-400">Google Login wird verarbeitet...</p>
      </div>
    </div>
  );
}
