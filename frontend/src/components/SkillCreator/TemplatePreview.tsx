import { useEffect, useState } from "react";
import { ArrowLeft, CheckCircle, XCircle, Sparkles, Save, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  renderTemplate,
  renderTemplateLLM,
  createFromTemplate,
  evaluateSkillQuality,
  validateSkillMd,
  type TemplateSummary,
  type ValidateResult,
  type EvaluateResult,
} from "@/services/api";

interface TemplatePreviewProps {
  template: TemplateSummary;
  variables: Record<string, unknown>;
  onBack: () => void;
  onCreated: (skillName: string) => void;
}

export function TemplatePreview({ template, variables, onBack, onCreated }: TemplatePreviewProps) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluateResult | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function doRender() {
      try {
        if (template.llm_enhance) {
          setStreaming(true);
          let accumulated = "";
          for await (const event of renderTemplateLLM(template.name, variables)) {
            if (cancelled) break;
            if (event.type === "start") {
              // Frontmatter emitted at start
              const data = event.data as Record<string, string>;
              accumulated = data.content || "";
              setContent(accumulated);
              setLoading(false);
            } else if (event.type === "chunk") {
              const data = event.data as Record<string, string>;
              accumulated += data.content || "";
              setContent(accumulated);
              setLoading(false);
            } else if (event.type === "complete") {
              const data = event.data as Record<string, unknown>;
              const finalContent = data.content as string;
              setContent(finalContent);
              // Validate the final content
              try {
                const v = await validateSkillMd(finalContent);
                if (!cancelled) setValidation(v);
              } catch {
                // validation API failed, skip
              }
            } else if (event.type === "fallback") {
              const data = event.data as Record<string, unknown>;
              const fallbackContent = data.content as string;
              setContent(fallbackContent);
              try {
                const v = await validateSkillMd(fallbackContent);
                if (!cancelled) setValidation(v);
              } catch {
                // skip
              }
            }
          }
          setStreaming(false);
        } else {
          const result = await renderTemplate(template.name, variables);
          if (cancelled) return;
          setContent(result.content);
          setValidation({
            is_valid: result.is_valid,
            message: result.validation_message,
          });
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    doRender();
    return () => { cancelled = true; };
  }, [template, variables]);

  const handleEvaluate = async () => {
    if (!content) return;
    setEvaluating(true);
    try {
      const result = await evaluateSkillQuality(content);
      setEvaluation(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const result = await createFromTemplate(template.name, variables);
      onCreated(result.skill_name);
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading && !content) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        {template.llm_enhance ? "Generating with AI..." : "Rendering..."}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="mb-4">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <p className="text-sm text-destructive">Error: {error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-lg font-semibold">Preview</h2>
        {streaming && (
          <Badge variant="outline" className="gap-1 text-[10px]">
            <Loader2 className="h-2.5 w-2.5 animate-spin" />
            Streaming
          </Badge>
        )}
      </div>

      {/* Validation status */}
      {validation && (
        <div className={`mb-3 flex items-center gap-2 rounded-lg border p-2 text-sm ${validation.is_valid ? "border-green-500/30 bg-green-500/5 text-green-700 dark:text-green-400" : "border-destructive/30 bg-destructive/5 text-destructive"}`}>
          {validation.is_valid ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 shrink-0" />
          )}
          <span>{validation.message}</span>
        </div>
      )}

      {/* Content preview */}
      <div className="rounded-lg border border-input bg-muted/30 p-3 mb-4 max-h-[50vh] overflow-y-auto">
        <div className="prose prose-sm max-w-none text-sm">
          <ReactMarkdown>{content}</ReactMarkdown>
          {streaming && (
            <span className="inline-block w-0.5 h-4 bg-foreground/70 animate-pulse ml-0.5 align-text-bottom" />
          )}
        </div>
      </div>

      {/* Evaluation */}
      {evaluation && (
        <div className="mb-4 rounded-lg border border-input p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Sparkles className="h-4 w-4" />
            Quality Score: {evaluation.score}/10
          </div>
          {evaluation.suggestions.length > 0 && (
            <ul className="space-y-1 text-xs text-muted-foreground">
              {evaluation.suggestions.map((s, i) => (
                <li key={i}>- {s}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {!evaluation && (
          <Button variant="outline" onClick={handleEvaluate} disabled={evaluating || streaming || !content}>
            {evaluating ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Sparkles className="mr-1 h-4 w-4" />}
            Evaluate
          </Button>
        )}
        <Button
          className="flex-1"
          onClick={handleSave}
          disabled={saving || streaming || (validation != null && !validation.is_valid)}
        >
          {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
          Save Skill
        </Button>
      </div>

      {saveError && (
        <p className="mt-2 text-xs text-destructive">{saveError}</p>
      )}
    </div>
  );
}
