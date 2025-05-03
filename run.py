import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get host and port from environment variables or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Run FastAPI app with uvicorn
    uvicorn.run(
        "app.api.main:app", 
        host=host, 
        port=port, 
        reload=True
    ) 