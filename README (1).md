# 🎬 YouTube Video Summarizer
### World Fashion Exchange — Assessment Submission
**Candidate:** Devansh | **Role:** Data & AI Analyst

---

## What This Tool Does

Paste any YouTube video link and instantly get:
- A **short summary** (3–4 lines)
- A **detailed summary** (200–300 words)
- **Key bullet points** from the video
- **Actionable insights** you can apply
- An **interactive mind map** of the video's concepts
- A **history sidebar** — every summary you've ever generated, saved automatically

---

## My Approach

I broke the problem into four clear layers:

**1. Input & Validation**
Before anything else, the URL is validated and the YouTube video ID is extracted. This catches invalid links, private videos, playlists, and Shorts upfront — before any API call is made.

**2. Transcript Extraction**
Using `youtube-transcript-api`, the tool fetches the video's transcript. It prioritizes manually created captions over auto-generated ones for accuracy. The transcript language is detected automatically.

**3. AI Processing via Groq**
The transcript is sent to Groq's LLaMA 3.3-70B model — one of the fastest LLMs available — which generates all five output sections in a single structured JSON call. For non-English videos, a translation step runs first. For long videos, the transcript is split into 3,000-word chunks, each summarized separately, then merged.

**4. Presentation**
Results are displayed in a clean tabbed Streamlit interface. Every summary is saved to a local SQLite database and appears in the history sidebar — similar to how ChatGPT or Claude organizes past conversations. The mind map is rendered as an interactive draggable graph.

---

## Tools & Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| Transcript | youtube-transcript-api |
| AI / LLM | Groq API (LLaMA 3.3-70B) |
| Mind Map | streamlit-agraph |
| History | SQLite (local database) |
| IDE | Cursor (AI-assisted development) |
| Language | Python 3 |

---

## Standout Features (Beyond Requirements)

### 1. History System
Every summarized video is saved to a local SQLite database. The sidebar shows all past summaries with language tags, duration, and timestamps — just like Claude or ChatGPT's conversation history. Click any item to reload it instantly. No duplicate API calls — if you paste the same video again, it loads from history.

### 2. Interactive Mind Map
The video's concepts are automatically structured into a central topic with branches and subtopics, then rendered as a live draggable graph using `streamlit-agraph`. Users can drag nodes, zoom, and explore the concept structure visually.

### 3. Multi-Language Support
The tool detects the transcript language automatically. If the video is in Hindi, Spanish, French, Arabic, or any other language, it translates the transcript to English via Groq before summarizing. Mixed-language videos (like Hinglish) are handled naturally.

---

## Edge Cases Handled

| Situation | How It's Handled |
|---|---|
| Invalid or malformed URL | Validated before any API call; clear error shown |
| Private or deleted video | Specific error caught and displayed to user |
| Playlist URL (not single video) | Detected and rejected with instructions |
| YouTube Shorts | URL pattern normalized; works like any video |
| No transcript available | Clear error: creator has disabled captions |
| Auto-generated captions only | Works, but user is warned about potential inaccuracies |
| Very short video (< 50 words) | Warning shown; summary attempted anyway |
| Non-English video | Auto-detected → translated to English → summarized |
| Mixed-language video (Hinglish) | Groq handles naturally; output always in English |
| Very long video (2hr+) | Transcript chunked into 3,000-word segments; each chunk summarized separately; results merged |
| Groq rate limit hit | Auto-retry after 5 seconds; user not shown raw error |
| Missing API key | Clear setup instructions shown |
| Same video submitted twice | Loads from history; no duplicate API call |
| Malformed JSON from Groq | Fallback parser extracts what it can |

---

## Challenges Faced

**1. YouTube Transcript API Version Change**
The library updated its API between versions — `YouTubeTranscriptApi.list_transcripts()` became an instance method instead of a static one. Discovered this through the error and fixed by instantiating the class first.

**2. Groq Tagging Consistency**
When I first tried inline text highlighting, Groq would inconsistently apply or forget closing tags, or over-tag nearly every phrase. I iterated on the prompt several times before settling on plain text output for cleaner, more reliable results.

**3. Long Video Chunking**
LLMs have context limits. A 2-hour video transcript can be 15,000+ words. I solved this by chunking at 3,000 words, summarizing each chunk independently, then sending all chunk summaries back to Groq for a final merge — producing one coherent output.

**4. Mind Map Data Pollution**
Groq would sometimes include formatting tags inside mind map node labels, making them render with raw text like `[CONCEPT]elasticity[/CONCEPT]`. Fixed with a server-side strip function that cleans all node labels before rendering.

---

## How AI Helped Me Build This

- **Cursor** helped generate boilerplate, catch bugs in real time, and autocomplete repetitive patterns
- **Claude (Anthropic)** helped me think through the architecture, debug edge cases, and structure the Groq prompts for consistent JSON output
- **Groq / LLaMA 3.3** is the brain of the tool — doing translation, summarization, key point extraction, and mind map generation all in one call

---

## How to Run

```bash
# 1. Clone or download the project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Groq API key to .env
echo "GROQ_API_KEY=your_key_here" > .env

# 4. Run
streamlit run app.py
```

Get a free Groq API key at: https://console.groq.com

---

## Project Structure

```
yt-summarizer/
├── app.py            # Streamlit UI
├── transcript.py     # YouTube transcript fetcher + edge case handling
├── summarizer.py     # Groq AI summarization pipeline
├── mindmap.py        # Interactive mind map renderer
├── history.py        # SQLite history system
├── utils.py          # Helper functions
├── .env              # API key (not committed)
├── requirements.txt
└── README.md
```
