import axios from "axios";

import { clearSessionStorage, getAccessToken } from "./storage";

const defaultHost =
  typeof window !== "undefined" ? window.location.hostname : "localhost";
const defaultProtocol =
  typeof window !== "undefined" ? window.location.protocol : "http:";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  `${defaultProtocol}//${defaultHost}:8000/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearSessionStorage();
    }
    return Promise.reject(error);
  },
);
