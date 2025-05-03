#!/usr/bin/env python3
import requests
import json
import os
import sys
from pprint import pprint

# API base URL
BASE_URL = "http://localhost:8000"

# Test users
USERS = {
    "admin": {"username": "admin@example.com", "password": "password"},
    "premium": {"username": "premium@example.com", "password": "password"},
    "basic": {"username": "basic@example.com", "password": "password"}
}

class APITester:
    def __init__(self, base_url, user_type="admin"):
        self.base_url = base_url
        self.user_type = user_type
        self.token = None
        self.headers = {}
        self.document_id = None
    
    def authenticate(self):
        """Authenticate with the API and get token"""
        auth_url = f"{self.base_url}/auth/token"
        
        # Get credentials for the selected user type
        credentials = USERS.get(self.user_type)
        if not credentials:
            print(f"Error: User type '{self.user_type}' not found")
            sys.exit(1)
        
        # Prepare form data for OAuth2 authentication
        data = {
            "username": credentials["username"],
            "password": credentials["password"]
        }
        
        print(f"\n🔐 Authenticating as {credentials['username']}...")
        response = requests.post(auth_url, data=data)
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print(f"✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            sys.exit(1)
    
    def get_user_info(self):
        """Test the /auth/me endpoint"""
        me_url = f"{self.base_url}/auth/me"
        
        print("\n🧑 Getting user information...")
        response = requests.get(me_url, headers=self.headers)
        
        if response.status_code == 200:
            print(f"✅ User info retrieved successfully")
            pprint(response.json())
        else:
            print(f"❌ Failed to get user info: {response.status_code} - {response.text}")
    
    def upload_document(self, file_path):
        """Test document upload endpoint"""
        upload_url = f"{self.base_url}/documents/"
        
        print(f"\n📄 Uploading document: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
        
        # Prepare file and form data
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            data = {'sensitivity': 'internal'}
            
            response = requests.post(
                upload_url, 
                headers=self.headers, 
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            result = response.json()
            self.document_id = result.get("id")
            print(f"✅ Document uploaded successfully. Document ID: {self.document_id}")
            pprint(result)
        else:
            print(f"❌ Document upload failed: {response.status_code} - {response.text}")
    
    def list_documents(self):
        """Test document listing endpoint"""
        list_url = f"{self.base_url}/documents/"
        
        print("\n📋 Listing documents...")
        response = requests.get(list_url, headers=self.headers)
        
        if response.status_code == 200:
            documents = response.json()
            print(f"✅ Retrieved {len(documents)} documents")
            for doc in documents:
                print(f"  - {doc.get('name')} (ID: {doc.get('id')})")
        else:
            print(f"❌ Failed to list documents: {response.status_code} - {response.text}")
    
    def get_document(self, document_id=None, include_content=False):
        """Test get document endpoint"""
        doc_id = document_id or self.document_id
        
        if not doc_id:
            print("❌ No document ID provided and no document has been uploaded")
            return
        
        get_url = f"{self.base_url}/documents/{doc_id}"
        params = {"include_content": str(include_content).lower()}
        
        print(f"\n📑 Getting document {doc_id} (include_content={include_content})...")
        response = requests.get(get_url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            doc = response.json()
            print(f"✅ Document retrieved successfully")
            if "content" in doc:
                # Truncate content in display to avoid too much output
                content_preview = doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"]
                doc_info = {**doc, "content": content_preview}
                pprint(doc_info)
            else:
                pprint(doc)
        else:
            print(f"❌ Failed to get document: {response.status_code} - {response.text}")
    
    def execute_ai_prompt(self, operation_type="summarize", prompt="Summarize this document"):
        """Test AI prompt execution endpoint"""
        if not self.document_id:
            print("❌ No document ID available. Upload a document first.")
            return
        
        prompt_url = f"{self.base_url}/ai/prompt"
        
        payload = {
            "document_id": self.document_id,
            "operation_type": operation_type,
            "prompt": prompt,
            "parameters": {}
        }
        
        print(f"\n🤖 Executing AI prompt ({operation_type}): {prompt}")
        response = requests.post(prompt_url, headers=self.headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ AI operation executed successfully")
            if "response" in result:
                print("\nAI Response:")
                print("------------")
                print(result["response"])
                print("------------")
            else:
                pprint(result)
        else:
            print(f"❌ AI operation failed: {response.status_code} - {response.text}")
    
    def run_all_tests(self, file_path):
        """Run all API tests in sequence"""
        self.authenticate()
        self.get_user_info()
        self.upload_document(file_path)
        self.list_documents()
        self.get_document(include_content=False)
        self.get_document(include_content=True)
        
        # AI operations tests
        operations = [
            ("summarize", "Summarize this document in 3 bullet points"),
            ("extract", "Extract the key concepts about the Four-Perimeter Framework"),
            ("analyze", "Analyze the structure of this document"),
            ("translate", "Translate this document to Spanish"),
            ("answer", "What is the Four-Perimeter Framework?")
        ]
        
        for op_type, prompt in operations:
            self.execute_ai_prompt(op_type, prompt)

if __name__ == "__main__":
    # Check if user type is provided as command line argument
    user_type = sys.argv[1] if len(sys.argv) > 1 else "admin"
    
    # Check if file path is provided
    file_path = sys.argv[2] if len(sys.argv) > 2 else "test_document.txt"
    
    print(f"🚀 Starting API tests with user '{user_type}' and file '{file_path}'")
    
    tester = APITester(BASE_URL, user_type)
    tester.run_all_tests(file_path) 