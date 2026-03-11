import { useState } from "react";
import { Brain, Puzzle, Settings, Wand2 } from "lucide-react";
import { SkillListPanel } from "@/components/SkillList/SkillListPanel";
import { SkillCreator } from "@/components/SkillCreator/SkillCreator";
import { MemoryPanel } from "@/components/MemoryPanel/MemoryPanel";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils/cn";

type Tab = "skills" | "creator" | "memory" | "settings";

const tabs: { id: Tab; label: string; icon: typeof Puzzle }[] = [
  { id: "skills", label: "Skills", icon: Puzzle },
  { id: "creator", label: "Creator", icon: Wand2 },
  { id: "memory", label: "Memory", icon: Brain },
  { id: "settings", label: "Settings", icon: Settings },
];

export function Options() {
  const [activeTab, setActiveTab] = useState<Tab>("skills");

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-48 border-r bg-muted/30">
        <div className="border-b px-4 py-3">
          <h1 className="text-lg font-bold">Agent Skill</h1>
          <p className="text-xs text-muted-foreground">Extension Settings</p>
        </div>
        <div className="space-y-1 p-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? "secondary" : "ghost"}
                className={cn("w-full justify-start")}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tab.label}
              </Button>
            );
          })}
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {activeTab === "skills" && <SkillListPanel />}
        {activeTab === "creator" && <SkillCreator />}
        {activeTab === "memory" && <MemoryPanel />}
        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}

function SettingsPanel() {
  return (
    <div className="p-4">
      <h1 className="mb-4 text-xl font-bold">Settings</h1>
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Backend URL</label>
          <input
            type="text"
            className="w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm"
            defaultValue="http://localhost:8001"
          />
          <p className="mt-1 text-xs text-muted-foreground">The URL of the Agent Skill backend server.</p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Model</label>
          <input
            type="text"
            className="w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm"
            defaultValue="gpt-4o"
          />
          <p className="mt-1 text-xs text-muted-foreground">Default LLM model for chat and skill creation.</p>
        </div>
      </div>
    </div>
  );
}
