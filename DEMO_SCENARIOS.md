# SmartShift Demo Scenarios

Test scenarios for demonstrating SmartShift capabilities during the hackathon demo.

---

## 🎬 Demo Flow (3 Minutes)

### Minute 1: Introduction (30 seconds)
**Script:**
> "Warehouse managers face a daily challenge: when one zone gets overloaded, they need to quickly find the right worker with the right skills to help. This is usually done manually, relying on memory and spreadsheets. SmartShift solves this with AI."

**Show:**
- Problem statement slide
- Quick architecture diagram

---

### Minute 2: Live Demo (2 minutes)

#### Part 1: Show Current State (20 seconds)
**Action:** Open SmartShift app
**Point out:**
- 30 workers across 4 zones
- Real-time load status (color-coded)
- Zone statistics at the top

**Script:**
> "Here we have 30 warehouse workers across 4 zones. Each has primary skills and transferable skills. Notice Zone A has high load while Zone B has low load."

---

#### Part 2: Report Overload (30 seconds)
**Action:** Type in the input box:
```
Zone A dispatch is overloaded, need forklift help
```

**Click:** "Get AI Recommendation"

**Script:**
> "A manager simply describes the situation in plain English. Our AI parses this to understand: Zone A needs help, the skill required is forklift operation."

**While waiting (3-5 seconds):**
> "Behind the scenes, the system is:
> 1. Searching our vector database for workers with forklift skills
> 2. Filtering by availability and zone
> 3. Having our AI agents analyze the best match"

---

#### Part 3: Show Recommendation (40 seconds)
**Action:** Point to the recommendation card

**Highlight:**
1. **Selected Worker:** "Ahmed Hassan from Zone B"
2. **Reasoning:** Read the AI-generated explanation
3. **Load Impact:** Show before/after percentages
4. **Alternative Candidates:** Expand to show other options

**Script:**
> "The AI recommends Ahmed Hassan. Why? He has forklift as a transferable skill, his current zone has low load and can spare him, and moving him will balance the workload. The system even shows us the load impact - Zone A will drop from 90% to 75%, while Zone B only increases from 40% to 45%."

---

#### Part 4: Confirm Shift (30 seconds)
**Action:** Click "Confirm Shift"

**Show:**
- Success message
- Updated worker registry (Ahmed now in Zone A)
- New zone statistics

**Script:**
> "With one click, the shift is confirmed. The worker registry updates in real-time, and we can see the new zone balance. What used to take 10-15 minutes of phone calls and checking spreadsheets now takes 30 seconds."

---

### Minute 3: Technical Highlights (30 seconds)

**Script:**
> "SmartShift is powered by:
> - IBM Granite LLM via watsonx.ai for intelligent reasoning
> - CrewAI agents that collaborate to find the best match
> - Semantic skill search using vector embeddings
> - And everything was built using IBM Bob IDE
>
> The system works even without internet - it uses local ChromaDB and can fall back to rule-based logic if the LLM isn't available."

---

## 📋 Test Scenarios

### Scenario 1: Primary Skill Match ✅
**Input:**
```
Zone A needs forklift operator
```

**Expected Result:**
- Worker with "Forklift Operator" as primary skill
- High confidence score (>0.8)
- Match type: "primary"
- Clear reasoning about skill match

**Success Criteria:**
- ✅ Finds worker with forklift as primary skill
- ✅ Excludes workers already in Zone A
- ✅ Selects available worker
- ✅ Provides clear reasoning

---

### Scenario 2: Transferable Skill Match ✅
**Input:**
```
Zone C dispatch overloaded, need loading help
```

**Expected Result:**
- Worker with "Loading" in transferable skills
- Medium-high confidence (0.6-0.8)
- Match type: "transferable"
- Reasoning mentions transferable skill

**Success Criteria:**
- ✅ Finds worker with loading as transferable skill
- ✅ Explains why transferable skill is suitable
- ✅ Shows alternative candidates
- ✅ Load impact analysis included

---

### Scenario 3: Shift-Specific Request ✅
**Input:**
```
Zone B packing needs help for afternoon shift
```

**Expected Result:**
- Only afternoon shift workers recommended
- Worker with packing skill
- Reasoning mentions shift compatibility

**Success Criteria:**
- ✅ Filters by afternoon shift
- ✅ Finds packing specialist
- ✅ No morning/night shift workers shown
- ✅ Shift mentioned in reasoning

---

### Scenario 4: Urgent Request ⚡
**Input:**
```
Urgent: Zone D storage overloaded, need inventory manager
```

**Expected Result:**
- Quick response
- Best available inventory manager
- Urgency acknowledged in reasoning

**Success Criteria:**
- ✅ Processes urgency flag
- ✅ Finds inventory manager
- ✅ Prioritizes low-load source zones
- ✅ Clear action plan

---

### Scenario 5: Multiple Skill Keywords 🔍
**Input:**
```
Zone A receiving needs heavy equipment operator or forklift
```

**Expected Result:**
- Workers with either skill
- Ranked by match quality
- Multiple candidates shown

