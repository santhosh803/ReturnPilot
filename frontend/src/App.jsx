import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Analytics from "./components/Analytics";
import ChatInterface from "./components/ChatInterface";
import ReturnQueue from "./components/ReturnQueue";

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Analytics />} />
            <Route path="/chat" element={<ChatInterface />} />
            <Route path="/returns" element={<ReturnQueue />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
