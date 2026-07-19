import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";

import { NAV_ITEMS } from "./nav-config";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function CommandPalette({ open, onOpenChange }: Props) {
  const navigate = useNavigate();

  if (!open) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-[10vh]"
      onClick={() => onOpenChange(false)}
    >
      <Command
        className="w-[640px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
        onClick={(event) => event.stopPropagation()}
      >
        <Command.Input
          placeholder="Type a command or jump to module..."
          className="w-full border-b border-slate-200 bg-transparent px-4 py-3 outline-none dark:border-slate-700"
        />
        <Command.List className="max-h-96 overflow-auto p-2">
          <Command.Empty className="p-3 text-sm text-slate-500">
            No result.
          </Command.Empty>
          <Command.Group heading="Navigation">
            {NAV_ITEMS.map((item) => (
              <Command.Item
                key={item.to}
                value={item.label}
                className="cursor-pointer rounded-lg px-3 py-2 text-sm data-[selected=true]:bg-slate-100 dark:data-[selected=true]:bg-slate-800"
                onSelect={() => {
                  navigate(item.to);
                  onOpenChange(false);
                }}
              >
                {item.label}
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}
