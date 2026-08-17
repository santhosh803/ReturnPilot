import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Bot, BarChart2, Inbox, Sparkles } from "lucide-react";

export default function Navbar() {
  const location = useLocation();

  const navItems = [
    { label: "Dashboard", path: "/", icon: BarChart2 },
    { label: "AI Agent Chat", path: "/chat", icon: Bot },
    { label: "Return Queue", path: "/returns", icon: Inbox },
  ];

  return (
    <nav className="h-16 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center space-x-8">
        <Link to="/" className="flex items-center space-x-2.5 group">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <Sparkles className="w-4 h-4" />
          </div>
          <span className="font-bold text-base tracking-tight text-white group-hover:text-indigo-300 transition-colors">
            ReturnPilot
          </span>
        </Link>

        <div className="flex items-center space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`px-3.5 py-2 rounded-xl text-xs font-medium flex items-center space-x-2 transition-all ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />
          MCP Server Connected
        </span>
      </div>
    </nav>
  );
}
