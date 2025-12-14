# Step 7 - Question Answering Mode

**Status:** Idea

---

## Goal

Instead of just returning search results, synthesize an answer from multiple notes - like a personal RAG system.

---

## Ideas

- New tool: `ask_vault(question)`
- Searches for relevant chunks
- Passes them to Claude with the question
- Returns a synthesized answer with citations

---

## Potential Features

- "According to your notes, here's what you know about X..."
- Citation links back to source notes
- Confidence scoring based on how much relevant content exists
- "You haven't written much about this" detection

---

## Implementation Thoughts

- Could use Claude as the synthesis layer
- Or a smaller local model for privacy
- Need to handle "I don't have notes on this" gracefully

---

## Example Usage

```
User: "What's my philosophy on productivity?"
Claude: Based on your notes, you believe in [X] (from [[Note1]]),
        combined with [Y] (from [[Note2]])...
```
