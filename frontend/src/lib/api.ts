import axios from "axios";
import type {
  Anomaly,
  ApiErrorBody,
  Category,
  Forecast,
  ImportRecord,
  Insight,
  ModelStatus,
  PaginatedResponse,
  RecurringPayment,
  TokenResponse,
  Transaction,
  User,
} from "../types";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "finintel_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthRoute =
      typeof window !== "undefined" &&
      (window.location.pathname === "/login" || window.location.pathname === "/register");
    if (error.response?.status === 401 && !isAuthRoute && typeof window !== "undefined") {
      clearToken();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

/** Pulls the {code, message} out of the app's documented error envelope,
 * falling back to a generic message for network errors / unexpected shapes.
 */
export function extractErrorMessage(error: unknown): string {
  const body = (error as { response?: { data?: ApiErrorBody } })?.response?.data;
  return body?.error?.message ?? "Something went wrong. Please try again.";
}

export const api = {
  auth: {
    register: (email: string, password: string, full_name: string) =>
      apiClient.post<User>("/api/v1/auth/register", { email, password, full_name }),
    login: (email: string, password: string) =>
      apiClient.post<TokenResponse>("/api/v1/auth/login", { email, password }),
    logout: () => apiClient.post("/api/v1/auth/logout"),
  },
  users: {
    me: () => apiClient.get<User>("/api/v1/users/me"),
  },
  imports: {
    upload: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return apiClient.post<ImportRecord>("/api/v1/imports", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    list: (skip = 0, limit = 20) =>
      apiClient.get<PaginatedResponse<ImportRecord>>("/api/v1/imports", { params: { skip, limit } }),
  },
  transactions: {
    list: (params: { skip?: number; limit?: number; category?: string; transaction_type?: string } = {}) =>
      apiClient.get<PaginatedResponse<Transaction>>("/api/v1/transactions", { params }),
    get: (id: string) => apiClient.get<Transaction>(`/api/v1/transactions/${id}`),
  },
  categories: {
    list: () => apiClient.get<{ items: Category[] }>("/api/v1/categories"),
    create: (name: string) => apiClient.post<Category>("/api/v1/categories", { name }),
    remove: (id: string) => apiClient.delete(`/api/v1/categories/${id}`),
  },
  anomalies: {
    list: (skip = 0, limit = 50) =>
      apiClient.get<PaginatedResponse<Anomaly>>("/api/v1/anomalies", { params: { skip, limit } }),
    detect: () => apiClient.post("/api/v1/anomalies/detect"),
  },
  recurring: {
    list: (skip = 0, limit = 50) =>
      apiClient.get<PaginatedResponse<RecurringPayment>>("/api/v1/recurring", { params: { skip, limit } }),
    detect: () => apiClient.post("/api/v1/recurring/detect"),
  },
  forecasts: {
    list: () => apiClient.get<{ items: Forecast[] }>("/api/v1/forecasts"),
    generate: () => apiClient.post("/api/v1/forecasts/generate"),
  },
  insights: {
    list: () => apiClient.get<{ items: Insight[] }>("/api/v1/insights"),
    generate: () => apiClient.post("/api/v1/insights/generate"),
  },
  ml: {
    models: () => apiClient.get<ModelStatus[]>("/api/v1/ml/models"),
  },
};
