"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bot, Send, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { apiPost } from "@/lib/api";
import { getDemoStatus } from "@/lib/demo";
import { canMutate, type AccessContext } from "@/lib/rbac";

type ChatMode = "question" | "procedure" | "regulation" | "incident_explanation" | "recommendation";
type Citation = {
  document_id: string;
  title: string;
  source_uri: string;
  section: string;
  score: number;
};
type ChatResponse = {
  answer: string;
  grounded: boolean;
  citations: Citation[];
  conversation_id: string;
};
type Message = {
  role: "user" | "assistant";
  content: string;
  grounded?: boolean;
  citations?: Citation[];
};

const starterMessages: Message[] = [
  {
    role: "assistant",
    content: "Ask a safety question. I will answer only from indexed documents and show citations.",
    grounded: true,
    citations: []
  }
];

export function AssistantClient({ access }: Readonly<{ access: AccessContext }>) {
  const [mode, setMode] = useState<ChatMode>("question");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>(starterMessages);
  const demoQuery = useQuery({
    queryKey: ["demo-status"],
    queryFn: getDemoStatus,
    refetchInterval: 2_000,
    staleTime: 1_000
  });

  const mutation = useMutation({
    mutationFn: (body: { mode: ChatMode; question: string }) =>
      apiPost<ChatResponse, typeof body & { conversation_id: string; plant_id: string }>("/chat/query", {
        ...body,
        conversation_id: "frontend-command-center",
        plant_id: demoQuery.data?.plant_id ?? "demo-plant"
      }),
    onSuccess: (response) => {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          grounded: response.grounded,
          citations: response.citations
        }
      ]);
    },
    onError: () => {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: [
            "I do not have information on that in the indexed safety corpus.",
            "No operational recommendation can be made without a cited source."
          ].join(" "),
          grounded: false,
          citations: []
        }
      ]);
    }
  });

  function submit() {
    const trimmed = question.trim();
    if (!trimmed) {
      return;
    }
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setQuestion("");
    mutation.mutate({ mode, question: trimmed });
  }

  return (
    <div className="grid min-h-[680px] gap-4 xl:grid-cols-[1fr_320px]">
      <section className="flex min-h-0 flex-col rounded-md border border-border bg-card">
        <div className="border-b border-border px-5 py-4">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <Bot className="h-4 w-4 text-informational" />
            AI Safety Assistant
          </h2>
          <p className="text-sm text-muted-foreground">Retrieval-only answers with visible citations.</p>
        </div>
        <div className="min-h-0 flex-1 space-y-4 overflow-auto p-5">
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={message.role === "user" ? "ml-auto max-w-3xl" : "mr-auto max-w-4xl"}
            >
              <div
                className={
                  message.role === "user"
                    ? "rounded-md border border-primary/40 bg-primary/10 p-4"
                    : "rounded-md border border-border bg-background p-4"
                }
              >
                {message.role === "assistant" && (
                  <div className="mb-3 flex items-center gap-2 text-sm">
                    {message.grounded ? (
                      <>
                        <ShieldCheck className="h-4 w-4 text-safe" />
                        <span className="text-safe">Grounded response</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="h-4 w-4 text-warning" />
                        <span className="text-warning">No relevant source found</span>
                      </>
                    )}
                  </div>
                )}
                <p className="text-sm leading-6">{message.content}</p>
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-4 grid gap-2">
                    {message.citations.map((citation) => (
                      <a
                        key={`${citation.document_id}-${citation.section}`}
                        href={citation.source_uri}
                        className="rounded-md border border-border px-3 py-2 text-xs hover:bg-card"
                      >
                        <span className="block text-foreground">
                          {citation.title} | {citation.section}
                        </span>
                        <span className="text-muted-foreground">
                          confidence {citation.score.toFixed(2)} | {citation.document_id}
                        </span>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
        <div className="border-t border-border p-4">
          <div className="flex gap-3">
            <select
              value={mode}
              onChange={(event) => setMode(event.target.value as ChatMode)}
              className="h-11 rounded-md border border-border bg-background px-3 text-sm"
            >
              <option value="question">Question</option>
              <option value="procedure">Procedure</option>
              <option value="regulation">Regulation</option>
              <option value="incident_explanation">Incident Explanation</option>
              <option value="recommendation">Recommendation</option>
            </select>
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  submit();
                }
              }}
              disabled={!canMutate(access)}
              placeholder={canMutate(access) ? "Ask using indexed safety documents" : "Read-only role"}
              className="h-11 flex-1 rounded-md border border-border bg-background px-3 text-sm"
            />
            <Button onClick={submit} disabled={!canMutate(access) || mutation.isPending}>
              <Send className="mr-2 h-4 w-4" />
              Send
            </Button>
          </div>
        </div>
      </section>

      <aside className="rounded-md border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Grounding Rules</h2>
        <div className="mt-4 space-y-3 text-sm text-muted-foreground">
          <p>Every answer must show document and section citations.</p>
          <p>Low-confidence retrieval is rendered as a distinct no-source response.</p>
          <p>Viewer and Compliance Officer roles are read-only in this interface.</p>
        </div>
      </aside>
    </div>
  );
}
