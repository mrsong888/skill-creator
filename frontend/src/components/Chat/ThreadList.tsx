import { useEffect } from "react";
import { MessageSquarePlus } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils/cn";

export function ThreadList() {
  const { threads, currentThreadId, loadThreads, selectThread, newThread } = useChatStore();

  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  return (
    <div className="flex h-full flex-col border-r">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <h2 className="text-sm font-semibold">Chats</h2>
        <Button variant="ghost" size="icon" onClick={newThread} title="New chat">
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {threads.map((t) => (
          <button
            key={t.id}
            className={cn(
              "w-full px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
              currentThreadId === t.id && "bg-accent",
            )}
            onClick={() => selectThread(t.id)}
          >
            <p className="truncate font-medium">{t.title || "Untitled"}</p>
            {t.skill_name && <p className="truncate text-xs text-muted-foreground">Skill: {t.skill_name}</p>}
          </button>
        ))}
      </div>
    </div>
  );
}
