import { apiClient } from "./api-client";
import type {
  ActivityItem,
  DashboardSummary,
  PaginatedResponse,
  Product,
  PublishingJob,
  SocialAccount,
  User,
} from "../types/api";

export async function login(email: string, password: string) {
  const { data } = await apiClient.post<{ access_token: string; token_type: string }>(
    "/auth/login",
    { email, password },
  );
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await apiClient.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export async function getDashboardSummary() {
  const { data } = await apiClient.get<DashboardSummary>("/dashboard/summary");
  return data;
}

export async function getDashboardActivities() {
  const { data } = await apiClient.get<ActivityItem[]>("/dashboard/activities");
  return data;
}

export async function getProducts() {
  const { data } = await apiClient.get<{ items: Product[] } | Product[]>("/products");
  if (Array.isArray(data)) {
    return data;
  }
  return data.items;
}

export async function refreshProduct(productId: number) {
  const { data } = await apiClient.post(`/products/${productId}/refresh`);
  return data;
}

export async function getAiTemplates() {
  const { data } = await apiClient.get("/ai/templates");
  return data;
}

export async function getAiHistory() {
  const { data } = await apiClient.get("/ai/history");
  return data;
}

export async function getImageTemplates() {
  const { data } = await apiClient.get("/images/templates");
  return data;
}

export async function getImageHistory() {
  const { data } = await apiClient.get("/images/history");
  return data;
}

export async function getPublishingJobs() {
  const { data } = await apiClient.get<PaginatedResponse<PublishingJob>>(
    "/publish/jobs",
  );
  return data;
}

export async function getPublishingHistory() {
  const { data } = await apiClient.get("/publish/history");
  return data;
}

export async function retryPublish(jobId: number) {
  const { data } = await apiClient.post("/publish/retry", { job_id: jobId });
  return data;
}

export async function cancelPublish(jobId: number) {
  const { data } = await apiClient.post("/publish/cancel", { job_id: jobId });
  return data;
}

export async function getSocialAccounts() {
  const { data } = await apiClient.get<SocialAccount[]>("/social/accounts");
  return data;
}

export async function getAnalyticsOverview() {
  const { data } = await apiClient.get("/analytics/overview");
  return data;
}

export async function getAnalyticsEvents() {
  const { data } = await apiClient.get("/analytics/events");
  return data;
}

export async function getUsers() {
  const { data } = await apiClient.get<User[]>("/users");
  return data;
}

export async function getHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}
