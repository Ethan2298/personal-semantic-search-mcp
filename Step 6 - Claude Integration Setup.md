# Step 6 - Claude Integration Setup

**Status:** Idea

---

## Goal

Configure Claude Code to understand when and how to use semantic search proactively, without being prompted.

---

## Current Problem

- Claude only uses search when explicitly asked
- Doesn't know the vault structure or what's indexed
- No guidance on when searching would be helpful

---

## Implementation

### Update CLAUDE.md with:

1. **When to search proactively:**
   - User asks about something they "wrote before" or "have notes on"
   - User references a concept that might exist in vault
   - User asks "what do I know about X"
   - Starting work on a topic that likely has prior notes

2. **How to use the tools:**
   - `search_notes` - semantic search, good for concepts
   - `index_notes` - run after adding new files
   - `get_index_stats` - check what's indexed

3. **What's indexed:**
   - 909 chunks across 378 files
   - Mostly .md (80%), some .py (13%)
   - Location: ~/Desktop/Notes

---

## Questions to Resolve

- [ ] What triggers should make Claude search automatically?
- [ ] Should Claude announce when it's searching or do it silently?
- [ ] How to handle "no results found" gracefully?

---

## CLAUDE.md Section Draft

```markdown
## Semantic Search Integration

You have access to a semantic search MCP that indexes this vault.

**Use proactively when:**
- User asks about prior notes or knowledge
- A topic comes up that likely has existing notes
- User says "I wrote about this" or "what do I know about"

**Tools:**
- `search_notes(query, limit)` - semantic search
- `get_index_stats()` - see what's indexed
- `index_notes()` - re-index after changes
```
