"use client";

import { useEffect, useState } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Anomaly } from "@/types";

const SEVERITY_CLASS: Record<Anomaly["severity"], string> = {
  low: "tag-blue",
  medium: "tag-amber",
  high: "tag-rose",
};

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  async function load() {
    try {
      const { data } = await api.anomalies.list(0, 100);
      setAnomalies(data.items);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRescan() {
    setIsScanning(true);
    setError(null);
    try {
      await api.anomalies.detect();
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsScanning(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header page-header-row">
        <div>
          <h1 className="page-title">Anomalies</h1>
          <p className="page-subtitle">
            Transactions that look unusual compared to your own history — not confirmed fraud.
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleRescan} disabled={isScanning}>
          <RefreshCw size={18} className={isScanning ? "spin" : ""} />
          {isScanning ? "Scanning…" : "Re-scan"}
        </button>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      {anomalies === null ? (
        <Skeleton height={300} />
      ) : anomalies.length === 0 ? (
        <div className="card glass">
          <div className="empty-state">
            <div className="empty-state-icon">
              <AlertTriangle size={32} />
            </div>
            <h3>No anomalies detected</h3>
            <p>Nothing unusual in your transaction history right now.</p>
          </div>
        </div>
      ) : (
        <div className="card-grid">
          {anomalies.map((a) => (
            <div key={a.id} className="card glass anomaly-card">
              <div className="anomaly-card-header">
                <span className={`tag ${SEVERITY_CLASS[a.severity]}`}>{a.severity} severity</span>
                <span className="text-muted">{new Date(a.transaction_date).toLocaleDateString()}</span>
              </div>
              <h3 className="anomaly-merchant">{a.merchant ?? a.description}</h3>
              <div className="anomaly-amount text-rose">₹{a.amount.toLocaleString()}</div>
              <p className="anomaly-reason">{a.reason}</p>
              <span className="tag mt-sm">{a.category}</span>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
