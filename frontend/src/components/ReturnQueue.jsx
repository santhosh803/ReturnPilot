import React, { useState, useEffect } from "react";
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  ArrowUpDown,
  ShoppingBag,
  ExternalLink,
} from "lucide-react";
import { getReturns, approveAgentReturn } from "../api/client";

export default function ReturnQueue() {
  const [returns, setReturns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedReturn, setSelectedReturn] = useState(null);

  useEffect(() => {
    fetchReturns();
  }, [statusFilter, searchQuery]);

  const fetchReturns = async () => {
    setLoading(true);
    try {
      const data = await getReturns(statusFilter, searchQuery);
      setReturns(data || []);
    } catch (e) {
      console.error("Failed to fetch returns:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = async (returnId, decision) => {
    try {
      await approveAgentReturn({
        returnId,
        decision,
        reason: `Quick action via Return Queue: ${decision}`,
      });
      fetchReturns();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "pending":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">Pending</span>;
      case "awaiting_approval":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-500/20 text-orange-300 border border-orange-500/30 animate-pulse">Awaiting Approval (HITL)</span>;
      case "approved":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Approved</span>;
      case "rejected":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">Rejected</span>;
      case "exchanged":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">Exchanged</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">{status}</span>;
    }
  };

  const getRiskBadge = (score) => {
    const s = Number(score || 0);
    if (s < 0.3) {
      return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{s.toFixed(2)} Low Risk</span>;
    } else if (s <= 0.7) {
      return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">{s.toFixed(2)} Medium Risk</span>;
    } else {
      return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">{s.toFixed(2)} High Risk</span>;
    }
  };

  const tabs = [
    { label: "All Returns", value: "" },
    { label: "Pending", value: "pending" },
    { label: "Awaiting HITL", value: "awaiting_approval" },
    { label: "Approved", value: "approved" },
    { label: "Rejected", value: "rejected" },
    { label: "Exchanged", value: "exchanged" },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Returns Management Queue</h1>
          <p className="text-xs text-slate-400 mt-1">
            Review, filter, and take action on incoming customer return requests
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by ID, email, order..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.value}
            onClick={() => setStatusFilter(t.value)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              statusFilter === t.value
                ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/40"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Returns List */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 text-sm">
          Loading returns queue...
        </div>
      ) : returns.length === 0 ? (
        <div className="py-16 text-center text-slate-500 bg-slate-900/30 rounded-2xl border border-slate-800/80">
          <ShoppingBag className="w-10 h-10 mx-auto text-slate-600 mb-2" />
          <p className="text-sm font-medium">No returns found matching the current filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {returns.map((ret) => (
            <div
              key={ret.id}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col md:flex-row justify-between gap-4"
            >
              <div className="space-y-2 flex-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-mono font-bold text-sm text-indigo-300">
                    {ret.return_id}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Order #{ret.order_id_code}
                  </span>
                  {getStatusBadge(ret.status)}
                  {getRiskBadge(ret.customer_risk_score)}
                </div>

                <div className="text-xs text-slate-300">
                  <span className="font-medium text-slate-200">{ret.customer_name}</span>{" "}
                  <span className="text-slate-500">({ret.customer_email})</span>
                </div>

                <p className="text-xs text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
                  <strong className="text-slate-300">Reason:</strong> "{ret.reason_text}"
                  {ret.reason_classified && (
                    <span className="ml-2 px-2 py-0.5 rounded text-[10px] bg-slate-800 text-indigo-300 font-mono">
                      classified: {ret.reason_classified}
                    </span>
                  )}
                </p>

                {ret.exchange_recommendation && (
                  <p className="text-[11px] text-emerald-400/90 bg-emerald-950/20 p-2 rounded-lg border border-emerald-500/20">
                    {ret.exchange_recommendation}
                  </p>
                )}
              </div>

              {/* Action column */}
              <div className="flex flex-col justify-between items-end min-w-44 shrink-0 space-y-3">
                <div className="text-right">
                  <div className="text-sm font-bold text-emerald-400">
                    ${Number(ret.refund_amount || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {new Date(ret.created_at).toLocaleDateString()}
                  </div>
                </div>

                {(ret.status === "pending" || ret.status === "awaiting_approval") && (
                  <div className="flex items-center space-x-2 w-full">
                    <button
                      onClick={() => handleQuickAction(ret.return_id, "approved")}
                      className="flex-1 py-1.5 px-3 rounded-lg bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white text-xs font-semibold border border-emerald-500/30 transition-all flex items-center justify-center space-x-1 cursor-pointer"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => handleQuickAction(ret.return_id, "rejected")}
                      className="flex-1 py-1.5 px-3 rounded-lg bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white text-xs font-semibold border border-rose-500/30 transition-all flex items-center justify-center space-x-1 cursor-pointer"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
