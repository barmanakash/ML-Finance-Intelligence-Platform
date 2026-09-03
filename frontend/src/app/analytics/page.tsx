"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Transaction } from "@/types";

const CHART_COLORS = ["#3b82f6", "#10b981", "#f43f5e", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"];

function monthLabel(date: Date): string {
  return date.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
}

export default function AnalyticsPage() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.transactions
      .listAll(1000)
      .then((items) => setTransactions(items))
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  const debits = (transactions ?? []).filter((t) => t.transaction_type === "debit");

  const byCategory = Object.entries(
    debits.reduce<Record<string, number>>((acc, t) => {
      acc[t.category] = (acc[t.category] ?? 0) + t.amount;
      return acc;
    }, {})
  )
    .map(([category, amount]) => ({ category, amount: Math.round(amount) }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 10);

  const byMonth = Object.entries(
    debits.reduce<Record<string, number>>((acc, t) => {
      const d = new Date(t.transaction_date);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      acc[key] = (acc[key] ?? 0) + t.amount;
      return acc;
    }, {})
  )
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([key, amount]) => {
      const [year, month] = key.split("-").map(Number);
      return { month: monthLabel(new Date(year, month - 1, 1)), amount: Math.round(amount) };
    });

  const topMerchants = Object.entries(
    debits.reduce<Record<string, number>>((acc, t) => {
      const key = t.merchant ?? t.description;
      acc[key] = (acc[key] ?? 0) + t.amount;
      return acc;
    }, {})
  )
    .map(([merchant, amount]) => ({ merchant, amount: Math.round(amount) }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 8);

  const isLoading = transactions === null;

  return (
    <AppShell>
      <div className="page-header">
        <h1 className="page-title">Analytics</h1>
        <p className="page-subtitle">Spending patterns across categories, months, and merchants.</p>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      {isLoading ? (
        <Skeleton height={400} />
      ) : debits.length === 0 ? (
        <div className="card glass">
          <div className="empty-state">
            <h3>No spending data yet</h3>
            <p>Upload a CSV of transactions to see analytics here.</p>
          </div>
        </div>
      ) : (
        <div className="analytics-grid">
          <div className="card glass">
            <div className="card-header">
              <h2 className="card-title">Spending by Category</h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={byCategory} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis dataKey="category" type="category" stroke="#94a3b8" fontSize={12} width={100} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)" }} />
                <Bar dataKey="amount" radius={[0, 6, 6, 0]}>
                  {byCategory.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card glass">
            <div className="card-header">
              <h2 className="card-title">Monthly Spending Trend</h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={byMonth}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)" }} />
                <Line type="monotone" dataKey="amount" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card glass analytics-full-width">
            <div className="card-header">
              <h2 className="card-title">Top Merchants</h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topMerchants}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="merchant" stroke="#94a3b8" fontSize={11} angle={-20} textAnchor="end" height={70} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)" }} />
                <Bar dataKey="amount" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </AppShell>
  );
}
