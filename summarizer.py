from groq import Groq
from dotenv import load_dotenv
import os
import json
import time

load_dotenv(override=True)
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# Primary model — llama-3.1-8b-instant is widely available on free tier.
# Fallback chain tried in order if a model is unavailable.
MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODELS = [
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen/qwen3-32b",
]
# ─────────────────────────────────────────
# 1. CORE GROQ CALLER
# ─────────────────────────────────────────

def call_groq(prompt: str, system: str = "", retries: int = 2) -> str:
    """
    Core function to call Groq API with retry logic.
    Returns response text or raises an error.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    models_to_try = [MODEL] + FALLBACK_MODELS

    for model in models_to_try:
        for attempt in range(retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.4,
                    max_tokens=4096,
                )
                return response.choices[0].message.content

            except Exception as e:
                error_str = str(e).lower()
                if "api_key" in error_str or "authentication" in error_str:
                    raise Exception("❌ Invalid Groq API key. Please check your .env file.")
                elif "model" in error_str or "model_not_found" in error_str:
                    # This model isn't available — break inner loop, try next model
                    break
                elif "rate_limit" in error_str and attempt < retries:
                    time.sleep(5)
                    continue
                else:
                    if attempt < retries:
                        time.sleep(3)
                        continue
                    # Last attempt on this model failed — try next model
                    break

    raise Exception("❌ All Groq models unavailable. Please check your API key quota at console.groq.com")


# ─────────────────────────────────────────
# 2. TRANSLATION (if non-english)
# ─────────────────────────────────────────

def translate_to_english(text: str, language_name: str) -> str:
    """
    Translates transcript to English if it's in another language.
    Handles chunked translation for long transcripts.
    """
    system = "You are an expert translator. Translate the given text to English accurately. Return only the translated text, nothing else."

    prompt = f"""The following text is in {language_name}. 
Translate it to English. Preserve the meaning and context carefully.

TEXT:
{text}

Return only the English translation."""

    return call_groq(prompt, system)


# ─────────────────────────────────────────
# 3. MAIN SUMMARIZER
# ─────────────────────────────────────────

def summarize(transcript_result: dict) -> dict:
    """
    Main summarization pipeline.
    Handles translation, chunking, and full summary generation.
    Returns complete summary dict.
    """

    # Step 1: Check API key exists
    load_dotenv(override=True)
    if not os.getenv("GROQ_API_KEY"):
        return {"error": "❌ GROQ_API_KEY not found. Please add it to your .env file."}

    chunks = transcript_result.get("chunks", [])
    is_english = transcript_result.get("is_english", True)
    language_name = transcript_result.get("language_name", "English")
    duration = transcript_result.get("duration_minutes", 0)

    try:
        # Step 2: Translate if non-english
        if not is_english:
            translated_chunks = []
            for chunk in chunks:
                translated = translate_to_english(chunk, language_name)
                translated_chunks.append(translated)
            final_text = " ".join(translated_chunks)
        else:
            final_text = " ".join(chunks)

        # Step 3: If multiple chunks (long video), summarize each chunk first
        if len(chunks) > 1:
            final_text = summarize_long_video(chunks if is_english else translated_chunks, duration)

        # Step 4: Generate full structured summary
        result = generate_full_summary(final_text, duration)
        result["original_language"] = language_name
        result["was_translated"] = not is_english
        result["duration_minutes"] = duration

        return result

    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────
# 4. LONG VIDEO HANDLER
# ─────────────────────────────────────────

def summarize_long_video(chunks: list, duration: float) -> str:
    """
    For long videos: summarize each chunk separately,
    then merge all chunk summaries into one coherent text.
    """
    chunk_summaries = []

    for i, chunk in enumerate(chunks):
        prompt = f"""This is part {i+1} of {len(chunks)} of a long video transcript.
Summarize this part in 150-200 words, capturing the key points discussed.

TRANSCRIPT PART {i+1}:
{chunk}"""

        summary = call_groq(prompt, "You are an expert summarizer.")
        chunk_summaries.append(f"Part {i+1}: {summary}")

    # Now merge all chunk summaries
    merged = "\n\n".join(chunk_summaries)
    merge_prompt = f"""Below are summaries of different parts of a long video.
Combine them into one coherent, unified transcript summary of 400-500 words.
Remove redundancy, keep all key information.

PART SUMMARIES:
{merged}

Return a unified, flowing summary."""

    return call_groq(merge_prompt, "You are an expert summarizer.")


# ─────────────────────────────────────────
# 5. FULL SUMMARY GENERATOR (with highlights)
# ─────────────────────────────────────────

def generate_full_summary(text: str, duration: float) -> dict:
    """
    Generates all 4 sections of the summary with color highlight tags.
    Returns a dict with all sections.
    """

    system = """You are an expert video content summarizer.
Write clean, clear summaries in plain text only.
No special tags, no markdown, no formatting symbols.
Always respond in English."""

    prompt = f"""Analyze this video transcript and generate a complete structured summary.

TRANSCRIPT:
{text}

Generate your response in the following JSON format exactly:

{{
  "short_summary": "3-4 line overview of the entire video. Use highlight tags where appropriate.",
  
  "detailed_summary": "A thorough 200-300 word summary covering all major points discussed. Use [IMPORTANT], [CONCEPT], [ACTION], [STAT] tags generously to highlight key content.",
  
  "key_points": [
    "Point 1 with highlight tags where needed",
    "Point 2 with highlight tags where needed",
    "Point 3 with highlight tags where needed",
    "Point 4 with highlight tags where needed",
    "Point 5 with highlight tags where needed",
    "Point 6 with highlight tags where needed"
  ],
  
  "actionable_insights": [
    "Insight 1 — specific and practical, use [ACTION] tags",
    "Insight 2 — specific and practical",
    "Insight 3 — specific and practical",
    "Insight 4 — specific and practical",
    "Insight 5 — specific and practical"
  ],
  
  "mind_map_data": {{
    "central_topic": "Main topic of the video in 3-5 words (plain text only, no tags)",
    "branches": [
      {{
        "topic": "Branch 1 name (plain text only, no tags)",
        "subtopics": ["subtopic 1 plain text", "subtopic 2 plain text", "subtopic 3 plain text"]
      }},
      {{
        "topic": "Branch 2 name (plain text only, no tags)",
        "subtopics": ["subtopic 1 plain text", "subtopic 2 plain text", "subtopic 3 plain text"]
      }},
      {{
        "topic": "Branch 3 name (plain text only, no tags)",
        "subtopics": ["subtopic 1 plain text", "subtopic 2 plain text"]
      }},
      {{
        "topic": "Branch 4 name (plain text only, no tags)",
        "subtopics": ["subtopic 1 plain text", "subtopic 2 plain text"]
      }}
    ]
  }}

IMPORTANT: Use highlight tags ONLY in short_summary, detailed_summary, key_points, and actionable_insights.
The mind_map_data must contain plain text only — absolutely no [CONCEPT], [ACTION], [IMPORTANT], or [STAT] tags.
}}

Return ONLY the JSON. No extra text before or after."""

    raw = call_groq(prompt, system)

    # Parse JSON safely
    try:
        # Strip any markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        result = json.loads(clean)
        return result

    except json.JSONDecodeError:
        # Fallback: return raw text in short_summary if JSON parsing fails
        return {
            "short_summary": raw,
            "detailed_summary": "",
            "key_points": [],
            "actionable_insights": [],
            "mind_map_data": {"central_topic": "Video Summary", "branches": []}
        }