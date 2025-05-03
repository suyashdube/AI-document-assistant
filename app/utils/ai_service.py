import os
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid

from ..models.ai_operations import AIOperationType
from ..models.documents import DocumentSensitivity
from ..ai_controls import (
    prompt_filtering,
    rag_protection,
    external_access_control,
    response_enforcement
)

load_dotenv()

class AIService:
    """
    Integrates LangChain with the four-perimeter framework for secure AI operations.
    """
    
    def __init__(self):
        # Initialize OpenAI client
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Use ChatOpenAI instead of OpenAI for better compatibility
        try:
            self.llm = ChatOpenAI(
                api_key=self.openai_api_key, 
                temperature=0.1,
                max_tokens=1000,
                model_name="gpt-3.5-turbo"
            )
            print("Initialized ChatOpenAI successfully")
        except Exception as e:
            print(f"Error initializing ChatOpenAI: {e}")
            # Fallback to a mock LLM for development
            from langchain.llms.fake import FakeListLLM
            self.llm = FakeListLLM(responses=["This is a mock response for development"])
            print("Using FakeListLLM as fallback")
        
        # Initialize embeddings with try/catch
        try:
            self.embeddings = OpenAIEmbeddings(api_key=self.openai_api_key)
            print("Initialized OpenAIEmbeddings successfully")
        except Exception as e:
            print(f"Error initializing OpenAIEmbeddings: {e}")
            # For development, we can continue without embeddings
            self.embeddings = None
        
        # Document index (would be a proper database in production)
        self._documents = {}
        
        # Simple in-memory vector store for RAG
        self._vector_store = None
        
    async def process_document(
        self,
        user: Dict[str, Any],
        document_content: str,
        document_name: str,
        document_type: str,
        sensitivity: str = "internal"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process a new document: store, embed, and index it.
        """
        # Create document ID
        doc_id = str(uuid.uuid4())
        
        # Store the document
        self._documents[doc_id] = {
            "id": doc_id,
            "name": document_name,
            "type": document_type,
            "sensitivity": sensitivity,
            "content": document_content,
            "owner_id": user.get("id", "unknown")
        }
        
        # Only proceed with embeddings if the embeddings object is available
        if self.embeddings is not None:
            try:
                # Split text into chunks for embedding
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                chunks = text_splitter.split_text(document_content)
                
                # Create Document objects for the vector store
                docs = [
                    Document(
                        page_content=chunk,
                        metadata={
                            "id": doc_id,
                            "name": document_name,
                            "type": document_type,
                            "sensitivity": sensitivity,
                            "owner_id": user.get("id", "unknown")
                        }
                    )
                    for chunk in chunks
                ]
                
                # Create or update the vector store
                if self._vector_store is None:
                    self._vector_store = FAISS.from_documents(docs, self.embeddings)
                else:
                    self._vector_store.add_documents(docs)
                
                return doc_id, {
                    "chunks": len(chunks),
                    "embedding_dimensions": 1536  # OpenAI embedding dimensions
                }
            except Exception as e:
                print(f"Error embedding document: {e}")
                # Continue without embedding
        
        # If we don't have embeddings or an error occurred, just return the doc ID
        return doc_id, {
            "chunks": 0,
            "embedding_dimensions": 0,
            "note": "Document stored without embeddings (development mode)"
        }
    
    async def execute_ai_operation(
        self,
        user: Dict[str, Any],
        operation_type: AIOperationType,
        document_ids: List[str],
        prompt: str,
        ai_agent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an AI operation with the full four-perimeter framework.
        
        Args:
            user: User requesting the operation
            operation_type: Type of operation to perform
            document_ids: IDs of documents to use
            prompt: User's prompt text
            ai_agent: Optional AI agent identity
            
        Returns:
            Operation result with metadata
        """
        # Ensure we have an AI agent identity
        if ai_agent is None:
            ai_agent = {
                "key": "default_ai_agent",
                "role": "ai_agent"
            }
        
        log = {
            "operation_id": str(uuid.uuid4()),
            "user_id": user.get("id", "unknown"),
            "operation_type": operation_type,
            "document_ids": document_ids,
            "success": False,
            "perimeters": {}
        }
        
        try:
            # Get document info for all requested documents
            docs_info = []
            for doc_id in document_ids:
                if doc_id in self._documents:
                    docs_info.append(self._documents[doc_id])
            
            if not docs_info:
                return {
                    "error": "No valid documents found",
                    "log": log
                }
            
            # Get sensitivity and document type for the first document (for simplified demo)
            doc_sensitivity = docs_info[0]["sensitivity"]
            doc_type = docs_info[0]["type"]
            
            # PERIMETER 1: Prompt Filtering
            is_permitted, filtered_prompt, prompt_context = await prompt_filtering.filter_prompt(
                user=user,
                prompt=prompt,
                operation_type=operation_type,
                document_type=doc_type,
                document_sensitivity=doc_sensitivity
            )
            
            log["perimeters"]["prompt_filtering"] = {
                "passed": is_permitted,
                "context": prompt_context
            }
            
            if not is_permitted:
                return {
                    "error": filtered_prompt,  # Contains the error message
                    "log": log
                }
            
            # PERIMETER 2: RAG Protection - Pre-query filtering
            filtered_doc_ids, rag_pre_context = await rag_protection.pre_query_filter(
                user=user,
                document_ids=document_ids,
                operation_type=operation_type
            )
            
            log["perimeters"]["rag_pre_query"] = {
                "passed": len(filtered_doc_ids) > 0,
                "context": rag_pre_context
            }
            
            if not filtered_doc_ids:
                return {
                    "error": "No documents available with your permissions",
                    "log": log
                }
            
            # Retrieve content for the filtered documents
            filtered_docs_info = []
            for doc_id in filtered_doc_ids:
                if doc_id in self._documents:
                    filtered_docs_info.append(self._documents[doc_id])
            
            # PERIMETER 2: RAG Protection - Post-query filtering
            filtered_docs, rag_post_context = await rag_protection.post_query_filter(
                user=user,
                query_results=filtered_docs_info,
                operation_type=operation_type
            )
            
            log["perimeters"]["rag_post_query"] = {
                "passed": True,
                "context": rag_post_context
            }
            
            # For operations requiring external access (e.g., API calls),
            # check with the third perimeter
            if operation_type in [AIOperationType.ANALYZE, AIOperationType.TRANSLATE]:
                # PERIMETER 3: External Access Control
                external_access, operation_id, ext_context = await external_access_control.check_external_access(
                    user=user,
                    ai_agent=ai_agent,
                    external_system=f"{operation_type}_service",
                    operation=operation_type,
                    context={
                        "document_ids": filtered_doc_ids,
                        "document_sensitivity": doc_sensitivity
                    }
                )
                
                log["perimeters"]["external_access"] = {
                    "passed": external_access,
                    "context": ext_context,
                    "operation_id": operation_id
                }
                
                if not external_access:
                    if operation_id:
                        return {
                            "status": "pending_approval",
                            "message": "This operation requires approval",
                            "operation_id": operation_id,
                            "log": log
                        }
                    else:
                        return {
                            "error": "External access denied",
                            "log": log
                        }
            
            # At this point, all perimeters have cleared for the operation
            # Prepare the RAG context and generate the AI response
            
            # Combine document contents
            combined_content = "\n\n".join([doc["content"] for doc in filtered_docs])
            
            # Create chat prompt template (update this section)
            system_template = f"You are an AI assistant helping with {operation_type} operations on documents."
            system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
            
            human_template = """Documents provided:
{context}

User query: {query}

Please provide a detailed response that addresses the user's query.
"""
            human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
            
            chat_prompt = ChatPromptTemplate.from_messages([
                system_message_prompt,
                human_message_prompt
            ])
            
            # Create the chain with ChatPromptTemplate
            chain = LLMChain(prompt=chat_prompt, llm=self.llm)
            
            # Run the chain with the appropriate inputs
            response = chain.run(context=combined_content, query=filtered_prompt)
            
            # PERIMETER 4: Response Enforcement
            filtered_response, resp_context = await response_enforcement.filter_response(
                user=user,
                original_response=response,
                operation_type=operation_type,
                document_ids=filtered_doc_ids,
                context={}
            )
            
            log["perimeters"]["response_enforcement"] = {
                "passed": True,
                "context": resp_context
            }
            
            # Operation succeeded
            log["success"] = True
            
            return {
                "operation_id": log["operation_id"],
                "response": filtered_response,
                "log": log
            }
            
        except Exception as e:
            log["error"] = str(e)
            return {
                "error": f"Error processing operation: {str(e)}",
                "log": log
            }
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)
    
    def get_document_ids(self) -> List[str]:
        """Get all document IDs."""
        return list(self._documents.keys())

# Export singleton instance
ai_service = AIService() 