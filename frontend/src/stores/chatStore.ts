import { create } from "zustand";
import {
  type Message,
  type ThreadSummary,
  getChatHistory,
  getThreadMessages,
  streamChat,
} from "@/services/api";

interface ChatState {
  threads: ThreadSummary[];
  currentThreadId: string | null;
  messages: Message[];
  streamingContent: string;
  isStreaming: boolean;
  boundSkill: string | null;
  pageContext: string | null;

  loadThreads: () => Promise<void>;
  selectThread: (threadId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  newThread: () => void;
  setBoundSkill: (name: string | null) => void;
  setPageContext: (context: string | null) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  threads: [],
  currentThreadId: null,
  messages: [],
  streamingContent: "",
  isStreaming: false,
  boundSkill: null,
  pageContext: null,

  loadThreads: async () => {
    const threads = await getChatHistory();
    set({ threads });
  },

  selectThread: async (threadId: string) => {
    const messages = await getThreadMessages(threadId);
    set({ currentThreadId: threadId, messages });
  },

  newThread: () => {
    set({ currentThreadId: null, messages: [], streamingContent: "" });
  },

  sendMessage: async (content: string) => {
    const { currentThreadId, boundSkill, pageContext, messages } = get();

    // Add user message to local state immediately
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      metadata: null,
      created_at: new Date().toISOString(),
    };
    set({ messages: [...messages, userMsg], isStreaming: true, streamingContent: "" });

    try {
      let fullContent = "";
      let threadId = currentThreadId;

      for await (const event of streamChat({
        message: content,
        thread_id: currentThreadId ?? undefined,
        skill_name: boundSkill ?? undefined,
        page_context: pageContext ?? undefined,
      })) {
        if (event.type === "message_start" && event.data.thread_id) {
          threadId = event.data.thread_id as string;
          set({ currentThreadId: threadId });
        } else if (event.type === "content_delta") {
          fullContent += (event.data.delta as string) || "";
          set({ streamingContent: fullContent });
        }
      }

      // Add assistant message
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: fullContent,
        metadata: null,
        created_at: new Date().toISOString(),
      };
      set((state) => ({
        messages: [...state.messages, assistantMsg],
        streamingContent: "",
        isStreaming: false,
      }));

      // Refresh thread list
      get().loadThreads();
    } catch (error) {
      console.error("Chat error:", error);
      set({ isStreaming: false, streamingContent: "" });
    }
  },

  setBoundSkill: (name) => set({ boundSkill: name }),
  setPageContext: (context) => set({ pageContext: context }),
}));
