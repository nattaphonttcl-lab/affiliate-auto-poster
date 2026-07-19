# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  # Affiliate Auto Poster Enterprise Dashboard

  Enterprise React dashboard for Affiliate Auto Poster backend modules.

  ## Stack

  - React 19 + TypeScript + Vite
  - React Router
  - TanStack Query
  - Axios
  - React Hook Form + Zod
  - TailwindCSS
  - Recharts
  - TanStack React Table
  - React DnD
  - Framer Motion
  - Vitest + React Testing Library
  - Playwright

  ## Architecture

  - App Providers:
    - Query client
    - Auth/session provider
    - Theme provider (dark/light)
    - DnD provider
    - Toast notifications
  - Global Layout:
    - Top navigation
    - Sidebar
    - Breadcrumb
    - Notification center
    - Command palette
    - Global search
  - Modules:
    - Overview dashboard
    - Products
    - AI Studio
    - Image Studio
    - Social Publishing
    - Analytics
    - Calendar (drag/drop)
    - File management
    - Settings
    - User management
    - System / realtime status

  ## Routing

  - Public:
    - `/login`
  - Protected:
    - `/dashboard`
    - `/products`
    - `/ai-studio`
    - `/image-studio`
    - `/publishing`
    - `/analytics`
    - `/calendar`
    - `/files`
    - `/settings`
    - `/users`
    - `/system`

  ## Permissions

  - Authentication is JWT-based via backend `/auth/login`.
  - Protected routes enforce authenticated access.
  - Role-aware route guard support exists in `RequireAuth` (`admin`, `editor`, `viewer`).
  - Session timeout uses activity-based expiration and auto-logout.

  ## API Integration Policy

  - Dashboard consumes existing backend endpoints only.
  - No duplicate backend business logic in frontend.
  - API base URL is configured via `VITE_API_BASE_URL`.

  ## Environment

  Copy `.env.example` to `.env` and adjust values:

  ```bash
  VITE_API_BASE_URL=http://localhost:8000/api/v1
  VITE_WS_URL=ws://localhost:8000/ws
  ```

  ## Commands

  ```bash
  npm install
  npm run dev
  npm run lint
  npm run build
  npm run test
  npm run test:e2e
  ```
