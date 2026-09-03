"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Repeat, Upload, TrendingUp, Lightbulb } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { StatCard } from "@/components/ui/StatCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Anomaly, Insight, Transaction } from "@/types";

function currentMonthKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[] | null>(null);
  const [insights, setInsights] = useState<Insight[] | null>(null);
  const [recurringCount, setRecurringCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function loadAll() {
    try {
      const [txns, anom, ins, recurring] = await Promise.all([
        api.transactions.listAll(500),
        api.anomalies.list(0, 5),
        api.insights.list(),
        api.recurring.list(0, 1),
      ]);
      setTransactions(txns);
      setAnomalies(anom.data.items);
      setInsights(ins.data.items);
      setRecurringCount(recurring.data.total);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      await api.imports.upload(file);
      await loadAll();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  }

  const isLoading = transactions === null;

  const now = new Date();
  const monthKey = currentMonthKey(now);
  const monthTxns = (transactions ?? []).filter(
    (t) => currentMonthKey(new Date(t.transaction_date)) === monthKey
  );
  const income = monthTxns.filter((t) => t.transaction_type === "credit").reduce((s, t) => s + t.amount, 0);
  const expenses = monthTxns.filter((t) => t.transaction_type === "debit").reduce((s, t) => s + t.amount, 0);
  const balance = income - expenses;
  const savingsRate = income > 0 ? Math.round(((income - expenses) / income) * 100) : 0;

  const recentTransactions = (transactions ?? []).slice(0, 6);

  return (
    <AppShell>
      <div className="page-header">
        <h1 className="page-title">Welcome back{`, `}</h1>
        <p className="page-subtitle">Here is your financial overview for this month.</p>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      {isLoading ? (
        <div className="stat-grid">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} height={140} variant="rect" />
          ))}
        </div>
      ) : (
        <div className="stat-grid">
          <StatCard title="Income (this month)" value={`₹${income.toLocaleString()}`} icon="income" trend="up" trendValue="" color="emerald" />
          <StatCard title="Expenses (this month)" value={`₹${expenses.toLocaleString()}`} icon="expense" trend="down" trendValue="" color="rose" />
          <StatCard title="Net Balance" value={`₹${balance.toLocaleString()}`} icon="balance" trend={balance >= 0 ? "up" : "down"} trendValue="" color="blue" />
          <StatCard title="Savings Rate" value={`${savingsRate}%`} icon="savings" trend={savingsRate >= 0 ? "up" : "down"} trendValue="" color="primary" />
        </div>
      )}

      <div className="content-grid">
        <div className="card glass">
          <div className="card-header">
            <h2 className="card-title">Recent Transactions</h2>
          </div>
          <div className="card-body">
            {isLoading ? (
              <Skeleton height={200} />
            ) : recentTransactions.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">
                  <Upload size={32} />
                </div>
                <h3>No transactions yet</h3>
                <p>Upload your first CSV to get started with intelligent categorization and anomaly detection.</p>
                <label className="btn btn-primary mt-4 file-btn">
                  <input type="file" accept=".csv" hidden onChange={handleUpload} disabled={isUploading} />
                  {isUploading ? "Uploading…" : "Upload Data"}
                </label>
              </div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th className="text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTransactions.map((t) => (
                    <tr key={t.id}>
                      <td>{new Date(t.transaction_date).toLocaleDateString()}</td>
                      <td>
                        {t.description}
                        {t.is_anomaly && <span className="tag tag-rose ml-sm">unusual</span>}
                      </td>
                      <td><span className="tag">{t.category}</span></td>
                      <td className={`text-right ${t.transaction_type === "credit" ? "text-emerald" : "text-rose"}`}>
                        {t.transaction_type === "credit" ? "+" : "-"}₹{t.amount.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card glass">
          <div className="card-header">
            <h2 className="card-title">Quick Actions</h2>
          </div>
          <div className="card-body actions-list">
            <label className="btn btn-secondary action-btn file-btn">
              <input type="file" accept=".csv" hidden onChange={handleUpload} disabled={isUploading} />
              <Upload size={18} />
              <span>{isUploading ? "Uploading…" : "Upload Transactions"}</span>
            </label>
            <button className="btn btn-secondary action-btn" onClick={() => router.push("/analytics")}>
              <TrendingUp size={18} />
              <span>View Analytics</span>
            </button>
            <button className="btn btn-secondary action-btn" onClick={() => router.push("/anomalies")}>
              <AlertTriangle size={18} />
              <span>Check Anomalies ({anomalies?.length ?? 0})</span>
            </button>
            <button className="btn btn-secondary action-btn" onClick={() => router.push("/recurring")}>
              <Repeat size={18} />
              <span>Recurring Payments ({recurringCount ?? 0})</span>
            </button>
          </div>
        </div>
      </div>

      <div className="card glass mt-lg">
        <div className="card-header">
          <h2 className="card-title">
            <Lightbulb size={18} className="inline-icon" /> Insights
          </h2>
        </div>
        <div className="card-body">
          {isLoading ? (
            <Skeleton height={80} />
          ) : (insights ?? []).length === 0 ? (
            <p className="text-muted">
              No insights yet — insights are generated automatically after your next CSV import.
            </p>
          ) : (
            <ul className="insight-list">
              {(insights ?? []).map((insight) => (
                <li key={insight.id} className="insight-item">
                  {insight.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <footer className="footer">
        <p className="disclaimer">
          This platform provides ML-driven financial insights. Not financial advice.
          Always verify critical transactions with your banking institution.
        </p>
      </footer>
    </AppShell>
  );
}
