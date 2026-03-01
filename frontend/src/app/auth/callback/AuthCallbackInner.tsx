"use client";
import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken, storeUser } from "../../../lib/auth";

export default function AuthCallbackInner() {
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

  return null;
}
