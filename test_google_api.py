#!/usr/bin/env python3
"""
Test Google API key loading and connectivity
"""
import os
import sys
from dotenv import load_dotenv

# Load environment from the correct location
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
print(f"Loading .env from: {env_path}")
print(f".env file exists: {os.path.exists(env_path)}")

load_dotenv(env_path)

# Test API key
api_key = os.getenv("GOOGLE_API_KEY")
print(f"GOOGLE_API_KEY loaded: {bool(api_key)}")
if api_key:
    print(f"API key preview: {api_key[:10]}...{api_key[-4:]}")

# Test Google API connectivity
if api_key:
    print("\n🧪 Testing Google API connectivity...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Test with a simple call
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello, test message")
        print("✅ Google API connection successful!")
        print(f"Response: {response.text[:50]}...")
        
    except Exception as e:
        print(f"❌ Google API connection failed: {e}")

# Test LangChain Google integration
if api_key:
    print("\n🧪 Testing LangChain Google integration...")
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        
        # Test chat model
        chat_model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.1
        )
        response = chat_model.invoke("Hello test")
        print("✅ LangChain ChatGoogleGenerativeAI successful!")
        print(f"Response: {response.content[:50]}...")
        
        # Test embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        embed_result = embeddings.embed_query("test query")
        print(f"✅ LangChain GoogleGenerativeAIEmbeddings successful! Embedding size: {len(embed_result)}")
        
    except Exception as e:
        print(f"❌ LangChain Google integration failed: {e}")
