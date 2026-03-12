import { useEffect, useState } from "react";
import { FileCode, Sparkles, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { listTemplates, type TemplateSummary } from "@/services/api";

interface TemplateListProps {
  onSelect: (template: TemplateSummary) => void;
  onBack: () => void;
}

export function TemplateList({ onSelect, onBack }: TemplateListProps) {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTemplates()
      .then(setTemplates)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Loading templates...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-destructive">
        Failed to load templates: {error}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-lg font-semibold">Choose a Template</h2>
      </div>

      <div className="grid gap-3">
        {templates.map((t) => (
          <button
            key={t.name}
            className="flex items-start gap-3 rounded-lg border border-input p-3 text-left transition-colors hover:bg-accent"
            onClick={() => onSelect(t)}
          >
            <FileCode className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{t.name}</span>
                <Badge variant="secondary" className="text-[10px]">{t.category}</Badge>
                {t.llm_enhance && (
                  <Badge variant="outline" className="text-[10px] gap-0.5">
                    <Sparkles className="h-2.5 w-2.5" />
                    AI
                  </Badge>
                )}
              </div>
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{t.description}</p>
            </div>
          </button>
        ))}
      </div>

      {templates.length === 0 && (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No templates found.
        </p>
      )}
    </div>
  );
}
