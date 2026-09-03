"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Repeat } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { RecurringPayment } from "@/types";

export default function RecurringPage() {
  const [items, setItems] = useState<RecurringPayment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);

  async function load() {
    try {
      const { data } = await api.recurring.list(0, 100);
      setItems(data.items);
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
      await api.recurring.detect();
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
          <h1 className="page-title">Recurring Payments</h1>
          <p className="page-subtitle">Subscriptions and bills detected from your transaction history.</p>
        </div>
        <button className="btn btn-primary" onClick={handleRescan} disabled={isScanning}>
          <RefreshCw size={18} className={isScanning ? "spin" : ""} />
          {isScanning ? "Scanning…" : "Re-scan"}
        </button>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      {items === null ? (
        <Skeleton height={300} />
      ) : items.length === 0 ? (
        <div className="card glass">
          <div className="empty-state">
            <div className="empty-state-icon">
              <Repeat size={32} />
            </div>
            <h3>No recurring payments found</h3>
            <p>Needs at least 3 similarly-timed charges from the same merchant to detect a pattern.</p>
          </div>
        </div>
      ) : (
        <div className="card glass">
          <div className="card-body">
            <table className="table">
              <thead>
                <tr>
                  <th>Merchant</th>
                  <th>Category</th>
                  <th>Frequency</th>
                  <th className="text-right">Avg. Amount</th>
                  <th>Next Expected</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id}>
                    <td>{r.merchant}</td>
                    <td><span className="tag">{r.category}</span></td>
                    <td className="capitalize">{r.frequency}</td>
                    <td className="text-right">₹{r.average_amount.toLocaleString()}</td>
                    <td>{new Date(r.next_expected_date).toLocaleDateString()}</td>
                    <td>
                      <div className="confidence-bar">
                        <div className="confidence-fill" style={{ width: `${Math.round(r.confidence * 100)}%` }} />
                      </div>
                      <span className="text-muted confidence-label">{Math.round(r.confidence * 100)}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}
