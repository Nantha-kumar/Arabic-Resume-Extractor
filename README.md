# Arabic Resume Extractor using FastAPI and Groq

This project provides a simple API built with FastAPI to extract structured information from Arabic resumes. It leverages the power of Groq's LLaMA 3.1 model to perform the extraction.

## Features

-   Extracts the following key fields from an Arabic resume:
    -   Name
    -   Email
    -   Phone
    -   Skills
    -   Experience (roles, companies, duration)
    -   Certificates
    -   Domain (primary area of expertise, e.g., IT, Healthcare, Finance)
-   Simple and fast API endpoint.
-   Easy to set up and run.

## Prerequisites

-   Python 3.7+
-   `pip` for package management
-   A Groq API key

## Setup and Installation

1.  **Clone the repository (or download the files):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment:**
    -   **On macOS and Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    -   **On Windows:**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set your Groq API Key:**
    You need to set your Groq API key as an environment variable.
    -   **On macOS and Linux:**
        ```bash
        export GROQ_API_KEY='your_groq_api_key_here'
        ```
    -   **On Windows (Command Prompt):**
        ```bash
        set GROQ_API_KEY=your_groq_api_key_here
        ```
    -   **On Windows (PowerShell):**
        ```bash
        $env:GROQ_API_KEY="your_groq_api_key_here"
        ```
    *Note: Replace `your_groq_api_key_here` with your actual key.*

## Running the Application

Once the setup is complete, you can run the FastAPI application using `uvicorn`.

```bash
uvicorn main:app --reload
```

The `--reload` flag makes the server restart after code changes. For production, you would run it without this flag.

The API will be available at `http://127.0.0.1:8000`.

## API Usage

You can access the interactive API documentation (Swagger UI) by navigating to `http://127.0.0.1:8000/docs` in your browser.

### Endpoint: `/extract/`

-   **Method:** `POST`
-   **Body:** The endpoint now accepts a file upload (`multipart/form-data`). The file should be sent with the key `resume_file`.
-   **Supported Formats:** The API can process `.docx`, `.pdf`, and `.txt` files.

### Example `curl` Request

You can use `curl` to test the endpoint from your terminal. Make sure you have a resume file (e.g., `my_resume.txt`) in the same directory.

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/extract/' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'resume_file=@my_resume.txt;type=text/plain'
```

## Using the Frontend

This project includes a simple web interface that is served directly by the FastAPI backend.

1.  Make sure the FastAPI server is running (as described in the "Running the Application" section).
2.  Open your web browser and navigate to **`http://127.0.0.1:8000/ui`**.
3.  The web page will load, and you can use the interface to select your resume file and submit it to the API. The extracted JSON will be displayed on the page.

### Example Response

The API will return a JSON object with the extracted data. (Note: The current implementation has a placeholder for the response parsing).

```json
{
  "extracted_data": [
    {
      "field_name": "الاسم الكامل",
      "value": "(مثال) أحمد محمد",
      "confidence_score": 0.95
    },
    {
      "field_name": "معلومات الاتصال",
      "value": "(مثال) email@example.com, +96612345678",
      "confidence_score": 0.98
    }
  ]
}