"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { TrendingUp } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { extractErrorMessage } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card glass card">
        <div className="logo auth-logo">
          <TrendingUp className="logo-icon text-primary" size={28} />
          <span className="logo-text">FinIntel</span>
        </div>
        <h1 className="page-title">Welcome back</h1>
        <p className="page-subtitle mb-lg">Log in to see your financial overview.</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="form-field">
            <span>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label className="form-field">
            <span>Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Logging in…" : "Log in"}
          </button>
        </form>

        <p className="auth-switch">
          Don&apos;t have an account? <Link href="/register">Create one</Link>
        </p>
        <p className="auth-hint">Demo account: demo@example.com / DemoPass123! (after `make seed`)</p>
      </div>
    </div>
  );
}
