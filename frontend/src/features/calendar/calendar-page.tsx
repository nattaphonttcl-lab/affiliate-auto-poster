import { useMemo, useState } from "react";
import { useDrag, useDrop } from "react-dnd";

import { Card } from "../../components/ui/card";

type Mode = "month" | "week" | "day";

type Task = {
  id: string;
  title: string;
  date: string;
};

type DragItem = {
  id: string;
  type: "task";
};

function TaskChip({ task }: { task: Task }) {
  const [{ isDragging }, dragRef] = useDrag(
    () => ({
      type: "task",
      item: { id: task.id, type: "task" } satisfies DragItem,
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    }),
    [task.id],
  );

  return (
    <div
      ref={(node) => {
        dragRef(node);
      }}
      className="cursor-move rounded bg-indigo-100 px-2 py-1 text-xs text-indigo-800"
      style={{ opacity: isDragging ? 0.5 : 1 }}
    >
      {task.title}
    </div>
  );
}

function DayCell({
  date,
  tasks,
  onDropTask,
}: {
  date: string;
  tasks: Task[];
  onDropTask: (taskId: string, targetDate: string) => void;
}) {
  const [, dropRef] = useDrop(
    () => ({
      accept: "task",
      drop: (item: DragItem) => {
        onDropTask(item.id, date);
      },
    }),
    [date, onDropTask],
  );

  return (
    <div
      ref={(node) => {
        dropRef(node);
      }}
      className="min-h-32 rounded-lg border border-slate-200 p-2"
    >
      <p className="mb-2 text-xs font-semibold text-slate-500">{date}</p>
      <div className="space-y-1">
        {tasks.map((task) => (
          <TaskChip key={task.id} task={task} />
        ))}
      </div>
    </div>
  );
}

export function CalendarPage() {
  const [mode, setMode] = useState<Mode>("month");
  const [tasks, setTasks] = useState<Task[]>([
    { id: "1", title: "Shopee Summer Push", date: "Mon" },
    { id: "2", title: "TikTok Bundle", date: "Tue" },
    { id: "3", title: "IG Reel Retarget", date: "Wed" },
  ]);

  const days = useMemo(() => {
    if (mode === "day") {
      return ["Today"];
    }
    if (mode === "week") {
      return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    }
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  }, [mode]);

  return (
    <Card>
      <div className="mb-3 flex gap-2">
        {(["month", "week", "day"] as const).map((item) => (
          <button
            key={item}
            onClick={() => setMode(item)}
            className={`rounded px-3 py-1 text-sm ${
              mode === item ? "bg-indigo-600 text-white" : "bg-slate-100"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="grid gap-2 md:grid-cols-4 lg:grid-cols-7">
        {days.map((day) => (
          <DayCell
            key={day}
            date={day}
            tasks={tasks.filter((task) => task.date === day)}
            onDropTask={(taskId, targetDate) => {
              setTasks((prev) =>
                prev.map((task) =>
                  task.id === taskId ? { ...task, date: targetDate } : task,
                ),
              );
            }}
          />
        ))}
      </div>
    </Card>
  );
}
