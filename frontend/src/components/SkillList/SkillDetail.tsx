import { Trash2, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { SkillDetail as SkillDetailType } from "@/services/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface SkillDetailProps {
  skill: SkillDetailType;
  onClose: () => void;
  onDelete: () => void;
}

export function SkillDetail({ skill, onClose, onDelete }: SkillDetailProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-lg font-semibold">{skill.name}</h2>
        <div className="flex gap-2">
          {skill.category === "custom" && (
            <Button variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="mr-1 h-4 w-4" />
              Delete
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4 flex flex-wrap gap-2">
          <Badge variant="secondary">{skill.category}</Badge>
          {skill.license && <Badge variant="outline">{skill.license}</Badge>}
          {skill.allowed_tools.map((t) => (
            <Badge key={t} variant="outline">
              {t}
            </Badge>
          ))}
        </div>
        <p className="mb-4 text-sm text-muted-foreground">{skill.description}</p>
        <div className="prose prose-sm max-w-none rounded-lg bg-muted p-4">
          <ReactMarkdown>{skill.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
