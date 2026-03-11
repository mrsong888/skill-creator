import { useState } from "react";
import { Globe, MessageSquare, Puzzle, Settings } from "lucide-react";
import { ChatPanel } from "@/components/Chat/ChatPanel";
import { ThreadList } from "@/components/Chat/ThreadList";
import { useChatStore } from "@/stores/chatStore";
import { useSkillStore } from "@/stores/skillStore";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils/cn";

type View = "chat" | "threads";

export function SidePanel() {
  const [view, setView] = useState<View>("chat");
  const [showSkillPicker, setShowSkillPicker] = useState(false);
  const { boundSkill, setBoundSkill, setPageContext } = useChatStore();
  const { skills, loadSkills } = useSkillStore();

  const capturePageContext = async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id) {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            const title = document.title;
            const text = document.body.innerText.slice(0, 4000);
            return `Title: ${title}\n\nContent:\n${text}`;
          },
        });
        if (results?.[0]?.result) {
          setPageContext(results[0].result);
        }
      }
    } catch (err) {
      console.error("Failed to capture page:", err);
    }
  };

  const handleSkillPicker = async () => {
    if (!showSkillPicker) {
      await loadSkills();
    }
    setShowSkillPicker(!showSkillPicker);
  };

  return (
    <div className="flex h-screen flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-center gap-1">
          <Button
            variant={view === "chat" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setView("chat")}
          >
            <MessageSquare className="mr-1 h-4 w-4" />
            Chat
          </Button>
          <Button
            variant={view === "threads" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setView("threads")}
          >
            Threads
          </Button>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={capturePageContext} title="Capture page content">
            <Globe className="h-4 w-4" />
          </Button>
          <Button
            variant={boundSkill ? "secondary" : "ghost"}
            size="icon"
            onClick={handleSkillPicker}
            title={boundSkill ? `Skill: ${boundSkill}` : "Bind skill"}
          >
            <Puzzle className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => chrome.runtime.openOptionsPage()}
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Skill picker dropdown */}
      {showSkillPicker && (
        <div className="border-b bg-muted p-2">
          <p className="mb-1 text-xs font-medium text-muted-foreground">Bind a skill to this conversation:</p>
          <div className="space-y-1">
            <button
              className={cn("w-full rounded px-2 py-1 text-left text-sm hover:bg-accent", !boundSkill && "bg-accent")}
              onClick={() => {
                setBoundSkill(null);
                setShowSkillPicker(false);
              }}
            >
              None
            </button>
            {skills
              .filter((s) => s.enabled)
              .map((s) => (
                <button
                  key={s.name}
                  className={cn(
                    "w-full rounded px-2 py-1 text-left text-sm hover:bg-accent",
                    boundSkill === s.name && "bg-accent",
                  )}
                  onClick={() => {
                    setBoundSkill(s.name);
                    setShowSkillPicker(false);
                  }}
                >
                  {s.name}
                  <span className="ml-2 text-xs text-muted-foreground">{s.description}</span>
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        {view === "chat" ? <ChatPanel /> : <ThreadList />}
      </div>
    </div>
  );
}
