import { useEffect, useState } from "react";
import { Brain, RefreshCw } from "lucide-react";
import { type MemoryData, getMemory, reloadMemory } from "@/services/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function MemoryPanel() {
  const [memory, setMemory] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    const data = await getMemory();
    setMemory(data);
    setLoading(false);
  };

  const handleReload = async () => {
    setLoading(true);
    const data = await reloadMemory();
    setMemory(data);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  if (!memory) {
    return <div className="p-4 text-sm text-muted-foreground">Loading memory...</div>;
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          <h1 className="text-xl font-bold">Memory</h1>
        </div>
        <Button variant="outline" size="sm" onClick={handleReload} disabled={loading}>
          <RefreshCw className={`mr-1 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Reload
        </Button>
      </div>

      {/* Context */}
      <div className="mb-6 space-y-3">
        <h2 className="text-sm font-semibold uppercase text-muted-foreground">Context</h2>
        {Object.entries(memory.context).map(([key, val]) => (
          <div key={key} className="rounded-lg border p-3">
            <p className="text-xs font-medium text-muted-foreground">{key}</p>
            <p className="mt-1 text-sm">{val.summary || "(empty)"}</p>
          </div>
        ))}
      </div>

      {/* Facts */}
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase text-muted-foreground">
          Facts ({memory.facts.length})
        </h2>
        {memory.facts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No facts recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {memory.facts.map((fact) => (
              <div key={fact.id} className="flex items-start gap-2 rounded border p-2">
                <Badge variant="outline" className="mt-0.5 shrink-0">
                  {fact.category}
                </Badge>
                <div className="flex-1">
                  <p className="text-sm">{fact.content}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Confidence: {(fact.confidence * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
