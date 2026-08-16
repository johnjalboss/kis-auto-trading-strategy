"""
Test Gemini 2.0 Flash generation
"""
import os
import config
from loguru import logger

api_key = getattr(config, 'GEMINI_API_KEY', '')
print("Testing Gemini API Key present:", bool(api_key))

if api_key:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    for model_name in ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]:
        try:
            m = genai.GenerativeModel(model_name)
            resp = m.generate_content("Say hello to the quant master in 1 sentence in Korean.")
            print(f"✅ Model [{model_name}] Response: {resp.text.strip()}")
            break
        except Exception as e:
            print(f"⚠️ Model [{model_name}] error: {e}")
