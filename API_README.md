# Resume Builder API

This API provides a RESTful interface to the Resume Builder CLI tool, allowing you to manage experiences and match them to job postings.

## Setup

1. Make sure you have the Resume Builder CLI installed and working
2. Install additional dependencies:
   ```bash
   pip install fastapi uvicorn
   ```
3. Run the API server:
   ```bash
   python run_api.py
   ```

## API Endpoints

### Experiences

#### Add Experience
- **URL**: `/api/experiences/`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "text": "Led a team of 5 developers to build a scalable microservices architecture using Python and Docker, resulting in 40% improved system performance.",
    "company": "TechCorp",
    "role": "Senior Developer",
    "duration": "Jan 2020 - Dec 2022",
    "no_extraction": false
  }
  ```
- **Response**: The created experience with extracted skills and categories

#### List Experiences
- **URL**: `/api/experiences/`
- **Method**: `GET`
- **Response**: Array of all experiences

#### Get Experience
- **URL**: `/api/experiences/{experience_id}`
- **Method**: `GET`
- **Response**: Single experience details

#### Delete Experience
- **URL**: `/api/experiences/{experience_id}`
- **Method**: `DELETE`
- **Response**: No content (204)

#### Search Experiences
- **URL**: `/api/experiences/search/?query={search_query}`
- **Method**: `GET`
- **Response**: Array of matching experiences

### Jobs

#### Match Job
- **URL**: `/api/jobs/match`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "url": "https://www.linkedin.com/jobs/view/example-job"
  }
  ```
- **Response**: Job details and matching experiences

#### Extract Job
- **URL**: `/api/jobs/extract`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "url": "https://www.linkedin.com/jobs/view/example-job"
  }
  ```
- **Response**: Extracted job details

### Utilities

#### Health Check
- **URL**: `/api/utils/health`
- **Method**: `GET`
- **Response**: System health status

#### Database Stats
- **URL**: `/api/utils/stats`
- **Method**: `GET`
- **Response**: Database statistics

#### Configuration Info
- **URL**: `/api/utils/config`
- **Method**: `GET`
- **Response**: Current configuration

## Example cURL Commands

### Add Experience
```bash
curl -X POST "http://localhost:8000/api/experiences/" \
     -H "Content-Type: application/json" \
     -d '{"text":"Led a team of 5 developers to build a scalable microservices architecture using Python and Docker, resulting in 40% improved system performance.","company":"TechCorp","duration":"Jan 2020 - Dec 2022"}'
```

### Add Experience
```bash
curl -X POST "http://localhost:8000/api/experiences/" \
     -H "Content-Type: application/json" \
     -d '{"text":"Wrote an article on medium about quantization","company":"LUCID","duration":"Jan 2020 - Dec 2021"}'
```

### List Experiences
```bash
curl -X GET "http://localhost:8000/api/experiences/"
```

### Search Experiences
```bash
curl -X GET "http://localhost:8000/api/experiences/search/?query=python"
```

### Delete Experience
```bash
curl -X DELETE "http://localhost:8000/api/experiences/exp-123"
```

### Match Job
```bash
curl -X POST "http://localhost:8000/api/jobs/match" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://www.linkedin.com/jobs/view/example-job"}'
```

## Interactive API Documentation

When the server is running, you can access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc