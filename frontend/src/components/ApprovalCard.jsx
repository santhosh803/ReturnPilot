import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle, ShieldAlert, DollarSign } from "lucide-react";
import { approveAgentReturn } from "../api/client";

export default function ApprovalCard({
  hitlDetails,
  sessionId,
  onResolved,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resolvedDecision, setResolvedDecision] = useState(null);

  if (!hitlDetails) return null;

  const returnId = hitlDetails.return_id;
  const refundAmount = hitlDetails.refund_amount || 0;
  const hitlReason = hitlDetails.hitl_reason || "Merchant authorization required.";
  const riskSummary = hitlDetails.risk_summary || "";

  const handleDecision = async (decision) => {
    setLoading(true);
    setError(null);
    try {
      const res = await approveAgentReturn({
        sessionId,
        returnId,
        decision,
        reason: `Merchant manual decision via UI: ${decision}`,
      });
      setResolvedDecision(decision);
      if (onResolved) onResolved(decision, res);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Failed to process approval");
    } finally {
      setLoading(false);
    }
  };

  if (resolvedDecision) {
    return (
      <div className={`mt-3 p-4 rounded-xl border ${resolvedDecision === 'approved' ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' : 'bg-rose-950/40 border-rose-500/40 text-rose-300'} flex items-center justify-between`}>
        <div className="flex items-center space-x-3">
          {resolvedDecision === 'approved' ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <XCircle className="w-5 h-5 text-rose-400" />}
          <span className="text-sm font-medium">Return <strong>{returnId}</strong> {resolvedDecision.toUpperCase()} by merchant.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 p-4 rounded-xl border border-amber-500/40 bg-amber-950/20 text-slate-200 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-amber-500/20">
        <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm">
          <ShieldAlert className="w-5 h-5" />
          <span>Human-In-The-Loop Review Required</span>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
          Awaiting Decision
        </span>
      </div>

      <div className="mt-3 space-y-2 text-xs">
        <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
          <span className="text-slate-400">Return ID:</span>
          <span className="font-mono font-semibold text-slate-100">{returnId}</span>
        </div>
        <div className="flex justify-between items-center bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
          <span className="text-slate-400">Requested Refund:</span>
          <span className="font-semibold text-emerald-400 text-sm flex items-center">
            <DollarSign className="w-3.5 h-3.5" />
            {Number(refundAmount).toFixed(2)}
          </span>
        </div>
        <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800 text-slate-300">
          <span className="text-slate-400 block mb-1">Trigger Reason:</span>
          <p className="text-slate-200 leading-relaxed">{hitlReason}</p>
          {riskSummary && (
            <p className="mt-1.5 text-amber-300/90 font-medium">
              {riskSummary}
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-2 text-xs text-rose-400 bg-rose-950/30 p-2 rounded border border-rose-500/30">
          {error}
        </div>
      )}

      <div className="mt-4 flex items-center space-x-3">
        <button
          onClick={() => handleDecision("approved")}
          disabled={loading}
          className="flex-1 py-2 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center justify-center space-x-1.5 transition-all shadow-md disabled:opacity-50 cursor-pointer"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>{loading ? "Processing..." : "Approve Refund"}</span>
        </button>
        <button
          onClick={() => handleDecision("rejected")}
          disabled={loading}
          className="flex-1 py-2 px-4 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs flex items-center justify-center space-x-1.5 transition-all shadow-md disabled:opacity-50 cursor-pointer"
        >
          <XCircle className="w-4 h-4" />
          <span>{loading ? "Processing..." : "Reject Return"}</span>
        </button>
      </div>
    </div>
  );
}
