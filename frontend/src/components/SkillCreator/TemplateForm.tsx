import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { TemplateSummary, TemplateVariable } from "@/services/api";

interface TemplateFormProps {
  template: TemplateSummary;
  onSubmit: (variables: Record<string, unknown>) => void;
  onBack: () => void;
}

function defaultValueFor(v: TemplateVariable): string {
  if (v.default != null) {
    if (Array.isArray(v.default)) return v.default.join("\n");
    return String(v.default);
  }
  return "";
}

export function TemplateForm({ template, onSubmit, onBack }: TemplateFormProps) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const v of template.variables) {
      init[v.name] = defaultValueFor(v);
    }
    return init;
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => {
      const copy = { ...prev };
      delete copy[name];
      return copy;
    });
  };

  const handleSubmit = () => {
    const newErrors: Record<string, string> = {};
    for (const v of template.variables) {
      if (v.required && !values[v.name]?.trim()) {
        newErrors[v.name] = "Required";
      }
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Convert list-type variables to arrays
    const result: Record<string, unknown> = {};
    for (const v of template.variables) {
      const val = values[v.name];
      if (v.type === "list" && val) {
        result[v.name] = val.split("\n").map((s) => s.trim()).filter(Boolean);
      } else {
        result[v.name] = val;
      }
    }
    onSubmit(result);
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h2 className="text-lg font-semibold">{template.name}</h2>
          <p className="text-xs text-muted-foreground">{template.description}</p>
        </div>
      </div>

      <div className="space-y-4">
        {template.variables.map((v) => (
          <div key={v.name}>
            <label className="mb-1 block text-sm font-medium">
              {v.description}
              {v.required && <span className="ml-1 text-destructive">*</span>}
            </label>

            {v.options.length > 0 ? (
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={values[v.name]}
                onChange={(e) => handleChange(v.name, e.target.value)}
              >
                {v.options.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : v.type === "text" || v.type === "list" ? (
              <textarea
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                rows={3}
                placeholder={v.type === "list" ? "One item per line" : ""}
                value={values[v.name]}
                onChange={(e) => handleChange(v.name, e.target.value)}
              />
            ) : (
              <Input
                value={values[v.name]}
                onChange={(e) => handleChange(v.name, e.target.value)}
                placeholder={v.description}
              />
            )}

            {errors[v.name] && (
              <p className="mt-1 text-xs text-destructive">{errors[v.name]}</p>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6">
        <Button className="w-full" onClick={handleSubmit}>
          Preview
        </Button>
      </div>
    </div>
  );
}
