import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";

function ThinkingIndicator() {
  return (
    <div className="flex gap-3 px-4 py-3 justify-start">
      <div className="max-w-[85%] rounded-lg px-4 py-3 bg-muted text-foreground">
        <div className="flex items-center gap-1.5">
          <div className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "0ms" }} />
          <div className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "150ms" }} />
          <div className="h-2 w-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}

export function ChatPanel() {
  const { messages, streamingContent, isStreaming, sendMessage } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, isStreaming]);

  const showThinking = isStreaming && !streamingContent;

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !isStreaming && (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p className="text-sm">Start a conversation...</p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatMessage key={msg.id} role={msg.role as "user" | "assistant"} content={msg.content} />
        ))}
        {showThinking && <ThinkingIndicator />}
        {streamingContent && <ChatMessage role="assistant" content={streamingContent} isStreaming />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
