from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import os
import io
import json
import docx
import PyPDF2
import httpx
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Union, Dict

# Load the GROQ_API_KEY from environment variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Initialize FastAPI app
app = FastAPI(
    title="Arabic Resume Extractor",
    description="An API to extract structured data from Arabic resumes using Groq's LLaMA 3.1.",
    version="1.0.0"
)

# --- CORS Middleware ---
# This allows the frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Pydantic Models ---
class ExtractedField(BaseModel):
    field_name: str
    value: Union[str, List[Dict[str, str]]]
    confidence_score: float

class ExtractionResponse(BaseModel):
    extracted_data: List[ExtractedField]

# --- API Endpoint ---
@app.post("/extract/", response_model=ExtractionResponse)
async def extract_resume_data(resume_file: UploadFile = File(...)):
    """
    Receives an Arabic resume file and returns extracted structured data.
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable not set.")

    # Determine the file type and extract text accordingly
    file_content = await resume_file.read()

    try:
        if resume_file.filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(file_content))
            resume_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        elif resume_file.filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            resume_text = ""
            for page in pdf_reader.pages:
                resume_text += page.extract_text() or ""
        elif resume_file.filename.endswith(".txt"):
             resume_text = file_content.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .docx, .pdf, or .txt file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process the file: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the uploaded file.")

    # The fields to be extracted, as requested by the user.
    fields_to_extract = [
        "Name",
        "Email",
        "Phone",
        "Skills",
        "Experience (roles, companies, duration)",
        "Certificates",
        "Domain (primary area of expertise, e.g., IT, Healthcare, Finance)"
    ]

    prompt = f"""
    Please extract the following fields from the Arabic resume text provided below.
    For each field, provide the extracted value and a confidence score from 0.0 to 1.0.
    The fields to extract are: {', '.join(fields_to_extract)}.

    Resume Text:
    ---
    {resume_text}
    ---

    Return the output as a JSON array, where each object has 'field_name', 'value', and 'confidence_score' keys.
    """

    request_body = {
        "model": "meta-llama/llama-4-maverick-17b-128e-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert AI assistant specialized in extracting structured information from Arabic resumes."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature":1,
        "max_tokens": 2048,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=request_body,
                timeout=30.0
            )
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            api_response = response.json()

            # Extract the content string from the API response
            extracted_content_str = api_response['choices'][0]['message']['content']

            # Clean the response string by removing Markdown code block syntax
            if extracted_content_str.startswith("```json"):
                extracted_content_str = extracted_content_str[7:]
            if extracted_content_str.endswith("```"):
                extracted_content_str = extracted_content_str[:-3]
            extracted_content_str = extracted_content_str.strip()

            # Parse the JSON string into a Python list of dictionaries
            try:
                extracted_data_list = json.loads(extracted_content_str)

                # Convert the list of dictionaries into a list of Pydantic models
                extracted_data = [ExtractedField(**item) for item in extracted_data_list]

                return ExtractionResponse(extracted_data=extracted_data)

            except (json.JSONDecodeError, TypeError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse the response from Groq API. Raw response: {extracted_content_str}"
                )

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error from Groq API: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    return {"status": "Arabic Resume Extractor API is running."}

# --- Serve Frontend ---
# This mounts the 'frontend' directory, making its files accessible from the server.
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")

# To run this application:
# 1. Install dependencies: pip install -r requirements.txt
# 2. Set the environment variable: export GROQ_API_KEY='your_groq_api_key'
# 3. Run the server: uvicorn main:app --reload