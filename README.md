# AI Document Assistant with Permit.io Access Controls

An AI-powered document assistant that uses Permit.io to implement comprehensive AI access controls. This application demonstrates the Four-Perimeter Framework for AI security.

## Features

- **Document Management**: Upload, list, and manage documents with fine-grained access controls
- **AI Operations**: Summarize, extract, analyze, and query documents using AI
- **Four-Perimeter AI Security Framework**:
  1. **Prompt Filtering**: Validate and authorize prompts before they reach the AI model
  2. **RAG Data Protection**: Secure control of knowledge base access for AI agents
  3. **External Access Control**: Manage AI agent access to external systems with approval workflows
  4. **Response Enforcement**: Filter and control AI-generated responses

## Architecture

This application is built with:

- **FastAPI**: For the backend API
- **LangChain**: For AI operations and document processing
- **Permit.io**: For implementing the Four-Perimeter Framework
- **OpenAI**: For LLM capabilities

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker (for running Permit.io PDP)
- OpenAI API key
- Permit.io API key

### Installation

1. Clone the repository

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and configure your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. Start the Permit.io Policy Decision Point (PDP) with Docker:
   ```bash
   docker run -p 7766:7000 \
     --env PDP_API_KEY=your_permit_api_key \
     --env PDP_DEBUG=true \
     permitio/pdp-v2:latest
   ```

5. Run the application:
   ```bash
   python run.py
   ```

6. Access the API documentation at http://localhost:8000/docs

## Test Users and Development Mode

For testing purposes, the application includes three mock users with different permission levels:

| Email | Password | Role | Subscription Tier |
|-------|----------|------|------------------|
| admin@example.com | password | admin | enterprise |
| premium@example.com | password | premium | premium |
| basic@example.com | password | free | basic |

In development mode, the application includes special handling:

1. **OpenAI Fallback**: If OpenAI API credentials are missing or invalid, the system uses mock responses
2. **Embeddings**: Document embeddings are optional in development mode
3. **Admin Permissions**: Admin users automatically get permission to perform most operations
4. **External Access Control**: Certain high-risk operations (analyze, translate) are still blocked by design

## The Four-Perimeter Framework Explained

The application implements Permit.io's Four-Perimeter Framework for AI security:

### 1. Prompt Filtering

This perimeter validates and authorizes prompts before they reach the AI model:
- Detect potentially harmful content patterns
- Verify user permissions for specific operations
- Apply length and content restrictions based on user roles

### 2. RAG Data Protection

This perimeter controls what data the AI can access:
- Pre-query filtering to control which documents can be retrieved
- Post-query filtering to sanitize data before it's processed by the AI
- Permission checks based on document sensitivity and user role

### 3. External Access Control

This perimeter manages AI agent interactions with external systems:
- Assign machine identities to AI agents
- Control which API calls and operations are authorized
- Implement human-in-the-loop approvals for sensitive operations

**Note**: Even admin users will receive "External Access Denied" errors for operations like "analyze" and "translate" by design. This demonstrates the separation of duties principle, where high-risk operations require explicit approval from a different authority, regardless of the user's role.

### 4. Response Enforcement

This perimeter controls AI-generated responses:
- Detect and redact sensitive information in outputs
- Apply different visibility rules based on user role
- Ensure compliance with legal and organizational policies

## Testing All Endpoints

The application includes a test script that can be used to test all endpoints with different user roles:

```bash
# Test with admin user
python test_endpoints.py admin

# Test with premium user
python test_endpoints.py premium

# Test with basic user
python test_endpoints.py basic
```

Expected behavior:
- Admin users can perform most operations but will be blocked from external API operations
- Premium and basic users will have different levels of access based on their roles
- The test script provides clear feedback on which operations succeeded or failed

## API Endpoints

### Authentication
- `POST /auth/token`: Get an access token
- `GET /auth/me`: Get current user info

### Documents
- `POST /documents/`: Upload a document
- `GET /documents/`: List accessible documents
- `GET /documents/{document_id}`: Get document details

### AI Operations
- `POST /ai/prompt`: Execute an AI operation with a prompt
- `GET /ai/approvals`: List pending approval requests
- `POST /ai/approvals/{operation_id}/approve`: Approve an operation
- `POST /ai/approvals/{operation_id}/reject`: Reject an operation

## Common Issues and Troubleshooting

- **401 Unauthorized**: Check your credentials and ensure you're using a valid token
- **403 Forbidden**: The user doesn't have permission for this operation
- **"External Access Denied"**: Operations that require external API access (like analyze/translate) are blocked by design, even for admins
- **OpenAI API Issues**: If you don't have valid OpenAI credentials, the system will use mock responses


## Acknowledgments

- [Permit.io](https://permit.io) for the Four-Perimeter Framework
- [LangChain](https://langchain.com) for AI capabilities
- [FastAPI](https://fastapi.tiangolo.com) for the API framework
- [OpenAI](https://openai.com) for the language models 
