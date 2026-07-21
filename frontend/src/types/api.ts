export type DashboardTotals = {
  products: number;
  caption_batches: number;
  promotional_images: number;
  scheduled_posts: number;
};

export type DashboardSchedulerBreakdown = {
  awaiting_confirmation: number;
  confirmed: number;
  processing: number;
  published: number;
  failed: number;
};

export type DashboardSummaryResponse = {
  totals: DashboardTotals;
  scheduler: DashboardSchedulerBreakdown;
};

export type DashboardActivityItem = {
  type: string;
  reference_id: number;
  status: string | null;
  occurred_at: string;
  description: string;
};

export type DashboardActivityResponse = {
  items: DashboardActivityItem[];
};

export type AnalyticsDailyPoint = {
  day: string;
  count: number;
};

export type AnalyticsOverviewResponse = {
  totals: Record<string, number>;
  daily: AnalyticsDailyPoint[];
};

export type AnalyticsEvent = {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: number | null;
  metadata: Record<string, string | number | boolean | null>;
  occurred_at: string;
};

export type AnalyticsEventsResponse = {
  items: AnalyticsEvent[];
};

export type PaginatedResponse<T> = {
  total: number;
  limit: number;
  offset: number;
  items: T[];
};

export type User = {
  id: number;
  email: string;
  is_active: boolean;
};

export type Product = {
  id: number;
  title: string;
  price: string;
  discount?: string | null;
  marketplace: string;
  shop_name?: string | null;
  category?: string | null;
  updated_at: string;
};

export type SocialAccount = {
  id: number;
  owner_user_id: number;
  platform: string;
  account_name: string;
  account_identifier: string;
  permissions: string[];
  is_active: boolean;
  timezone: string;
  rate_limit_per_minute: number;
};

export type PublishingJob = {
  id: number;
  platform: string;
  post_type: string;
  status: string;
  retry_count: number;
  scheduled_for?: string | null;
  published_at?: string | null;
  created_at: string;
};
