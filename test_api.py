import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_add_experience():
    print("Testing add experience endpoint...")
    data = {
        "text": "Led a team of 5 developers to build a scalable microservices architecture using Python and Docker, resulting in 40% improved system performance.",
        "company": "TechCorp",
        "role": "Senior Developer",
        "duration": "Jan 2020 - Dec 2022"
    }
    response = requests.post(f"{BASE_URL}/api/experiences/", json=data)
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    return response.json().get("id")

def test_list_experiences():
    print("Testing list experiences endpoint...")
    response = requests.get(f"{BASE_URL}/api/experiences/")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_get_experience(experience_id):
    print(f"Testing get experience endpoint for ID: {experience_id}...")
    response = requests.get(f"{BASE_URL}/api/experiences/{experience_id}")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_search_experiences():
    print("Testing search experiences endpoint...")
    response = requests.get(f"{BASE_URL}/api/experiences/search/?query=python")
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_match_job():
    print("Testing match job endpoint...")
    data = {
        "url": "https://www.linkedin.com/jobs/view/example-job"
    }
    response = requests.post(f"{BASE_URL}/api/jobs/match", json=data)
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_delete_experience(experience_id):
    print(f"Testing delete experience endpoint for ID: {experience_id}...")
    response = requests.delete(f"{BASE_URL}/api/experiences/{experience_id}")
    print(f"Status code: {response.status_code}")
    if response.status_code == 204:
        print("Experience successfully deleted")
    else:
        print(f"Response: {response.text}")
    print()

def main():
    print("Starting API tests...\n")
    
    # Test basic health endpoint
    test_health()
    
    # Test experience endpoints
    experience_id = test_add_experience()
    time.sleep(1)  # Small delay to ensure processing
    
    test_list_experiences()
    
    if experience_id:
        test_get_experience(experience_id)
    
    test_search_experiences()
    
    # Test job endpoints
    test_match_job()
    
    # Test delete endpoint
    if experience_id:
        test_delete_experience(experience_id)
        
    print("All tests completed!")

if __name__ == "__main__":
    main()