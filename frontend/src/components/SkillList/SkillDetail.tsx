import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Trash2, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { type SkillDetail as SkillDetailType, getSkillFiles, streamSkillChat } from "@/services/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ChatInput } from "@/components/Chat/ChatInput";
import { ChatMessage } from "@/components/Chat/ChatMessage";
import { cn } from "@/utils/cn";

interface SkillDetailProps {
  skill: SkillDetailType;
  onClose: () => void;
  onDelete: () => void;
}

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

export function SkillDetail({ skill, onClose, onDelete }: SkillDetailProps) {
  const [showChat, setShowChat] = useState(false);
  const [files, setFiles] = useState<Record<string, string>>({});
  const [activeFile, setActiveFile] = useState("SKILL.md");
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [updatedFiles, setUpdatedFiles] = useState<Set<string>>(new Set());
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Load skill files when entering chat mode
  useEffect(() => {
    if (showChat) {
      getSkillFiles(skill.name)
        .then(setFiles)
        .catch(() => {
          // fallback: just show SKILL.md content
          setFiles({ "SKILL.md": skill.content });
        });
    }
  }, [showChat, skill.name, skill.content]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const fileNames = Object.keys(files).sort((a, b) => {
    if (a === "SKILL.md") return -1;
    if (b === "SKILL.md") return 1;
    return a.localeCompare(b);
  });

  const handleSend = useCallback(
    async (message: string) => {
      if (streaming) return;

      setStreaming(true);
      setUpdatedFiles(new Set());

      const newMessages: ChatMsg[] = [...chatMessages, { role: "user", content: message }];
      setChatMessages(newMessages);

      let assistantContent = "";
      setChatMessages([...newMessages, { role: "assistant", content: "" }]);

      try {
        const history = chatMessages.map((m) => ({ role: m.role, content: m.content }));

        for await (const event of streamSkillChat(skill.name, message, history)) {
          if (event.type === "content_delta" && event.data.delta) {
            assistantContent += event.data.delta as string;
            setChatMessages([...newMessages, { role: "assistant", content: assistantContent }]);
          } else if (event.type === "file_updated" && event.data.path) {
            const filePath = event.data.path as string;
            const fileContent = event.data.content as string;
            setFiles((prev) => ({ ...prev, [filePath]: fileContent }));
            setUpdatedFiles((prev) => new Set(prev).add(filePath));
            setActiveFile(filePath);
          } else if (event.type === "error" && event.data.message) {
            assistantContent += `\n\n**Error:** ${event.data.message}`;
            setChatMessages([...newMessages, { role: "assistant", content: assistantContent }]);
          }
        }
      } catch (error) {
        assistantContent += `\n\n**Error:** ${error instanceof Error ? error.message : "Unknown error"}`;
        setChatMessages([...newMessages, { role: "assistant", content: assistantContent }]);
      } finally {
        setStreaming(false);
      }
    },
    [streaming, chatMessages, skill.name],
  );

  // Chat editing mode
  if (showChat) {
    return (
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setShowChat(false)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-lg font-semibold">{skill.name}</h2>
            <Badge variant="secondary">Edit Mode</Badge>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Main content: files + chat */}
        <div className="flex min-h-0 flex-1">
          {/* File viewer */}
          <div className="flex min-h-0 flex-1 flex-col border-r">
            {/* File tabs */}
            <div className="flex gap-1 overflow-x-auto border-b bg-muted/30 px-2 py-1">
              {fileNames.map((name) => (
                <button
                  key={name}
                  className={cn(
                    "whitespace-nowrap rounded px-3 py-1.5 text-xs transition-colors",
                    activeFile === name ? "bg-background font-medium shadow-sm" : "text-muted-foreground hover:text-foreground",
                    updatedFiles.has(name) && "text-green-600",
                  )}
                  onClick={() => setActiveFile(name)}
                >
                  {name.split("/").pop()}
                  {updatedFiles.has(name) && <span className="ml-1 text-[10px]">●</span>}
                </button>
              ))}
            </div>
            {/* File content */}
            <div className="flex-1 overflow-y-auto p-4">
              <pre className="whitespace-pre-wrap text-sm leading-relaxed">{files[activeFile] ?? ""}</pre>
            </div>
          </div>

          {/* Chat panel */}
          <div className="flex w-80 flex-shrink-0 flex-col">
            <div className="border-b px-3 py-2">
              <h4 className="text-xs font-medium text-muted-foreground">Chat with AI to edit this skill</h4>
            </div>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
              {chatMessages.length === 0 ? (
                <div className="flex h-full items-center justify-center p-4">
                  <p className="text-center text-sm text-muted-foreground">
                    Describe the changes you want to make to this skill.
                  </p>
                </div>
              ) : (
                <>
                  {chatMessages.map((msg, i) => (
                    <ChatMessage key={i} role={msg.role} content={msg.content} isStreaming={streaming && i === chatMessages.length - 1 && msg.role === "assistant"} />
                  ))}
                  <div ref={chatEndRef} />
                </>
              )}
            </div>
            {/* Input */}
            <ChatInput onSend={handleSend} disabled={streaming} />
          </div>
        </div>
      </div>
    );
  }

  // Normal detail view
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-lg font-semibold">{skill.name}</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowChat(true)}>
            Edit
          </Button>
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
