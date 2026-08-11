import { ArrowUpRight, ArrowDownRight, Minus, DollarSign, Activity, Wallet, PiggyBank } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string;
  icon: 'income' | 'expense' | 'balance' | 'savings';
  trend: 'up' | 'down' | 'neutral';
  trendValue: string;
  color: 'emerald' | 'rose' | 'blue' | 'primary';
}

export function StatCard({ title, value, icon, trend, trendValue, color }: StatCardProps) {
  const IconMap = {
    income: DollarSign,
    expense: Activity,
    balance: Wallet,
    savings: PiggyBank
  };

  const TrendIconMap = {
    up: ArrowUpRight,
    down: ArrowDownRight,
    neutral: Minus
  };

  const IconComponent = IconMap[icon];
  const TrendIcon = TrendIconMap[trend];

  return (
    <div className={`card glass stat-card color-${color}`}>
      <div className="stat-card-header">
        <h3 className="stat-title">{title}</h3>
        <div className={`stat-icon-wrapper bg-${color}-alpha`}>
          <IconComponent size={20} className={`text-${color}`} />
        </div>
      </div>
      <div className="stat-card-body">
        <div className="stat-value">{value}</div>
        <div className={`stat-trend trend-${trend}`}>
          <TrendIcon size={16} />
          <span>{trendValue}</span>
          <span className="trend-label">vs last month</span>
        </div>
      </div>
    </div>
  );
}
