# Known Limitations

1. External provider integrations require runtime credentials and may be unavailable in test environments.
2. AI/image provider failover is validated via mocked/controlled test paths when credentials are absent.
3. SQLite is default for local development and not intended for production scale.
4. Alert rules and long-term retention tuning are not fully automated yet.
5. Redis-backed distributed rate limiting is not yet implemented.
