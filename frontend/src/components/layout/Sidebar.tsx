"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Receipt, 
  PieChart, 
  AlertTriangle, 
  Repeat, 
  TrendingUp,
  Lightbulb,
  Tag,
} from 'lucide-react';

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: Receipt },
  { href: "/analytics", label: "Analytics", icon: PieChart },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/recurring", label: "Recurring", icon: Repeat },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/categories", label: "Categories", icon: Tag },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar glass">
      <div className="sidebar-header">
        <div className="logo">
          <TrendingUp className="logo-icon text-primary" size={28} />
          <span className="logo-text">FinIntel</span>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <ul className="nav-list">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <li className="nav-item" key={href}>
              <Link href={href} className={`nav-link ${pathname === href ? "active" : ""}`}>
                <Icon size={20} />
                <span>{label}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
