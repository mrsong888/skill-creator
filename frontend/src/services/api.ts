function getBaseUrl(): string {
  // 1. Check chrome.storage for user-configured URL
  // 2. Fall back to default
  return localStorage.getItem("backend_url") || "http://localhost:8001";
}

function baseUrl(): string {
  return getBaseUrl();
}

// ---------- Chat ----------

export interface ChatRequest {
  message: string;
  thread_id?: string;
  skill_name?: string;
  page_context?: string;
}

export interface SSEEvent {
  type: string;
  data: Record<string, unknown>;
}

export async function* streamChat(req: ChatRequest): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${baseUrl()}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!response.ok) throw new Error(`Chat failed: ${response.status}`);
  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

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
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: currentEvent, data };
        } catch {
          // skip malformed JSON
        }
        currentEvent = "";
      }
    }
  }
}

export interface ThreadSummary {
  id: string;
  title: string | null;
  skill_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export async function getChatHistory(): Promise<ThreadSummary[]> {
  const res = await fetch(`${baseUrl()}/api/chat/history`);
  return res.json();
}

export async function getThreadMessages(threadId: string): Promise<Message[]> {
  const res = await fetch(`${baseUrl()}/api/chat/${threadId}`);
  return res.json();
}

// ---------- Skills ----------

export interface SkillSummary {
  name: string;
  description: string;
  category: string;
  enabled: boolean;
}

export interface SkillDetail extends SkillSummary {
  license: string;
  allowed_tools: string[];
  content: string;
}

export async function listSkills(): Promise<SkillSummary[]> {
  const res = await fetch(`${baseUrl()}/api/skills`);
  return res.json();
}

export async function getSkill(name: string): Promise<SkillDetail> {
  const res = await fetch(`${baseUrl()}/api/skills/${name}`);
  return res.json();
}

export async function updateSkillEnabled(name: string, enabled: boolean): Promise<void> {
  await fetch(`${baseUrl()}/api/skills/${name}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

export async function deleteSkill(name: string): Promise<void> {
  await fetch(`${baseUrl()}/api/skills/${name}`, { method: "DELETE" });
}

export async function getSkillFiles(name: string): Promise<Record<string, string>> {
  const res = await fetch(`${baseUrl()}/api/skills/${name}/files`);
  if (!res.ok) throw new Error(`Failed to fetch skill files: ${res.statusText}`);
  const json = await res.json();
  return json.files;
}

export async function* streamSkillChat(
  skillName: string,
  message: string,
  history: Array<{ role: string; content: string }>,
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${baseUrl()}/api/skills/${skillName}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) throw new Error(`Skill chat failed: ${response.status}`);
  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

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
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: currentEvent, data };
        } catch {
          // skip malformed JSON
        }
        currentEvent = "";
      }
    }
  }
}

// ---------- Memory ----------

export interface MemoryData {
  version: string;
  lastUpdated: string;
  context: Record<string, { summary: string; updatedAt: string }>;
  facts: Array<{
    id: string;
    content: string;
    category: string;
    confidence: number;
    createdAt: string;
    source: string;
  }>;
}

export async function getMemory(): Promise<MemoryData> {
  const res = await fetch(`${baseUrl()}/api/memory`);
  return res.json();
}

export async function reloadMemory(): Promise<MemoryData> {
  const res = await fetch(`${baseUrl()}/api/memory/reload`, { method: "POST" });
  return res.json();
}

export async function updateMemory(data: Partial<MemoryData>): Promise<MemoryData> {
  const res = await fetch(`${baseUrl()}/api/memory`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

// ---------- Workspace ----------

export interface WorkspaceFile {
  name: string;
  path: string;
  size: number;
  category: string;
}

export async function listWorkspaceFiles(threadId: string): Promise<WorkspaceFile[]> {
  const res = await fetch(`${baseUrl()}/api/workspace/${threadId}/files`);
  return res.json();
}

export async function uploadFile(threadId: string, file: File): Promise<{ filename: string; size: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${baseUrl()}/api/workspace/${threadId}/upload`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

// ---------- Skill Templates ----------

export interface TemplateVariable {
  name: string;
  type: "string" | "text" | "list";
  required: boolean;
  default: unknown;
  description: string;
  options: string[];
}

export interface TemplateSummary {
  name: string;
  description: string;
  category: string;
  version: string;
  llm_enhance: boolean;
  variables: TemplateVariable[];
}

export interface RenderResult {
  content: string;
  is_valid: boolean;
  validation_message: string;
}

export interface CreateResult {
  success: boolean;
  skill_name: string;
  message: string;
  content: string;
}

export interface ValidateResult {
  is_valid: boolean;
  message: string;
}

export interface EvaluateResult {
  score: number;
  suggestions: string[];
  details: Record<string, unknown>;
}

export async function listTemplates(): Promise<TemplateSummary[]> {
  const res = await fetch(`${baseUrl()}/api/skill-templates`);
  return res.json();
}

export async function getTemplate(name: string): Promise<TemplateSummary> {
  const res = await fetch(`${baseUrl()}/api/skill-templates/${name}`);
  return res.json();
}

export async function renderTemplate(name: string, variables: Record<string, unknown>): Promise<RenderResult> {
  const res = await fetch(`${baseUrl()}/api/skill-templates/${name}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variables }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Render failed");
  }
  return res.json();
}

export async function* renderTemplateLLM(name: string, variables: Record<string, unknown>): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${baseUrl()}/api/skill-templates/${name}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variables }),
  });

  if (!response.ok) throw new Error(`Render failed: ${response.status}`);
  if (!response.body) throw new Error("No response body");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

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
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: currentEvent, data };
        } catch {
          // skip malformed JSON
        }
        currentEvent = "";
      }
    }
  }
}

export async function createFromTemplate(name: string, variables: Record<string, unknown>, skillName?: string, content?: string): Promise<CreateResult> {
  const res = await fetch(`${baseUrl()}/api/skill-templates/${name}/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variables, skill_name: skillName, content }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Create failed");
  }
  return res.json();
}

export async function validateSkillMd(content: string): Promise<ValidateResult> {
  const res = await fetch(`${baseUrl()}/api/skill-templates/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return res.json();
}

export async function evaluateSkillQuality(content: string): Promise<EvaluateResult> {
  const res = await fetch(`${baseUrl()}/api/skill-templates/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Evaluate failed");
  }
  return res.json();
}
