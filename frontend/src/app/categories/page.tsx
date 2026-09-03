"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, extractErrorMessage } from "@/lib/api";
import type { Category } from "@/types";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function load() {
    try {
      const { data } = await api.categories.list();
      setCategories(data.items);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.categories.create(newName.trim());
      setNewName("");
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    setError(null);
    try {
      await api.categories.remove(id);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1 className="page-title">Categories</h1>
        <p className="page-subtitle">System defaults plus any custom categories you&apos;ve added.</p>
      </div>

      {error && <div className="alert alert-error mb-lg">{error}</div>}

      <form onSubmit={handleCreate} className="filter-bar">
        <input
          type="text"
          placeholder="New category name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          maxLength={50}
        />
        <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
          <Plus size={16} /> Add
        </button>
      </form>

      {categories === null ? (
        <Skeleton height={300} />
      ) : (
        <div className="card glass">
          <div className="card-body">
            <div className="category-grid">
              {categories.map((c) => (
                <div key={c.id} className="category-chip">
                  <span>{c.name}</span>
                  {c.is_default ? (
                    <span className="text-muted category-default-label">default</span>
                  ) : (
                    <button className="icon-btn-sm" onClick={() => handleDelete(c.id)} title="Delete category">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
