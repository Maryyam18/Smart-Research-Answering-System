

import requests
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"[Autocorrect] GEMINI_API_KEY loaded: {GEMINI_API_KEY[:20] + '...' if GEMINI_API_KEY else 'NOT FOUND'}")


def gemini_autocorrect(query: str) -> str:
    """
    Sends a prompt to Gemini to autocorrect spelling, grammar, and informal words.
    
    Args:
        query (str): User's input query with potential spelling/grammar errors
        
    Returns:
        str: Corrected query, or original query if correction fails
    """
    if not GEMINI_API_KEY:
        print("[WARNING] GEMINI_API_KEY not set. Skipping autocorrect.")
        return query

    prompt = f"Correct spelling and grammar: '{query}' Return ONLY the corrected text."

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 100
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"

    try:
        print(f"\n[Gemini] Attempting correction for: '{query}'")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            corrected = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"[Gemini]  Corrected: '{corrected}'")
            return corrected
        else:
            error_msg = response.json().get("error", {}).get("message", response.text)
            print(f"[Gemini]  ERROR ({response.status_code}): {error_msg}")
            return query

    except Exception as e:
        print(f"[Gemini]  Exception: {type(e).__name__}: {str(e)}")
        return query


def debug_gemini_autocorrect(query: str) -> dict:
    """
    Debug function to test Gemini autocorrect and return raw response.
    Useful for troubleshooting.
    
    Args:
        query (str): User's input query
        
    Returns:
        dict: Contains raw_response and extracted_corrected text
    """
    if not GEMINI_URL or not GEMINI_API_KEY:
        return {"error": "GEMINI_URL or GEMINI_API_KEY not set"}

    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    prompt = f"Correct spelling and grammar: '{query}' Return ONLY the corrected text."
    
    payload = {
        "temperature": 0,
        "maxOutputTokens": 64,
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"HTTP error: {e}"}

    corrected = None
    if "candidates" in data and data["candidates"]:
        try:
            corrected = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    return {
        "raw_response": data,
        "extracted_corrected": corrected or ""
    }