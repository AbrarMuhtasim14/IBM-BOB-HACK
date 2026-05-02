# SmartShift - Quick Start Guide

Get SmartShift running in 5 minutes! 🚀

---

## Prerequisites Checklist

- [ ] Python 3.10 or higher installed
- [ ] IBM watsonx.ai account (or ready to use without LLM)
- [ ] 4GB RAM available
- [ ] Internet connection

---

## Installation Steps

### 1️⃣ Install Dependencies (2 minutes)

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

**Expected output:** All packages installed successfully

---

### 2️⃣ Configure Environment (1 minute)

```bash
# Copy environment template
cp .env.example .env
```

**Edit `.env` file:**

```bash
# Option A: With IBM watsonx.ai (full AI features)
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Option B: Without watsonx.ai (fallback mode)
# Leave credentials empty - system will use rule-based logic
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
```

---

### 3️⃣ Run the Application (30 seconds)

```bash
streamlit run app.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

The app will automatically:
- ✅ Load 30 worker profiles
- ✅ Generate skill embeddings
- ✅ Index workers in ChromaDB
- ✅ Initialize AI agents
- ✅ Open in your browser

---

## First Test (1 minute)

### Step 1: View Workers
You should see a table with 30 workers across 4 zones.

### Step 2: Try a Query
In the "Report Overload Situation" box, enter:
```
Zone A dispatch is overloaded, need forklift help
```

### Step 3: Get Recommendation
Click "Get AI Recommendation" and wait 3-5 seconds.

### Step 4: Review Result
You should see:
- ✅ Recommended worker
- ✅ AI reasoning
- ✅ Load impact analysis
- ✅ Alternative candidates

### Step 5: Confirm (Optional)
Click "Confirm Shift" to execute the change.

---

## Test Scenarios

### Scenario 1: Basic Skill Match
```
Zone A needs forklift operator
```
**Expected:** Worker with forklift as primary skill

### Scenario 2: Transferable Skill
```
Zone C dispatch overloaded, need loading help
```
**Expected:** Worker with loading as transferable skill

### Scenario 3: Shift-Specific
```
Zone B packing needs help for afternoon shift
```
**Expected:** Only afternoon shift workers

### Scenario 4: Urgent Request
```
Urgent: Zone D storage overloaded, need inventory manager
```
**Expected:** High-priority recommendation

---

## Troubleshooting

### ❌ Import Errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### ❌ "No workers found"
```bash
# Check if CSV exists
ls data/workers.csv

# If missing, the file should have been created during setup
```

### ❌ ChromaDB Errors
```bash
# Delete and recreate
rm -rf chroma_db/
# Restart app - will auto-recreate
```

### ❌ Port Already in Use
```bash
# Use different port
streamlit run app.py --server.port 8502
```

### ⚠️ "LLM not configured"
This is normal if you didn't add watsonx.ai credentials. The system will use fallback logic (still works, just without AI reasoning text).

---

## System Requirements

### Minimum
- Python 3.10+
- 4GB RAM
- 1GB disk space
- Internet (for initial model download)

### Recommended
- Python 3.11+
- 8GB RAM
- 2GB disk space
- IBM watsonx.ai account

---

## What's Happening Behind the Scenes?

When you run `streamlit run app.py`:

1. **Load Configuration** (0.5s)
   - Read environment variables
   - Set up logging

2. **Load Worker Data** (0.5s)
   - Parse `data/workers.csv`
   - Validate 30 worker profiles

3. **Generate Embeddings** (2s)
   - Download sentence-transformers model (first time only)
   - Create vector embeddings for all skills

4. **Initialize Vector Store** (0.5s)
   - Set up ChromaDB
   - Index worker profiles

5. **Initialize AI Agents** (0.5s)
   - Create CrewAI agents
   - Connect to watsonx.ai (if configured)

6. **Launch UI** (0.5s)
   - Start Streamlit server
   - Open browser

**Total: ~4-5 seconds**

---

## Next Steps

✅ **You're ready!** Try the test scenarios above.

📚 **Learn More:**
- Read [README.md](README.md) for full documentation
- Check [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for architecture details

🎥 **Record Demo:**
- Use the test scenarios
- Record a 2-3 minute video
- Show the full workflow

🐛 **Found Issues?**
- Check the troubleshooting section
- Review logs in the terminal
- Ensure all dependencies are installed

---

## Demo Checklist

Before recording your demo:

- [ ] App loads without errors
- [ ] Worker registry displays 30 workers
- [ ] Zone statistics show correctly
- [ ] Can enter overload description
- [ ] AI recommendation appears (3-7 seconds)
- [ ] Reasoning is clear and logical
- [ ] Load impact shows percentages
- [ ] Can confirm shift change
- [ ] Worker registry updates after confirmation

---

## Performance Tips

### Speed Up Embeddings
First run downloads the model (~80MB). Subsequent runs are instant.

### Reduce Memory Usage
```python
# In config/settings.py, use smaller model
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Current (90MB)
# vs
EMBEDDING_MODEL=paraphrase-MiniLM-L3-v2  # Smaller (60MB)
```

### Faster Responses
- Use local ChromaDB (already configured)
- Reduce `LLM_MAX_TOKENS` in `.env` (default: 500)
- Lower `LLM_TEMPERATURE` for more deterministic responses

---

## Success Indicators

✅ **System is working if:**
1. App loads in browser
2. Worker table displays
3. Can submit overload request
4. Gets recommendation within 10 seconds
5. Recommendation includes reasoning
6. Can confirm shift change

---

## Support

**Common Questions:**

**Q: Do I need watsonx.ai credentials?**
A: No, but recommended. System works without them using fallback logic.

**Q: How long does first run take?**
A: 30-60 seconds (downloads embedding model). Subsequent runs: 5 seconds.

**Q: Can I modify worker data?**
A: Yes! Edit `data/workers.csv` and restart the app.

**Q: How do I reset the system?**
A: Delete `chroma_db/` folder and restart.

---

**Ready to go! 🎉**

Run `streamlit run app.py` and start optimizing your warehouse workforce!