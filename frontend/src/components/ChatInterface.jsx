import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  Bot,
  User,
  Wrench,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Plus,
  Clock,
  Shield,
  Layers,
  ArrowRight,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { sendAgentChat, getAgentSessions } from "../api/client";
import ApprovalCard from "./ApprovalCard";

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sessionId, setSessionId] = useState(() => `sess_${Date.now()}`);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadSessions = async () => {
    try {
      const data = await getAgentSessions();
      setSessions(data || []);
    } catch (e) {
      console.error("Failed to load sessions:", e);
    }
  };

  const selectSession = (sess) => {
    setSessionId(sess.session_id);
    setMessages(sess.messages || []);
  };

  const startNewSession = () => {
    const newId = `sess_${Date.now()}`;
    setSessionId(newId);
    setMessages([]);
  };

  const handleSend = async (textToSend) => {
    const text = textToSend || inputMessage.trim();
    if (!text || loading) return;

    const userMsg = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setLoading(true);

    try {
      const res = await sendAgentChat(text, sessionId);
      const assistantMsg = {
        role: "assistant",
        content: res.response,
        steps: res.steps || [],
        hitl_pending: res.hitl_pending,
        hitl_details: res.hitl_details,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      loadSessions();
    } catch (err) {
      const errorMsg = {
        role: "assistant",
        content: `Error: ${err.response?.data?.error || err.message || "Failed to communicate with agent"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const toggleStepExpand = (msgIdx, stepIdx) => {
    const key = `${msgIdx}_${stepIdx}`;
    setExpandedSteps((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const quickPrompts = [
    {
      label: "Process Sizing Return",
      text: "Process the return for order #ORD-2024-0012 because the shirt was too small.",
    },
    {
      label: "Check Customer Risk",
      text: "Check return history and risk profile for customer victoria.vance@example.com",
    },
    {
      label: "Check Return Eligibility",
      text: "Check if order #ORD-2024-0005 items are eligible for return.",
    },
    {
      label: "Queue Overview",
      text: "List the top pending returns currently awaiting review.",
    },
  ];

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-950 text-slate-100 overflow-hidden">
      {/* Session History Sidebar */}
      <div className="w-72 bg-slate-900/80 border-r border-slate-800/80 flex flex-col hidden md:flex">
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Bot className="w-5 h-5 text-indigo-400" />
            <span className="font-semibold text-sm tracking-wide">Agent Sessions</span>
          </div>
          <button
            onClick={startNewSession}
            className="p-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs flex items-center space-x-1 border border-indigo-500/30 transition-all cursor-pointer"
            title="Start new conversation"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {sessions.length === 0 ? (
            <div className="text-xs text-slate-500 text-center py-8">
              No recent sessions yet.
            </div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => selectSession(s)}
                className={`w-full text-left p-2.5 rounded-xl text-xs transition-all flex flex-col space-y-1 cursor-pointer ${
                  s.session_id === sessionId
                    ? "bg-indigo-600/20 border border-indigo-500/40 text-indigo-200"
                    : "hover:bg-slate-800/60 text-slate-300 border border-transparent"
                }`}
              >
                <div className="font-medium truncate text-slate-200">
                  {s.title || `Session ${s.session_id.slice(-6)}`}
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-500">
                  <span>{new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  {s.hitl_pending && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold">
                      HITL
                    </span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Pane */}
      <div className="flex-1 flex flex-col bg-slate-950">
        {/* Chat Header */}
        <div className="px-6 py-3.5 border-b border-slate-800/80 bg-slate-900/40 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-sm text-slate-100 flex items-center space-x-2">
                <span>ReturnPilot Agent</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  LangGraph Active
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Chaining 8 MCP Tools with HITL Safeguards
              </p>
            </div>
          </div>

          <div className="text-xs text-slate-500 font-mono">
            {sessionId.slice(0, 16)}...
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-xl shadow-indigo-950/50">
                <Sparkles className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-100">
                  ReturnPilot Returns Agent
                </h2>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  Ask me to look up orders, check return policies, evaluate serial returners, recommend exchanges, or process refunds.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                {quickPrompts.map((qp, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(qp.text)}
                    className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 transition-all text-xs group cursor-pointer"
                  >
                    <div className="font-semibold text-slate-200 group-hover:text-indigo-300 flex items-center justify-between">
                      <span>{qp.label}</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-slate-400 text-[11px] mt-1 line-clamp-2">
                      {qp.text}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, msgIdx) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msgIdx}
                  className={`flex ${isUser ? "justify-end" : "justify-start"} space-x-3`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div className={`max-w-2xl space-y-3 ${isUser ? "items-end" : "items-start"}`}>
                    {/* Intermediate Tool Call Steps */}
                    {msg.steps && msg.steps.length > 0 && (
                      <div className="space-y-2 mb-2">
                        <div className="text-[11px] font-semibold text-slate-400 flex items-center space-x-1.5">
                          <Layers className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Agent Execution Steps ({msg.steps.length})</span>
                        </div>
                        {msg.steps.map((step, stepIdx) => {
                          const isExpanded = !!expandedSteps[`${msgIdx}_${stepIdx}`];
                          return (
                            <div
                              key={stepIdx}
                              className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden text-xs"
                            >
                              <button
                                onClick={() => toggleStepExpand(msgIdx, stepIdx)}
                                className="w-full px-3 py-2 flex items-center justify-between hover:bg-slate-800/40 text-left transition-colors cursor-pointer"
                              >
                                <div className="flex items-center space-x-2">
                                  <Wrench className="w-3.5 h-3.5 text-indigo-400" />
                                  <span className="font-mono font-medium text-indigo-300">
                                    {step.tool}
                                  </span>
                                </div>
                                <div className="flex items-center space-x-2 text-slate-400">
                                  <span className="text-[10px] text-slate-500">
                                    {step.result?.hitl_triggered ? "HITL Triggered" : "Completed"}
                                  </span>
                                  {isExpanded ? (
                                    <ChevronDown className="w-3.5 h-3.5" />
                                  ) : (
                                    <ChevronRight className="w-3.5 h-3.5" />
                                  )}
                                </div>
                              </button>

                              {isExpanded && (
                                <div className="p-3 border-t border-slate-800 bg-slate-950/80 font-mono text-[11px] space-y-2">
                                  <div>
                                    <span className="text-slate-500 block">Arguments:</span>
                                    <pre className="text-slate-300 overflow-x-auto p-1.5 bg-slate-900 rounded border border-slate-800">
                                      {JSON.stringify(step.args, null, 2)}
                                    </pre>
                                  </div>
                                  <div>
                                    <span className="text-slate-500 block">Result:</span>
                                    <pre className="text-emerald-400/90 overflow-x-auto p-1.5 bg-slate-900 rounded border border-slate-800">
                                      {JSON.stringify(step.result, null, 2)}
                                    </pre>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Message Bubble */}
                    <div
                      className={`p-4 rounded-2xl text-sm leading-relaxed ${
                        isUser
                          ? "bg-indigo-600 text-white rounded-tr-none shadow-md"
                          : "bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none shadow-lg"
                      }`}
                    >
                      {isUser ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        <div className="space-y-2 [&_p]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:space-y-1 [&_li]:marker:text-indigo-400 [&_strong]:font-semibold [&_strong]:text-slate-100 [&_h1]:text-base [&_h1]:font-bold [&_h2]:text-sm [&_h2]:font-bold [&_code]:bg-slate-800 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-indigo-300 [&_code]:text-xs [&_a]:text-indigo-400 [&_a]:underline">
                          <ReactMarkdown>{msg.content || ""}</ReactMarkdown>
                        </div>
                      )}

                      {/* HITL Card if pending */}
                      {msg.hitl_pending && msg.hitl_details && (
                        <ApprovalCard
                          hitlDetails={msg.hitl_details}
                          sessionId={sessionId}
                          onResolved={() => loadSessions()}
                        />
                      )}
                    </div>
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-300 shrink-0 mt-0.5">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })
          )}

          {loading && (
            <div className="flex items-center space-x-3 text-slate-400 text-xs animate-pulse">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <span>ReturnPilot is thinking, checking policies, and invoking MCP tools...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/60">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center space-x-3 max-w-4xl mx-auto"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="e.g. Process the return for order #ORD-2024-0020 or check customer return risk..."
              disabled={loading}
              className="flex-1 px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm flex items-center space-x-2 transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-40 cursor-pointer"
            >
              <span>Send</span>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
