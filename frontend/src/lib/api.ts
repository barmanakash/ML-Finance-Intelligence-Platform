import axios from 'axios';
import type { PaginatedResponse, Transaction, User, Insight } from '../types';

const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  transactions: {
    list: () => apiClient.get<PaginatedResponse<Transaction>>('/api/transactions'),
  },
  insights: {
    get: () => apiClient.get<Insight[]>('/api/insights'),
  },
  user: {
    me: () => apiClient.get<User>('/api/users/me'),
  }
};
