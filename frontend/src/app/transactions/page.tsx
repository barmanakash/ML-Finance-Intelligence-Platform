"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import { Upload } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Category, Transaction } from "@/types";

const PAGE_SIZE = 20;

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function load() {
    try {
      const { data } = await api.transactions.list({
        skip,
        limit: PAGE_SIZE,
        category: categoryFilter || undefined,
        transaction_type: typeFilter || undefined,
      });
      setTransactions(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  useEffect(() => {
    api.categories.list().then((res) => setCategories(res.data.items)).catch(() => {});
  }, []);

  useEffect(() => {
    setTransactions(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skip, categoryFilter, typeFilter]);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      await api.imports.upload(file);
      setSkip(0);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(skip / PAGE_SIZE) + 1;

  return (
    <AppShell>
      <div className="page-header page-header-row">
        <div>
          <h1 className="page-title">Transactions</h1>
          <p className="page-subtitle">{total} total transactions</p>
        </div>
        <label className="btn btn-primary file-btn">
          <input type="file" accept=".csv" hidden onChange={handleUpload} disabled={isUploading} />
          <Upload size={18} />
          {isUploading ? "Uploading…" : "Upload CSV"}
        </label>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      <div className="filter-bar">
        <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setSkip(0); }}>
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.name}>{c.name}</option>
          ))}
        </select>
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setSkip(0); }}>
          <option value="">All types</option>
          <option value="debit">Debit</option>
          <option value="credit">Credit</option>
        </select>
      </div>

      <div className="card glass">
        <div className="card-body">
          {transactions === null ? (
            <Skeleton height={400} />
          ) : transactions.length === 0 ? (
            <div className="empty-state">
              <h3>No transactions found</h3>
              <p>Try clearing your filters, or upload a CSV to get started.</p>
            </div>
          ) : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Merchant</th>
                    <th>Category</th>
                    <th>Type</th>
                    <th className="text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id}>
                      <td>{new Date(t.transaction_date).toLocaleDateString()}</td>
                      <td>
                        {t.description}
                        {t.is_anomaly && <span className="tag tag-rose ml-sm">unusual</span>}
                      </td>
                      <td>{t.merchant ?? "—"}</td>
                      <td><span className="tag">{t.category}</span></td>
                      <td>{t.transaction_type}</td>
                      <td className={`text-right ${t.transaction_type === "credit" ? "text-emerald" : "text-rose"}`}>
                        {t.transaction_type === "credit" ? "+" : "-"}₹{t.amount.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="pagination">
                <button className="btn btn-secondary" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}>
                  Previous
                </button>
                <span>Page {currentPage} of {totalPages}</span>
                <button
                  className="btn btn-secondary"
                  disabled={currentPage >= totalPages}
                  onClick={() => setSkip(skip + PAGE_SIZE)}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
