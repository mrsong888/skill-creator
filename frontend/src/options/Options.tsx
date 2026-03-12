import { useState } from "react";
import { Puzzle, Wand2 } from "lucide-react";
import { SkillListPanel } from "@/components/SkillList/SkillListPanel";
import { SkillCreator } from "@/components/SkillCreator/SkillCreator";
import { Button } from "@/components/ui/Button";
import { cn } from "@/utils/cn";

type Tab = "skills" | "creator";

const tabs: { id: Tab; label: string; icon: typeof Puzzle }[] = [
  { id: "skills", label: "Skills", icon: Puzzle },
  { id: "creator", label: "Creator", icon: Wand2 },
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
      </main>
    </div>
  );
}
