"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { StatCard } from "@/components/ui/StatCard";
import { Upload, BarChart3, AlertTriangle } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="layout">
      <Sidebar />
      <div className="main-wrapper">
        <Header />
        <main className="main-content">
          <div className="page-header">
            <h1 className="page-title">Welcome back, Alex</h1>
            <p className="page-subtitle">Here is your financial overview for this month.</p>
          </div>

          <div className="stat-grid">
            <StatCard
              title="Total Income"
              value="$12,450.00"
              icon="income"
              trend="up"
              trendValue="+14.5%"
              color="emerald"
            />
            <StatCard
              title="Total Expenses"
              value="$4,230.50"
              icon="expense"
              trend="down"
              trendValue="-2.4%"
              color="rose"
            />
            <StatCard
              title="Current Balance"
              value="$8,219.50"
              icon="balance"
              trend="up"
              trendValue="+8.2%"
              color="blue"
            />
            <StatCard
              title="Savings Rate"
              value="66%"
              icon="savings"
              trend="up"
              trendValue="+4.1%"
              color="primary"
            />
          </div>

          <div className="content-grid">
            <div className="card glass">
              <div className="card-header">
                <h2 className="card-title">Recent Activity</h2>
              </div>
              <div className="card-body empty-state">
                <div className="empty-state-icon">
                  <Upload size={32} />
                </div>
                <h3>No transactions yet</h3>
                <p>Upload your first CSV to get started with intelligent categorization and anomaly detection.</p>
                <button className="btn btn-primary mt-4">Upload Data</button>
              </div>
            </div>

            <div className="card glass">
              <div className="card-header">
                <h2 className="card-title">Quick Actions</h2>
              </div>
              <div className="card-body actions-list">
                <button className="btn btn-secondary action-btn">
                  <Upload size={18} />
                  <span>Upload Transactions</span>
                </button>
                <button className="btn btn-secondary action-btn">
                  <BarChart3 size={18} />
                  <span>View Analytics</span>
                </button>
                <button className="btn btn-secondary action-btn">
                  <AlertTriangle size={18} />
                  <span>Check Anomalies</span>
                </button>
              </div>
            </div>
          </div>

          <footer className="footer">
            <p className="disclaimer">
              This platform provides ML-driven financial insights. Not financial advice. 
              Always verify critical transactions with your banking institution.
            </p>
          </footer>
        </main>
      </div>
    </div>
  );
}
