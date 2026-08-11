export interface User {
  id: string;
  email: string;
  display_name: string;
  currency: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  transaction_date: string;
  description: string;
  merchant: string;
  amount: number;
  currency: string;
  transaction_type: 'DEBIT' | 'CREDIT';
  category: string;
  category_confidence: number;
  is_anomaly: boolean;
  anomaly_score: number;
}

export interface Category {
  id: string;
  name: string;
  type: string;
  color: string;
}

export interface Anomaly {
  id: string;
  transaction_id: string;
  anomaly_score: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reasons: string[];
}

export interface RecurringTransaction {
  id: string;
  merchant: string;
  frequency: 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY';
  average_amount: number;
  confidence: number;
  next_expected_date: string;
}

export interface Forecast {
  id: string;
  period: string;
  predicted_amount: number;
  confidence_lower: number;
  confidence_upper: number;
  model_version: string;
}

export interface Insight {
  id: string;
  type: string;
  message: string;
  data: any;
  period: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: any;
    request_id: string;
  };
}

export interface HealthResponse {
  status: string;
  mongodb: string;
  timestamp: string;
  version: string;
}
