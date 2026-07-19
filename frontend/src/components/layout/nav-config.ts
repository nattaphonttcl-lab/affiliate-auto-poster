import {
  BarChart3,
  Bot,
  CalendarDays,
  Database,
  FileImage,
  Files,
  LayoutDashboard,
  Package,
  Send,
  Settings,
  Users,
} from "lucide-react";

export const NAV_ITEMS = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { to: "/products", label: "Products", icon: Package },
  { to: "/ai-studio", label: "AI Studio", icon: Bot },
  { to: "/image-studio", label: "Image Studio", icon: FileImage },
  { to: "/publishing", label: "Publishing", icon: Send },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/files", label: "File Management", icon: Files },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/users", label: "Users", icon: Users },
  { to: "/system", label: "System", icon: Database },
];
