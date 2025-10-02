# Claude Desktop - MCP Tools Usage Guide

---

## 🔴 RULE #1: Always Call conversation_log

**At the end of EVERY response, you MUST call `mcp_ai-agent-orchestrator_conversation_log`**

No exceptions. Simple question or complex task - always call it.

---

## 🔴 RULE #2: meta Parameter is a STRING

**This is the most common error. Pay attention!**

```python
# ❌ WRONG - causes "Input should be a valid string" error
{
  "meta": {"source": "claude"}
}

# ❌ WRONG - even with topic
{
  "meta": {"source": "claude", "topic": "team_work_summary"}
}

# ✅ CORRECT - meta must be a STRING
{
  "meta": "{\"source\":\"claude\"}"
}

# ✅ CORRECT - with topic
{
  "meta": "{\"source\":\"claude\",\"topic\":\"team_work_summary\"}"
}
```

**Key point: Wrap the JSON object in quotes and escape internal quotes with `\"`**

---

## 📋 How to Call conversation_log

**Tool name:** `mcp_ai-agent-orchestrator_conversation_log`

**Parameters (all strings):**

1. **channel** - Session ID
   - Format: `"claude_session_YYYYMMDD_HHMM"`
   - Use current date/time
   - Example: `"claude_session_20251002_1630"`

2. **messages** - Conversation history as JSON string
   - Format: `"[{\"role\":\"user\",\"text\":\"...\",\"timestamp\":\"...\"}]"`
   - Escape internal quotes with `\"`
   - Use ISO 8601 timestamps

3. **meta** - Metadata as JSON string (⚠️ NOT an object!)
   - Format: `"{\"source\":\"claude\"}"`
   - To add topic: `"{\"source\":\"claude\",\"topic\":\"discussion\"}"`
   - Always escape internal quotes with `\"`

---

## ✅ Correct Example

```python
{
  "channel": "claude_session_20251002_1630",
  "messages": "[{\"role\":\"user\",\"text\":\"Tell me about the project\",\"timestamp\":\"2025-10-02T16:30:00Z\"},{\"role\":\"assistant\",\"text\":\"This project is about...\",\"timestamp\":\"2025-10-02T16:30:15Z\"}]",
  "meta": "{\"source\":\"claude\"}"
}
```

**With topic:**
```python
{
  "channel": "claude_session_20251002_1630",
  "messages": "[{\"role\":\"user\",\"text\":\"Team work summary?\",\"timestamp\":\"2025-10-02T16:30:00Z\"}]",
  "meta": "{\"source\":\"claude\",\"topic\":\"team_work_summary\"}"
}
```

---

## 📋 How to Call extract (when needed)

**Tool name:** `mcp_ai-agent-orchestrator_extract`

**Parameters (all strings):**

1. **query** - Search query as JSON string
   - Format: `"{\"text\":\"search term\",\"limit\":20}"`
   - Always a string, not an object

2. **channel** - Search scope
   - Use `""` for all channels
   - Or specific session ID

**Example:**
```python
{
  "query": "{\"text\":\"team work\",\"limit\":20}",
  "channel": ""
}
```

---

## 🚫 Common Mistakes

### Mistake #1: meta as Object
```python
# ❌ WRONG
"meta": {"source": "claude"}

# ✅ CORRECT
"meta": "{\"source\":\"claude\"}"
```

### Mistake #2: Using Backticks
```python
# ❌ WRONG
`meta`: `{\"source\":\"claude\"}`

# ✅ CORRECT
"meta": "{\"source\":\"claude\"}"
```

### Mistake #3: Double Escaping
```python
# ❌ WRONG
"meta": "{\\\"source\\\":\\\"claude\\\"}"

# ✅ CORRECT
"meta": "{\"source\":\"claude\"}"
```

---

## 📝 Response Pattern

**Follow this pattern for every response:**

1. Answer user's question
2. Call `conversation_log` tool with correct parameters
3. Done

**Remember:**
- meta is a STRING (not object)
- Escape quotes once: `\"`
- No backticks, use double quotes: `"`

---

## 🔍 Quick Checklist

Before calling the tool, verify:

- [ ] meta is a string? `"{\"source\":\"claude\"}"`
- [ ] NOT an object? `{"source": "claude"}` ← Wrong!
- [ ] Using double quotes, not backticks?
- [ ] Escaping once, not twice?

---

## 💡 Remember

**meta parameter format:**
- Basic: `"{\"source\":\"claude\"}"`
- With topic: `"{\"source\":\"claude\",\"topic\":\"your_topic\"}"`

**Always wrap the entire JSON in quotes and escape internal quotes!**
