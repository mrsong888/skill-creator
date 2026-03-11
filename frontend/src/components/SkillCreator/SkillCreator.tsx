import { useState } from "react";
import { Wand2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/Button";

interface CreatorMessage {
  role: "user" | "assistant";
  content: string;
}

export function SkillCreator() {
  const [messages, setMessages] = useState<CreatorMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMsg: CreatorMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

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
    }
  };

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4 flex items-center gap-2">
        <Wand2 className="h-5 w-5" />
        <h1 className="text-xl font-bold">Skill Creator</h1>
      </div>

      <p className="mb-4 text-sm text-muted-foreground">
        Describe what you want your skill to do. The assistant will help you create a SKILL.md file.
      </p>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`rounded-lg p-3 text-sm ${msg.role === "user" ? "bg-primary text-primary-foreground ml-8" : "bg-muted mr-8"}`}>
            {msg.role === "user" ? (
              <p className="whitespace-pre-wrap">{msg.content}</p>
            ) : (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input */}
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
    </div>
  );
}
