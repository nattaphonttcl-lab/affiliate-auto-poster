export type DashboardSummary = {
  products_total: number;
  caption_batches_total: number;
  promotional_images_total: number;
  scheduled_posts_total: number;
  scheduler_status_counts: Record<string, number>;
};

export type ActivityItem = {
  activity_type: string;
  title: string;
  subtitle: string;
  occurred_at: string;
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
