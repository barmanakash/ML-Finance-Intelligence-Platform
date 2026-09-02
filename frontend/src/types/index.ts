// Mirrors backend/app/schemas/*.py response shapes exactly — see those
// files for the source of truth. Kept in one file since this is a small
// portfolio app, not because everything belongs together long-term.

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Transaction {
  id: string;
  transaction_date: string;
  description: string;
  merchant: string | null;
  amount: number;
  currency: string;
  transaction_type: "debit" | "credit";
  category: string;
  is_anomaly: boolean;
  anomaly_score: number | null;
  import_id: string;
  reference: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface ImportRowError {
  row: number;
  message: string;
}

export interface ImportRecord {
  id: string;
  filename: string;
  status: "completed" | "partial" | "failed";
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  errors: ImportRowError[];
  created_at: string;
}

export interface Category {
  id: string;
  name: string;
  is_default: boolean;
  created_at: string;
}

export interface Anomaly {
  id: string;
  transaction_id: string;
  amount: number;
  merchant: string | null;
  description: string;
  category: string;
  transaction_date: string;
  anomaly_score: number;
  severity: "low" | "medium" | "high";
  reason: string;
  created_at: string;
}

export interface RecurringPayment {
  id: string;
  merchant: string;
  category: string;
  frequency: "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly";
  average_amount: number;
  occurrences: number;
  confidence: number;
  last_transaction_date: string;
  next_expected_date: string;
}

export interface Forecast {
  period: "7d" | "30d" | "90d";
  method: string;
  daily_predictions: number[];
  predicted_total: number;
  start_date: string;
  end_date: string;
  generated_at: string;
}

export interface Insight {
  id: string;
  type: string;
  message: string;
  created_at: string;
}

export interface ModelStatus {
  model_name: string;
  is_ready: boolean;
  active_version: number | null;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}
