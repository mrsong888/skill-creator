import { Puzzle } from "lucide-react";
import type { SkillSummary } from "@/services/api";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/utils/cn";

interface SkillCardProps {
  skill: SkillSummary;
  selected?: boolean;
  onClick: () => void;
  onToggle: (enabled: boolean) => void;
}

export function SkillCard({ skill, selected, onClick, onToggle }: SkillCardProps) {
  return (
    <div
      className={cn(
        "cursor-pointer rounded-lg border p-4 transition-colors hover:bg-accent",
        selected && "border-primary bg-accent",
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Puzzle className="h-5 w-5 text-muted-foreground" />
          <h3 className="font-medium">{skill.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={skill.category === "public" ? "secondary" : "outline"}>{skill.category}</Badge>
          <label className="relative inline-flex cursor-pointer items-center" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              className="peer sr-only"
              checked={skill.enabled}
              onChange={(e) => onToggle(e.target.checked)}
            />
            <div className="peer h-5 w-9 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full" />
          </label>
        </div>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{skill.description}</p>
    </div>
  );
}
