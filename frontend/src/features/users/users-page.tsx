import { useQuery } from "@tanstack/react-query";

import { getUsers } from "../../lib/api";
import { Card } from "../../components/ui/card";

export function UsersPage() {
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: getUsers });

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold">Users / Roles / Permissions</h2>
      <div className="space-y-2">
        {(usersQuery.data ?? []).map((user) => (
          <div key={user.id} className="rounded-lg bg-slate-100 p-3 dark:bg-slate-800">
            <p className="font-medium">{user.email}</p>
            <p className="text-sm text-slate-500">
              {user.is_active ? "active" : "inactive"} · role: admin (frontend policy)
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
