# ReturnPilot

AI-powered eCommerce returns management platform with an MCP (Model Context Protocol) server and LangGraph agent that enables intelligent returns processing, exchange recommendations, risk scoring, and policy enforcement through natural language.

---

## Core Architecture

```
Customer / Merchant Input (Natural Language)
                     │
                     ▼
             LangGraph ReAct Agent
                     │
                     ▼ (Calls Tools via MCP)
┌────────────────────────────────────────────────────────┐
│                   ReturnPilot MCP Server               │
│                                                        │
│  • lookup_order             • recommend_exchange       │
│  • check_return_eligibility • flag_serial_returner     │
│  • initiate_return          • process_refund (HITL)    │
│  • classify_return_reason   • list_pending_returns     │
└────────────────────────────────────────────────────────┘
                     │
                     ▼
        Django ORM  ──►  PostgreSQL (Neon)
```

---

## MCP Server Tools

ReturnPilot exposes 8 tools via the Model Context Protocol:

| Tool | Description |
|---|---|
| `lookup_order` | Retrieve order items, delivery timeline, customer profile, and return history. |
| `check_return_eligibility` | Evaluate return window and category-specific conditions. |
| `initiate_return` | Create return requests with free-text customer reasons and line items. |
| `classify_return_reason` | Classify customer return intent into structured return categories. |
| `recommend_exchange` | Suggest catalog alternatives (sizes/colors/similar items) to minimize refunds. |
| `flag_serial_returner` | Detect return abuse patterns and compute behavioral risk scores. |
| `process_refund` | Process refunds with human-in-the-loop (HITL) escalation gates. |
| `list_pending_returns` | Query and filter merchant review queues by lifecycle status. |

---

## Claude Desktop Configuration

To connect ReturnPilot MCP tools to Claude Desktop, add the following configuration to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ReturnPilot": {
      "command": "python",
      "args": ["manage.py", "run_mcp_server"],
      "cwd": "/path/to/ReturnPilot"
    }
  }
}
```

---

## Local Setup

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/santhosh803/ReturnPilot.git
cd ReturnPilot

# Install dependencies using uv
uv sync
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in the database and service configurations:
```bash
cp .env.example .env
```

### 3. Run Migrations & Seed Data
```bash
uv run python manage.py migrate
uv run python manage.py seed_data
```

### 4. Run the Servers
- **Django API & Admin**: `uv run python manage.py runserver`
- **MCP Server (stdio mode)**: `uv run python manage.py run_mcp_server`
- **MCP Server (SSE mode on port 8001)**: `uv run python manage.py run_mcp_server --transport sse --port 8001`
