"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useAuth } from "@/lib/auth";

/** Wraps every authenticated page: redirects to /login if there's no
 * session, otherwise renders the standard sidebar+header shell around
 * whatever page content is passed in. Centralizing this here means every
 * page under app/(dashboard) just writes its own content and gets the
 * auth guard + chrome for free.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="auth-loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-wrapper">
        <Header />
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
