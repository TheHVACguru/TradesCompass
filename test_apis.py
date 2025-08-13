#!/usr/bin/env python3
"""
Test script to verify RapidAPI subscriptions and API availability
"""

import os
import requests
import json

def test_rapidapi_key():
    """Test if RapidAPI key is configured"""
    api_key = os.environ.get('RAPIDAPI_KEY')
    if not api_key:
        print("❌ RAPIDAPI_KEY not found in environment variables")
        return False
    print(f"✅ RAPIDAPI_KEY found: {api_key[:10]}...")
    return True

def test_x_twitter_api():
    """Test X/Twitter API access"""
    api_key = os.environ.get('RAPIDAPI_KEY')
    if not api_key:
        return False
    
    print("\n📱 Testing X/Twitter API...")
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'twitter-api45.p.rapidapi.com'
    }
    params = {
        'query': 'test',
        'count': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ X/Twitter API is working!")
            return True
        elif response.status_code == 403:
            print("   ❌ 403 Forbidden - You need to subscribe to this API on RapidAPI")
            print("   👉 Visit: https://rapidapi.com/omarmhaimdat/api/twitter-api45")
        elif response.status_code == 429:
            print("   ⚠️ 429 Rate Limit - API quota exceeded or subscription limit reached")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Connection error: {str(e)}")
    return False

def test_linkedin_api():
    """Test LinkedIn API access"""
    api_key = os.environ.get('RAPIDAPI_KEY')
    if not api_key:
        return False
    
    print("\n💼 Testing LinkedIn API...")
    url = "https://linkedin-profiles-and-company-data.p.rapidapi.com/search-profiles"
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'linkedin-profiles-and-company-data.p.rapidapi.com'
    }
    params = {
        'keywords': 'software engineer',
        'limit': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ LinkedIn API is working!")
            return True
        elif response.status_code == 403:
            print("   ❌ 403 Forbidden - You need to subscribe to this API on RapidAPI")
            print("   👉 Visit: https://rapidapi.com/rockapis-rockapis-default/api/linkedin-profiles-and-company-data")
        elif response.status_code == 404:
            print("   ❌ 404 Not Found - API endpoint may have changed or require subscription")
        elif response.status_code == 429:
            print("   ⚠️ 429 Rate Limit - API quota exceeded or subscription limit reached")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Connection error: {str(e)}")
    return False

def test_alternative_apis():
    """Suggest alternative APIs that might work"""
    api_key = os.environ.get('RAPIDAPI_KEY')
    if not api_key:
        return
    
    print("\n🔍 Testing Alternative APIs...")
    
    # Test a simple free API to verify RapidAPI key works
    print("\n   Testing Chuck Norris Jokes API (Free tier)...")
    url = "https://matchilling-chuck-norris-jokes-v1.p.rapidapi.com/jokes/random"
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'matchilling-chuck-norris-jokes-v1.p.rapidapi.com'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("   ✅ Your RapidAPI key is valid and working!")
        else:
            print(f"   ❌ RapidAPI key might be invalid. Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing API key: {str(e)}")

def main():
    print("=" * 60)
    print("RapidAPI Integration Test for Candidate Sourcing")
    print("=" * 60)
    
    # Test API key
    if not test_rapidapi_key():
        print("\n⚠️ Please set your RAPIDAPI_KEY environment variable first")
        return
    
    # Test each API
    x_works = test_x_twitter_api()
    linkedin_works = test_linkedin_api()
    
    # Test if key is valid
    test_alternative_apis()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if x_works and linkedin_works:
        print("✅ All APIs are working! You can search for candidates.")
    elif not x_works and not linkedin_works:
        print("❌ No APIs are accessible. You need to subscribe to these APIs on RapidAPI:")
        print("\n1. Twitter/X API:")
        print("   https://rapidapi.com/omarmhaimdat/api/twitter-api45")
        print("\n2. LinkedIn API:")
        print("   https://rapidapi.com/rockapis-rockapis-default/api/linkedin-profiles-and-company-data")
        print("\n💡 TIP: Many APIs offer free tiers with limited requests per month.")
    else:
        if x_works:
            print("✅ X/Twitter API is working")
        else:
            print("❌ X/Twitter API needs subscription")
            
        if linkedin_works:
            print("✅ LinkedIn API is working")
        else:
            print("❌ LinkedIn API needs subscription")
    
    print("\n📚 To subscribe to an API:")
    print("1. Visit the API page on RapidAPI")
    print("2. Click 'Subscribe to Test'")
    print("3. Choose a plan (many have free tiers)")
    print("4. The API will be added to your account")

if __name__ == "__main__":
    main()