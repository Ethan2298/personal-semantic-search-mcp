# Step 5 - Search Results Tuning

**Status:** Idea

---

## Goal

Optimize the search results - how many to return, relevance thresholds, and result formatting.

---

## Current Behavior

- Default limit: 5 results
- No minimum relevance threshold
- Returns 300 char preview per chunk
- Score shown but not filtered on

---

## Questions to Resolve

- [ ] What's a good default number of results?
- [ ] Should we filter out low-relevance results (e.g., score < 0.3)?
- [ ] Is 300 chars enough preview, or too much?
- [ ] Should results include full file path or just filename?
- [ ] Add option to return full chunk content instead of preview?

---

## Ideas

- Add `min_score` parameter to filter weak matches
- Add `preview_length` parameter
- Add `include_full_content` boolean
- Better formatting of results (collapsible? numbered?)
- Show which headers/sections matched

---

## Testing Needed

Run searches and evaluate:
1. Are top results actually relevant?
2. Are low-scoring results noise?
3. What score range indicates "good" vs "weak" matches?
