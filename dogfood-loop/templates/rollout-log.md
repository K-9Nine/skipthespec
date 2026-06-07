# Rollout Log — <feature name>

> One log per feature. Append a block per rung. This is the evidence the promote/iterate/kill decision is based on. Keep it factual.

- **Mission (one sentence):**
- **Feature flag:**
- **Success metric + target:**
- **Rollback metric + threshold:**

---

## Rung <0|1|2|3|4> — <audience> — <date opened>

### Quantitative
- Eligible users: 
- Invoked (adoption): __ / __ = __%
- Completed success (helpfulness): __ / __ = __%
- Rollback metric reading: __ (threshold: __) — [ ] within / [ ] tripped
- Retention (day-2 / day-7), if applicable: 

### Qualitative (verbatim, not summarized)
- 👍 …
- 👎 …
- 🐞 Bug/friction: … (severity: low/med/high) → [ ] converted to eval task in eval-loops

### Synthesis
- What the data says (not opinion): 
- Biases checked: [ ] vocal-minority [ ] novelty spike [ ] survivorship [ ] goalpost drift

### Decision
- [ ] Promote to next rung   [ ] Iterate (back to prototype-first)   [ ] Kill (flip switch)
- Recommendation reasoning: 
- Human verdict (required for default-on / ultimate success): 
- Date closed: 

---
```
(repeat block for each rung)
```
