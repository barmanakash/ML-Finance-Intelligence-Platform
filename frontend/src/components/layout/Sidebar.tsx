import Link from 'next/link';
import { 
  LayoutDashboard, 
  Receipt, 
  PieChart, 
  AlertTriangle, 
  Repeat, 
  TrendingUp 
} from 'lucide-react';

export function Sidebar() {
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
          <li className="nav-item">
            <Link href="/" className="nav-link active">
              <LayoutDashboard size={20} />
              <span>Dashboard</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link href="/transactions" className="nav-link">
              <Receipt size={20} />
              <span>Transactions</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link href="/analytics" className="nav-link">
              <PieChart size={20} />
              <span>Analytics</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link href="/anomalies" className="nav-link">
              <AlertTriangle size={20} />
              <span>Anomalies</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link href="/recurring" className="nav-link">
              <Repeat size={20} />
              <span>Recurring</span>
            </Link>
          </li>
          <li className="nav-item">
            <Link href="/forecast" className="nav-link">
              <TrendingUp size={20} />
              <span>Forecast</span>
            </Link>
          </li>
        </ul>
      </nav>
    </aside>
  );
}
