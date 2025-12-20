

import requests
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def gemini_autocorrect(query: str) -> str:
    """
    Uses LangChain ChatGoogleGenerativeAI for autocorrection
    """
    try:
        print(f"\n[Gemini] Attempting correction for: '{query}'")
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite"
        )
        
        prompt = f"Correct spelling and grammar: '{query}' Return ONLY the corrected text."
        response = llm.invoke(prompt)
        corrected = response.content.strip()
        
        print(f"[Gemini] Corrected: '{corrected}'")
        return corrected
        
    except Exception as e:
        print(f"[Gemini] Exception: {type(e).__name__}: {str(e)}")
        return query


# def debug_gemini_autocorrect(query: str) -> dict:
#     """
#     Debug function to test Gemini autocorrect and return raw response.
#     Useful for troubleshooting.
    
#     Args:
#         query (str): User's input query
        
#     Returns:
#         dict: Contains raw_response and extracted_corrected text
#     """
#     if not GEMINI_URL or not GEMINI_API_KEY:
#         return {"error": "GEMINI_URL or GEMINI_API_KEY not set"}

#     url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
#     prompt = f"Correct spelling and grammar: '{query}' Return ONLY the corrected text."
    
#     payload = {
#         "temperature": 0,
#         "maxOutputTokens": 64,
#         "contents": [
#             {"role": "user", "parts": [{"text": prompt}]}
#         ]
#     }
#     headers = {"Content-Type": "application/json"}

#     try:
#         resp = requests.post(url, headers=headers, json=payload, timeout=10)
#         resp.raise_for_status()
#         data = resp.json()
#     except Exception as e:
#         return {"error": f"HTTP error: {e}"}

#     corrected = None
#     if "candidates" in data and data["candidates"]:
#         try:
#             corrected = data["candidates"][0]["content"]["parts"][0]["text"].strip()
#         except Exception:
#             pass

#     return {
#         "raw_response": data,
#         "extracted_corrected": corrected or ""
#     }