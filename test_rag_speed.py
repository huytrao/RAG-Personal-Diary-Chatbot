#!/usr/bin/env python3
"""
Test script to check RAG response speed
"""
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8001"

def test_fast_mode():
    """Test generate_fast_response"""
    print("🧪 Testing FAST MODE...")
    start_time = time.time()
    
    try:
        response = requests.get(
            f"{BASE_URL}/users/1/query",
            params={
                "query": "hello",
                "fast_mode": True,
                "chat_history": "[]"
            },
            timeout=60  # 60 second timeout
        )
        
        elapsed = time.time() - start_time
        print(f"⏱️  Fast mode took: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Fast mode SUCCESS")
            print(f"📝 Response: {result.get('response', '')[:100]}...")
            print(f"⚡ Processing time: {result.get('processing_time', 0):.2f}s")
            return True
        else:
            print(f"❌ Fast mode FAILED: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⏰ Fast mode TIMEOUT after {elapsed:.2f} seconds")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"💥 Fast mode ERROR after {elapsed:.2f} seconds: {e}")
        return False

def test_contextual_mode():
    """Test generate_contextual_response"""
    print("\n🧪 Testing CONTEXTUAL MODE...")
    start_time = time.time()
    
    try:
        chat_history = json.dumps([
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello! How can I help you?"}
        ])
        
        response = requests.get(
            f"{BASE_URL}/users/1/query",
            params={
                "query": "tell me about my day",
                "fast_mode": False,
                "chat_history": chat_history
            },
            timeout=60  # 60 second timeout
        )
        
        elapsed = time.time() - start_time
        print(f"⏱️  Contextual mode took: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Contextual mode SUCCESS")
            print(f"📝 Response: {result.get('response', '')[:100]}...")
            print(f"⚡ Processing time: {result.get('processing_time', 0):.2f}s")
            return True
        else:
            print(f"❌ Contextual mode FAILED: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⏰ Contextual mode TIMEOUT after {elapsed:.2f} seconds")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"💥 Contextual mode ERROR after {elapsed:.2f} seconds: {e}")
        return False

def test_health():
    """Test if service is running"""
    print("🏥 Testing service health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is healthy")
            return True
        else:
            print(f"❌ Service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"💥 Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting RAG Speed Test\n")
    
    # Test service health first
    if not test_health():
        print("❌ Service is not running. Please start the RAG service first.")
        exit(1)
    
    print("\n" + "="*50)
    
    # Test both modes
    fast_success = test_fast_mode()
    contextual_success = test_contextual_mode()
    
    print("\n" + "="*50)
    print("📊 TEST SUMMARY:")
    print(f"Fast Mode: {'✅ PASS' if fast_success else '❌ FAIL'}")
    print(f"Contextual Mode: {'✅ PASS' if contextual_success else '❌ FAIL'}")
    
    if not fast_success and not contextual_success:
        print("\n💡 Both modes failed - check RAG system setup")
    elif fast_success and not contextual_success:
        print("\n💡 Fast mode works, contextual mode has issues")
    elif not fast_success and contextual_success:
        print("\n💡 Contextual mode works, fast mode has issues")
    else:
        print("\n🎉 Both modes working!")