**Success Criteria:**
- ✅ Matches both "heavy equipment" and "forklift"
- ✅ Shows semantic similarity
- ✅ Ranks by relevance
- ✅ Explains skill relationship

---

### Scenario 6: Zone Capacity Check 📊
**Input:**
```
Zone B is overloaded, need packing specialist
```

**Expected Result:**
- Worker from zone with spare capacity
- Load impact shows improvement
- Source zone can spare the worker

**Success Criteria:**
- ✅ Checks source zone capacity
- ✅ Doesn't take from high-load zones
- ✅ Shows load rebalancing
- ✅ Overall balance improves

---

## 🎯 Success Metrics

### Functional Metrics
- ✅ All 6 scenarios return valid recommendations
- ✅ Response time < 10 seconds per query
- ✅ Recommendations include reasoning
- ✅ Load impact calculations accurate
- ✅ Shift confirmation works correctly

### Quality Metrics
- ✅ Skill matching accuracy > 80%
- ✅ Reasoning is clear and logical
- ✅ Alternative candidates are relevant
- ✅ Load balancing improves overall distribution
- ✅ No workers recommended from high-load zones

### User Experience Metrics
- ✅ UI is intuitive and responsive
- ✅ Natural language input works
- ✅ Visual feedback is clear
- ✅ Error messages are helpful
- ✅ One-click confirmation

---

## 🐛 Edge Cases to Test

### Edge Case 1: No Available Workers
**Input:**
```
Zone A needs quantum physicist
```

**Expected:**
- Error message: "No available workers found with quantum physicist skill"
- Suggestion to try different skill or zone

---

### Edge Case 2: All Workers Busy
**Setup:** Mark all workers as unavailable
**Input:**
```
Zone A needs forklift operator
```

**Expected:**
- Error message: "No available workers at this time"
- Suggestion to check back later

---

### Edge Case 3: Ambiguous Zone
**Input:**
```
The warehouse needs help with packing
```

**Expected:**
- Error message: "Could not identify which zone is overloaded"
- Prompt to specify zone

---

### Edge Case 4: Ambiguous Skill
**Input:**
```
Zone A is overloaded
```

**Expected:**
- Error message: "Could not identify required skill"
- Prompt to specify what type of worker is needed

---

## 📊 Performance Benchmarks

### Target Performance
| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Initial Load | < 5s | < 10s | > 10s |
| Query Response | < 5s | < 10s | > 10s |
| Embedding Generation | < 3s | < 5s | > 5s |
| Vector Search | < 100ms | < 500ms | > 500ms |
| UI Responsiveness | Instant | < 1s | > 1s |

### Actual Performance (to be measured)
- Initial Load: _____ seconds
- Query Response: _____ seconds
- Embedding Generation: _____ seconds
- Vector Search: _____ ms
- UI Responsiveness: _____ ms

---

## 🎥 Recording Checklist

Before recording demo video:

### Pre-Recording
- [ ] System fully initialized
- [ ] All 30 workers loaded
- [ ] ChromaDB indexed
- [ ] Browser window sized appropriately
- [ ] Screen recording software ready
- [ ] Audio test completed
- [ ] Script reviewed

### During Recording
- [ ] Clear audio narration
- [ ] Smooth mouse movements
- [ ] Pause for AI processing
- [ ] Highlight key features
- [ ] Show reasoning clearly
- [ ] Demonstrate confirmation
- [ ] Show updated state

### Post-Recording
- [ ] Video length 2-3 minutes
- [ ] Audio clear and audible
- [ ] All features demonstrated
- [ ] No errors or glitches shown
- [ ] Professional presentation
- [ ] Exported in HD quality

---

## 🔄 Reset Instructions

Between demo runs:

```bash
# Option 1: Soft reset (keep embeddings)
# Just restart the app
streamlit run app.py

# Option 2: Full reset (re-index everything)
rm -rf chroma_db/
streamlit run app.py
```

---

## 💡 Demo Tips

### Do's ✅
- Speak clearly and confidently
- Explain what's happening during wait times
- Highlight the AI reasoning
- Show the load impact visually
- Mention IBM technologies used
- Keep it under 3 minutes

### Don'ts ❌
- Don't rush through the demo
- Don't skip the reasoning explanation
- Don't ignore errors (have backup scenarios)
- Don't forget to mention IBM Bob IDE
- Don't exceed 3 minutes

---

## 🏆 Judging Criteria Alignment

### Innovation (25%)
- ✅ AI-powered workforce optimization
- ✅ Semantic skill matching
- ✅ Natural language interface
- ✅ Real-time recommendations

### Technical Implementation (25%)
- ✅ IBM Granite LLM integration
- ✅ CrewAI multi-agent system
- ✅ Vector database for semantic search
- ✅ Clean architecture

### IBM Technology Usage (25%)
- ✅ IBM Bob IDE (all code)
- ✅ IBM watsonx.ai (Granite model)
- ✅ Proper integration and usage

### Presentation (25%)
- ✅ Clear problem statement
- ✅ Live working demo
- ✅ Professional UI
- ✅ Comprehensive documentation

---

**Ready to demo! 🚀**

Follow the 3-minute script above for a winning presentation!