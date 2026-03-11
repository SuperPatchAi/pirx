"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Send,
  Loader2,
  MessageCircle,
  Sparkles,
  BarChart3,
  Activity,
  Zap,
  Heart,
  TrendingUp,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  toolCalls?: { tool: string; args: Record<string, unknown> }[];
}

const SUGGESTION_CHIPS = [
  { label: "How is my projection trending?", icon: TrendingUp },
  { label: "Explain my Aerobic Base", icon: Activity },
  { label: "Am I ready to race?", icon: Zap },
  { label: "Compare last 2 weeks", icon: BarChart3 },
  { label: "What are my drivers doing?", icon: Sparkles },
  { label: "How is my sleep affecting readiness?", icon: Heart },
];

const THREAD_KEY_PREFIX = "pirx_chat_thread_id";

export default function ChatPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const threadKey = `${THREAD_KEY_PREFIX}_${user?.id}`;

  useEffect(() => {
    const stored = localStorage.getItem(threadKey);
    if (stored) setThreadId(stored);
    else setHistoryLoaded(true);
  }, [threadKey]);

  useEffect(() => {
    if (threadId) {
      localStorage.setItem(threadKey, threadId);
    }
  }, [threadId, threadKey]);

  const handleNewChat = useCallback(() => {
    localStorage.removeItem(threadKey);
    setThreadId(null);
    setMessages([]);
    setHistoryLoaded(true);
  }, [threadKey]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (!threadId || historyLoaded) return;
    let cancelled = false;
    async function loadHistory() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const data = await apiFetch(`/chat/history?thread_id=${threadId}`);
        if (!cancelled && data.messages && data.messages.length > 0) {
          setMessages(
            data.messages.map(
              (m: {
                role: string;
                content: string;
                timestamp: string;
                tool_calls?: unknown[];
              }) => ({
                id: crypto.randomUUID(),
                role: m.role as "user" | "assistant",
                content: m.content,
                timestamp: m.timestamp,
                toolCalls: m.tool_calls as
                  | { tool: string; args: Record<string, unknown> }[]
                  | undefined,
              })
            )
          );
        }
      } catch {
        /* history load failure is non-critical */
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    }
    loadHistory();
    return () => { cancelled = true; };
  }, [threadId, historyLoaded]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setIsLoading(true);

      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date().toISOString(),
        },
      ]);

      try {
        const { createClient } = await import("@/lib/supabase/client");
        const { API_URL } = await import("@/lib/api");
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const token = session?.access_token;

        const response = await fetch(`${API_URL}/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: text.trim(),
            thread_id: threadId,
          }),
        });

        if (!response.ok) {
          const errMsg =
            response.status === 401
              ? "Session expired. Please log out and log back in."
              : `Server error (${response.status}). Please try again later.`;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: errMsg } : m
            )
          );
          setIsLoading(false);
          return;
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let sseBuffer = "";

        while (reader) {
          const { done, value } = await reader.read();
          if (done) break;

          sseBuffer += decoder.decode(value, { stream: true });
          const lines = sseBuffer.split("\n");
          sseBuffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const data = JSON.parse(line.slice(6));
              if (data.done) {
                if (!threadId && data.thread_id) setThreadId(data.thread_id);
                break;
              }
              if (data.delta) {
                fullText += data.delta;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: fullText } : m
                  )
                );
              }
              if (data.thread_id && !threadId) setThreadId(data.thread_id);
              if (data.error) {
                fullText = "Something went wrong. Please try again.";
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: fullText } : m
                  )
                );
              }
            } catch {
              /* skip malformed SSE lines */
            }
          }
        }

        if (!fullText) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: "No response received. Please try again." }
                : m
            )
          );
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    "Unable to connect to the server. Please check that the backend is running.",
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, threadId]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100dvh-80px)] -my-6 -mx-4">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <Link href="/dashboard">
          <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Go back">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex items-center gap-2 flex-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <p className="text-sm font-semibold">PIRX</p>
            <p className="text-[10px] text-muted-foreground">
              Performance Intelligence
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={handleNewChat}
          title="New Chat"
          aria-label="New conversation"
        >
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full space-y-6">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <MessageCircle className="h-8 w-8 text-primary" />
            </div>
            <div className="text-center space-y-2">
              <h2 className="text-lg font-semibold">Ask PIRX anything</h2>
              <p className="text-sm text-muted-foreground max-w-[280px]">
                I observe and explain your running performance data. Ask about
                projections, drivers, readiness, or training patterns.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center max-w-sm">
              {SUGGESTION_CHIPS.map((chip) => {
                const Icon = chip.icon;
                return (
                  <button
                    key={chip.label}
                    onClick={() => sendMessage(chip.label)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border bg-card hover:bg-accent transition-colors"
                  >
                    <Icon className="h-3 w-3 text-muted-foreground" />
                    {chip.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-muted-foreground/20">
                    <p className="text-[10px] text-muted-foreground">
                      Analyzed: {msg.toolCalls.map((tc) => tc.tool).join(", ")}
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading &&
          messages.length > 0 &&
          messages[messages.length - 1].role === "assistant" &&
          !messages[messages.length - 1].content && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-muted rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">...</span>
                </div>
              </div>
            </motion.div>
          )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t bg-background px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your performance..."
            rows={1}
            className="flex-1 resize-none rounded-xl border bg-muted px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 max-h-32"
            style={{ minHeight: "40px" }}
          />
          <Button
            size="icon"
            className="h-10 w-10 rounded-xl shrink-0"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
