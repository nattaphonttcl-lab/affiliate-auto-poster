import { useQuery } from "@tanstack/react-query";

import { getSocialAccounts } from "../../lib/api";
import { Card } from "../../components/ui/card";

export function SettingsPage() {
  const socialAccounts = useQuery({ queryKey: ["social-accounts"], queryFn: getSocialAccounts });

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-3 text-sm font-semibold">Provider & Worker Settings</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
            <p className="font-medium">AI Providers</p>
            <p className="text-sm text-slate-500">Configured via backend secure provider configs.</p>
          </div>
          <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
            <p className="font-medium">Scheduler & Rate Limits</p>
            <p className="text-sm text-slate-500">Managed by server-side policy and env settings.</p>
          </div>
          <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
            <p className="font-medium">Feature Flags</p>
            <p className="text-sm text-slate-500">Frontend-safe toggles are loaded from build env.</p>
          </div>
          <div className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
            <p className="font-medium">Storage</p>
            <p className="text-sm text-slate-500">Uses existing image/storage backend APIs only.</p>
          </div>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-semibold">Social Accounts</h2>
        <div className="space-y-2">
          {(socialAccounts.data ?? []).map((account) => (
            <div key={account.id} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
              <p className="font-medium">{account.account_name}</p>
              <p className="text-sm text-slate-500">{account.platform} · {account.account_identifier}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
