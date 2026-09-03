"use client";

import { useEffect, useState } from "react";
import { RefreshCw, TrendingUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Forecast } from "@/types";

const PERIOD_LABELS: Record<string, string> = { "7d": "Next 7 Days", "30d": "Next 30 Days", "90d": "Next 90 Days" };

export default function ForecastPage() {
  const [forecasts, setForecasts] = useState<Forecast[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  async function load() {
    try {
      const { data } = await api.forecasts.list();
      setForecasts(data.items);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleGenerate() {
    setIsGenerating(true);
    setError(null);
    setStatus(null);
    try {
      const { data } = await api.forecasts.generate();
      setStatus((data as { message?: string }).message ?? null);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header page-header-row">
        <div>
          <h1 className="page-title">Expense Forecast</h1>
          <p className="page-subtitle">Predicted spending based on your recent daily transaction history.</p>
        </div>
        <button className="btn btn-primary" onClick={handleGenerate} disabled={isGenerating}>
          <RefreshCw size={18} className={isGenerating ? "spin" : ""} />
          {isGenerating ? "Generating…" : "Generate Forecast"}
        </button>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}
      {status && <div className="alert mb-lg">{status}</div>}

      {forecasts === null ? (
        <Skeleton height={300} />
      ) : forecasts.length === 0 ? (
        <div className="card glass">
          <div className="empty-state">
            <div className="empty-state-icon">
              <TrendingUp size={32} />
            </div>
            <h3>No forecast available yet</h3>
            <p>
              Needs at least 14 distinct days of transaction history, and a trained forecasting model
              (<code>make train</code>). Click &quot;Generate Forecast&quot; after uploading more data.
            </p>
          </div>
        </div>
      ) : (
        <div className="forecast-grid">
          {forecasts.map((f) => (
            <div key={f.period} className="card glass">
              <div className="card-header">
                <h2 className="card-title">{PERIOD_LABELS[f.period] ?? f.period}</h2>
                <span className="text-muted">via {f.method.replace(/_/g, " ")}</span>
              </div>
              <div className="forecast-total">₹{f.predicted_total.toLocaleString()}</div>
              <p className="text-muted mb-md">
                {new Date(f.start_date).toLocaleDateString()} – {new Date(f.end_date).toLocaleDateString()}
              </p>
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={f.daily_predictions.map((v, i) => ({ day: i + 1, amount: v }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)" }} />
                  <Line type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
