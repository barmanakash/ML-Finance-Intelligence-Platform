"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Lightbulb } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Insight } from "@/types";

export default function InsightsPage() {
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  async function load() {
    try {
      const { data } = await api.insights.list();
      setInsights(data.items);
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
    try {
      await api.insights.generate();
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
          <h1 className="page-title">Insights</h1>
          <p className="page-subtitle">Deterministic, rule-based observations about your spending — no AI guesswork.</p>
        </div>
        <button className="btn btn-primary" onClick={handleGenerate} disabled={isGenerating}>
          <RefreshCw size={18} className={isGenerating ? "spin" : ""} />
          {isGenerating ? "Generating…" : "Re-generate"}
        </button>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      {insights === null ? (
        <Skeleton height={200} />
      ) : insights.length === 0 ? (
        <div className="card glass">
          <div className="empty-state">
            <div className="empty-state-icon">
              <Lightbulb size={32} />
            </div>
            <h3>No insights yet</h3>
            <p>Insights need a couple of months of transaction history to compare against.</p>
          </div>
        </div>
      ) : (
        <div className="card glass">
          <div className="card-body">
            <ul className="insight-list">
              {insights.map((insight) => (
                <li key={insight.id} className="insight-item">
                  <span className="tag mr-sm">{insight.type.replace(/_/g, " ")}</span>
                  {insight.message}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </AppShell>
  );
}
