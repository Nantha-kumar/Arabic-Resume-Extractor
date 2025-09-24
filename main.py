# Fixed Arabic Resume Extractor API

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
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Union, Dict, Any

# Load the GROQ_API_KEY from environment variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Initialize FastAPI app
app = FastAPI(
    title="Arabic Resume Extractor",
    description="An API to extract structured data from Arabic resumes using Groq's LLaMA 3.1.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Fixed Pydantic Models ---
class ExtractedField(BaseModel):
    field_name: str
    value: Union[str, List[str]]  # Simplified to handle string lists properly
#    confidence_score: float

    # @field_validator('confidence_score')
    # @classmethod
    # def validate_confidence_score(cls, v):
    #     if not 0.0 <= v <= 1.0:
    #         raise ValueError('Confidence score must be between 0.0 and 1.0')
    #     return v

class ExtractionResponse(BaseModel):
    extracted_data: List[ExtractedField]

# --- Helper Functions ---
def clean_json_response(response_text: str) -> str:
    """Clean and prepare JSON response from LLM for parsing"""
    # Remove markdown code blocks
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    response_text = response_text.strip()

    # Fix common JSON issues
    response_text = response_text.replace("'", '"')  # Replace single quotes with double quotes
    response_text = response_text.replace('\\n', '\\\\n')  # Escape newlines

    return response_text

def create_structured_prompt() -> str:
    """Create a more structured prompt for better JSON output"""
    fields_to_extract = [
        "Name",
        "Email",
        "Phone",
        "Skills",
        "Experience (roles, companies, duration)",
        "Certificates",
        "Domain (primary area of expertise, e.g., IT, Healthcare, Finance)"
    ]

    return f"""
You are an expert AI assistant specialized in extracting structured information from Arabic resumes.

Extract the following fields from the Arabic resume text and return ONLY a valid JSON array.

Fields to extract: {', '.join(fields_to_extract)}

For each field, create an object with these exact keys:
- "field_name": the name of the field being extracted
- "value": the extracted value (string for single values, array of strings for lists like skills)

Important formatting rules:
1. Return ONLY valid JSON - no explanations, no markdown, no additional text
2. Use double quotes for all strings
3. For list-type fields (like Skills), use an array of strings: ["skill1", "skill2", "skill3"]
4. For single-value fields (like Name, Email), use a string: "John Doe"

Example format:
[
  {{"field_name": "Name", "value": "أحمد محمد"}},
  {{"field_name": "Skills", "value": ["البرمجة", "إدارة المشاريع"]}}
]
"""

def validate_and_fix_json_structure(data_list: List[Dict[str, Any]]) -> List[ExtractedField]:
    """Validate and fix JSON structure to match Pydantic model"""
    fixed_data = []

    for item in data_list:
        try:
            # Ensure all required fields exist
            field_name = item.get('field_name', 'Unknown')
            value = item.get('value', '')
            # confidence_score = float(item.get('confidence_score', 0.0))

            # Handle value type conversion
            if isinstance(value, list):
                # Convert list elements to strings if needed
                value = [str(v) for v in value if v]  # Remove empty values
            elif value is None:
                value = ""
            else:
                value = str(value)

            # Ensure confidence score is valid
            # confidence_score = max(0.0, min(1.0, confidence_score))

            fixed_item = {
                'field_name': field_name,
                'value': value,
            }

            # Validate with Pydantic model
            extracted_field = ExtractedField(**fixed_item)
            fixed_data.append(extracted_field)

        except Exception as e:
            print(f"Error processing item {item}: {str(e)}")
            # Create a fallback item
            fixed_data.append(ExtractedField(
                field_name=str(item.get('field_name', 'Unknown')),
                value="",
            ))

    return fixed_data

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
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Please upload a .docx, .pdf, or .txt file."
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process the file: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the uploaded file.")

    # Create structured prompt
    system_prompt = create_structured_prompt()

    prompt = f"""
    {system_prompt}

    Resume Text:
    ---
    {resume_text}
    ---

    Return the JSON array now:
    """

    request_body = {
          "model": "llama-3.3-70b-versatile",
        # "model":"llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert AI assistant specialized in extracting structured information from Arabic resumes. You MUST return ONLY valid JSON format with no additional text or explanations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,  # Lower temperature for more consistent output
        "max_tokens": 2048,
        "response_format": {"type": "json_object"}  # Force JSON output
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
            response.raise_for_status()
            api_response = response.json()

            # Extract the content string from the API response
            extracted_content_str = api_response['choices'][0]['message']['content']

            # Clean the response
            cleaned_content = clean_json_response(extracted_content_str)

            try:
                # Parse JSON
                extracted_data_raw = json.loads(cleaned_content)

                # Handle different response formats
                if isinstance(extracted_data_raw, dict):
                    # If response is wrapped in an object, try to extract the array
                    if 'extracted_data' in extracted_data_raw:
                        extracted_data_raw = extracted_data_raw['extracted_data']
                    elif 'data' in extracted_data_raw:
                        extracted_data_raw = extracted_data_raw['data']
                    else:
                        # Convert single object to array
                        extracted_data_raw = [extracted_data_raw]

                # Validate and fix the data structure
                extracted_data = validate_and_fix_json_structure(extracted_data_raw)

                return ExtractionResponse(extracted_data=extracted_data)

            except json.JSONDecodeError as e:
                # Fallback: create a minimal response
                fallback_data = [
                    ExtractedField(
                        field_name="Error",
                        value=f"JSON parsing failed: {str(e)}. Raw response: {cleaned_content[:200]}...",
                    )
                ]
                return ExtractionResponse(extracted_data=fallback_data)

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from Groq API: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}"
            )

# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    return {"status": "Arabic Resume Extractor API is running."}

# --- Serve Frontend ---
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="frontend")
