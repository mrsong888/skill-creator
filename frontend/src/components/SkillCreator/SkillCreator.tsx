import { useEffect, useRef, useState } from "react";
import { Wand2, FileCode, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/Button";
import { TemplateList } from "./TemplateList";
import { TemplateForm } from "./TemplateForm";
import { TemplatePreview } from "./TemplatePreview";
import type { TemplateSummary } from "@/services/api";

type Mode = "choose" | "template-list" | "template-form" | "template-preview" | "chat";

interface CreatorMessage {
  role: "user" | "assistant";
  content: string;
}

function ThinkingIndicator() {
  return (
    <div className="rounded-lg p-3 text-sm bg-muted mr-8">
      <div className="flex items-center gap-1.5">
        <div className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "0ms" }} />
        <div className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "150ms" }} />
        <div className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}

function ChatCreator() {
  const [messages, setMessages] = useState<CreatorMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasContent, setHasContent] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, hasContent]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: CreatorMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);
    setHasContent(false);

    try {
      const backendUrl = localStorage.getItem("backend_url") || "http://localhost:8001";
      const response = await fetch(`${backendUrl}/api/skill-creator/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!response.ok || !response.body) throw new Error("Failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let content = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEvent === "content_delta") {
            try {
              const data = JSON.parse(line.slice(6));
              content += data.delta || "";
              setHasContent(true);
              setMessages((prev) => {
                const copy = [...prev];
                const last = copy[copy.length - 1];
                if (last?.role === "assistant") {
                  copy[copy.length - 1] = { ...last, content };
                } else {
                  copy.push({ role: "assistant", content });
                }
                return copy;
              });
            } catch {
              // skip
            }
            currentEvent = "";
          }
        }
      }
    } catch (err) {
      console.error("Skill creator error:", err);
    } finally {
      setIsStreaming(false);
      setHasContent(false);
    }
  };

  const showThinking = isStreaming && !hasContent;

  return (
    <>
      <p className="mb-4 text-sm text-muted-foreground">
        Describe what you want your skill to do. The assistant will help you create a SKILL.md file.
      </p>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.map((msg, i) => {
          const isLastAssistant = isStreaming && hasContent && msg.role === "assistant" && i === messages.length - 1;
          return (
            <div key={i} className={`rounded-lg p-3 text-sm ${msg.role === "user" ? "bg-primary text-primary-foreground ml-8" : "bg-muted mr-8"}`}>
              {msg.role === "user" ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {isLastAssistant && (
                    <span className="inline-block w-0.5 h-4 bg-foreground/70 animate-pulse ml-0.5 align-text-bottom" />
                  )}
                </div>
              )}
            </div>
          );
        })}
        {showThinking && <ThinkingIndicator />}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <textarea
          className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="Describe your skill..."
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={isStreaming}
        />
        <Button onClick={handleSend} disabled={isStreaming || !input.trim()}>
          <Wand2 className="mr-1 h-4 w-4" />
          Create
        </Button>
      </div>
    </>
  );
}

export function SkillCreator() {
  const [mode, setMode] = useState<Mode>("choose");
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateSummary | null>(null);
  const [variables, setVariables] = useState<Record<string, unknown>>({});
  const [createdSkill, setCreatedSkill] = useState<string | null>(null);

  const handleTemplateSelect = (template: TemplateSummary) => {
    setSelectedTemplate(template);
    setMode("template-form");
  };

  const handleFormSubmit = (vars: Record<string, unknown>) => {
    setVariables(vars);
    setMode("template-preview");
  };

  const handleCreated = (skillName: string) => {
    setCreatedSkill(skillName);
  };

  const resetToChoose = () => {
    setMode("choose");
    setSelectedTemplate(null);
    setVariables({});
    setCreatedSkill(null);
  };

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4 flex items-center gap-2">
        <Wand2 className="h-5 w-5" />
        <h1 className="text-xl font-bold">Skill Creator</h1>
      </div>

      {/* Success message */}
      {createdSkill && (
        <div className="mb-4 rounded-lg border border-green-500/30 bg-green-500/5 p-3 text-sm text-green-700 dark:text-green-400">
          Skill "{createdSkill}" created successfully!
          <Button variant="ghost" size="sm" className="ml-2" onClick={resetToChoose}>
            Create another
          </Button>
        </div>
      )}

      {/* Mode: choose */}
      {mode === "choose" && !createdSkill && (
        <div className="flex-1 flex flex-col items-center justify-center gap-4">
          <p className="text-sm text-muted-foreground mb-2">How would you like to create a skill?</p>
          <div className="grid gap-3 w-full max-w-xs">
            <button
              className="flex items-center gap-3 rounded-lg border border-input p-4 text-left transition-colors hover:bg-accent"
              onClick={() => setMode("template-list")}
            >
              <FileCode className="h-6 w-6 text-muted-foreground" />
              <div>
                <div className="font-medium text-sm">From Template</div>
                <div className="text-xs text-muted-foreground">Pick a template and fill in variables</div>
              </div>
            </button>
            <button
              className="flex items-center gap-3 rounded-lg border border-input p-4 text-left transition-colors hover:bg-accent"
              onClick={() => setMode("chat")}
            >
              <MessageSquare className="h-6 w-6 text-muted-foreground" />
              <div>
                <div className="font-medium text-sm">Custom (Chat)</div>
                <div className="text-xs text-muted-foreground">Describe your skill to the AI assistant</div>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Mode: template-list */}
      {mode === "template-list" && (
        <div className="flex-1 overflow-y-auto">
          <TemplateList onSelect={handleTemplateSelect} onBack={() => setMode("choose")} />
        </div>
      )}

      {/* Mode: template-form */}
      {mode === "template-form" && selectedTemplate && (
        <div className="flex-1 overflow-y-auto">
          <TemplateForm
            template={selectedTemplate}
            onSubmit={handleFormSubmit}
            onBack={() => setMode("template-list")}
          />
        </div>
      )}

      {/* Mode: template-preview */}
      {mode === "template-preview" && selectedTemplate && (
        <div className="flex-1 overflow-y-auto">
          <TemplatePreview
            template={selectedTemplate}
            variables={variables}
            onBack={() => setMode("template-form")}
            onCreated={handleCreated}
          />
        </div>
      )}

      {/* Mode: chat */}
      {mode === "chat" && <ChatCreator />}
    </div>
  );
}
