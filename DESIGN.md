# Design Document: Resume Builder CLI

## Overview

This document outlines the design for a Python CLI tool that processes professional experience text, extracts structured information using OpenAI, creates vector embeddings, and stores the data in Weaviate for later semantic search to populate resumes.

## Requirements

### Functional Requirements
1. Accept input text with company name metadata
2. Extract core skills, categories, and relevant job titles using OpenAI GPT-4.1 mini
3. Generate vector embeddings for all extracted information
4. Store data objects in Weaviate database optimized for semantic search
5. Support both local and cloud Weaviate deployments

### Non-Functional Requirements
1. Modular architecture for easy component swapping
2. Configurable hyperparameters
3. Error handling and recovery
4. Extensible for future enhancements

## Architecture

### High-Level Components

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│     CLI     │───▶│  Extractor   │───▶│ Vectorizer  │───▶│   Storage    │
│   Interface │    │   (OpenAI)   │    │ (Weaviate)  │    │ (Weaviate)   │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
       │                    │                   │                 │
       ▼                    ▼                   ▼                 ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│Configuration│    │   Prompts    │    │   Schema    │    │  Local/Cloud │
│  Management │    │  Templates   │    │ Definition  │    │   Adapters   │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
```

### Project Structure

```
resume_builder/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Entry point and command definitions
│   └── commands.py          # Individual CLI commands
├── core/
│   ├── __init__.py
│   ├── extractor.py         # OpenAI integration for information extraction
│   ├── processor.py         # Text processing and data preparation
│   └── exceptions.py        # Custom exceptions
├── database/
│   ├── __init__.py
│   ├── base.py             # Abstract database interface
│   ├── local_weaviate.py   # Local Weaviate implementation
│   └── cloud_weaviate.py   # Cloud Weaviate implementation
├── models/
│   ├── __init__.py
│   ├── schemas.py          # Data models and Weaviate schemas
│   └── experience.py       # Experience data class
├── config/
│   ├── __init__.py
│   ├── settings.py         # Configuration management
│   └── config.yaml         # Default configuration
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Logging utilities
│   └── helpers.py          # General utility functions
├── requirements.txt
├── setup.py
└── README.md
```

## Data Models

### Experience Schema (Weaviate Collection)

```python
{
    "class": "Experience",
    "description": "Professional experience entry for resume building",
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
        "text2vec-openai": {
            "model": "text-embedding-3-small",
            "dimensions": 1536,
            "type": "text"
        }
    },
    "properties": [
        {
            "name": "original_text",
            "dataType": ["text"],
            "description": "Original experience description",
            "moduleConfig": {
                "text2vec-openai": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            }
        },
        {
            "name": "skills",
            "dataType": ["text[]"],
            "description": "Extracted core skills"
        },
        {
            "name": "categories",
            "dataType": ["text[]"],
            "description": "Experience categories/domains"
        },
        {
            "name": "relevant_jobs",
            "dataType": ["text[]"],
            "description": "Relevant job titles"
        },
        {
            "name": "company_name",
            "dataType": ["string"],
            "description": "Company where experience was gained"
        },
        {
            "name": "created_date",
            "dataType": ["date"],
            "description": "Entry creation timestamp"
        },
        {
            "name": "combined_text",
            "dataType": ["text"],
            "description": "Combined text for enhanced vectorization",
            "moduleConfig": {
                "text2vec-openai": {
                    "skip": False,
                    "vectorizePropertyName": False
                }
            }
        }
    ]
}
```

### Python Data Classes

```python
@dataclass
class ExperienceData:
    original_text: str
    company_name: str
    skills: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    relevant_jobs: List[str] = field(default_factory=list)
    created_date: datetime = field(default_factory=datetime.now)
    combined_text: str = ""
    
    def generate_combined_text(self) -> str:
        """Generate enhanced text for vectorization"""
        parts = [self.original_text]
        if self.skills:
            parts.append(f"Key skills: {', '.join(self.skills)}")
        if self.categories:
            parts.append(f"Categories: {', '.join(self.categories)}")
        if self.relevant_jobs:
            parts.append(f"Relevant for: {', '.join(self.relevant_jobs)}")
        return " | ".join(parts)
```

## Implementation Details

### 1. CLI Interface (Click Framework)

```python
@click.group()
@click.option('--config', default='config/config.yaml', help='Configuration file path')
@click.pass_context
def cli(ctx, config):
    """Resume Builder CLI - Manage your professional experiences"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)

@cli.command()
@click.option('--text', required=True, help='Experience description text')
@click.option('--company', required=True, help='Company name')
@click.option('--extract/--no-extract', default=True, help='Extract skills and metadata')
def add_experience(text, company, extract):
    """Add a new professional experience"""
    # Implementation details
```

### 2. OpenAI Integration

```python
class ExperienceExtractor:
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def extract_information(self, text: str) -> Dict[str, List[str]]:
        """Extract skills, categories, and relevant jobs from text"""
        prompt = self._build_extraction_prompt(text)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _build_extraction_prompt(self, text: str) -> str:
        return f"""
        Extract structured information from this professional experience description.
        
        Text: {text}
        
        Extract:
        1. Core skills (both technical and soft skills)
        2. Professional categories/domains
        3. Relevant job titles that would value this experience
        
        Return as JSON:
        {{
            "skills": ["skill1", "skill2", ...],
            "categories": ["category1", "category2", ...],
            "relevant_jobs": ["job_title1", "job_title2", ...]
        }}
        """
```

### 3. Weaviate Storage Layer

```python
class WeaviateDatabase(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass
    
    @abstractmethod
    def create_schema(self) -> None:
        pass
    
    @abstractmethod
    def store_experience(self, experience: ExperienceData) -> str:
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        pass

class LocalWeaviateDatabase(WeaviateDatabase):
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.client = None
    
    def connect(self) -> None:
        self.client = weaviate.connect_to_local(
            host=self.host,
            port=self.port
        )
    
    def store_experience(self, experience: ExperienceData) -> str:
        collection = self.client.collections.get("Experience")
        
        result = collection.data.insert(
            properties={
                "original_text": experience.original_text,
                "skills": experience.skills,
                "categories": experience.categories,
                "relevant_jobs": experience.relevant_jobs,
                "company_name": experience.company_name,
                "created_date": experience.created_date,
                "combined_text": experience.combined_text
            }
        )
        return result

class CloudWeaviateDatabase(WeaviateDatabase):
    def __init__(self, cluster_url: str, api_key: str):
        self.cluster_url = cluster_url
        self.api_key = api_key
        self.client = None
    
    def connect(self) -> None:
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=self.cluster_url,
            auth_credentials=weaviate.auth.AuthApiKey(self.api_key)
        )
```

### 4. Configuration Management

```yaml
# config.yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: "gpt-4.1-mini"
  extraction_temperature: 0.3

weaviate:
  type: "local"  # or "cloud"
  local:
    host: "localhost"
    port: 8080
  cloud:
    cluster_url: ${WEAVIATE_CLUSTER_URL}
    api_key: ${WEAVIATE_API_KEY}
  
  collection:
    name: "Experience"
    vectorizer: "text2vec-openai"
    vectorizer_config:
      model: "text-embedding-3-small"
      dimensions: 1536

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

```python
class Config:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.data = yaml.safe_load(f)
        self._expand_env_vars()
    
    def _expand_env_vars(self):
        """Expand environment variables in config"""
        # Implementation for ${VAR} substitution
    
    @property
    def openai_config(self) -> Dict:
        return self.data['openai']
    
    @property
    def weaviate_config(self) -> Dict:
        return self.data['weaviate']
```

### 5. Main Processing Pipeline

```python
class ExperienceProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.extractor = ExperienceExtractor(
            api_key=config.openai_config['api_key'],
            model=config.openai_config['model']
        )
        self.database = self._create_database()
    
    def _create_database(self) -> WeaviateDatabase:
        """Factory method for database creation"""
        weaviate_config = self.config.weaviate_config
        
        if weaviate_config['type'] == 'local':
            return LocalWeaviateDatabase(**weaviate_config['local'])
        elif weaviate_config['type'] == 'cloud':
            return CloudWeaviateDatabase(**weaviate_config['cloud'])
        else:
            raise ValueError(f"Unknown Weaviate type: {weaviate_config['type']}")
    
    def process_experience(self, text: str, company: str, extract: bool = True) -> str:
        """Main processing pipeline"""
        try:
            # Create experience object
            experience = ExperienceData(
                original_text=text,
                company_name=company
            )
            
            # Extract information if requested
            if extract:
                extracted = self.extractor.extract_information(text)
                experience.skills = extracted.get('skills', [])
                experience.categories = extracted.get('categories', [])
                experience.relevant_jobs = extracted.get('relevant_jobs', [])
            
            # Generate combined text for enhanced vectorization
            experience.combined_text = experience.generate_combined_text()
            
            # Store in database
            result_id = self.database.store_experience(experience)
            
            logger.info(f"Successfully stored experience with ID: {result_id}")
            return result_id
            
        except Exception as e:
            logger.error(f"Error processing experience: {str(e)}")
            raise
```

## Configuration & Setup

### Local Development Setup

```bash
# 1. Start local Weaviate
docker-compose up -d

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export OPENAI_API_KEY="your-key-here"

# 4. Initialize database schema
resume-builder init-db

# 5. Add first experience
resume-builder add-experience \
  --text "Led a team of 5 developers to build a microservices architecture..." \
  --company "TechCorp"
```

### Docker Compose for Local Weaviate

```yaml
version: '3.4'
services:
  weaviate:
    image: cr.weaviate.io/semitechnologies/weaviate:1.32.0
    ports:
      - 8080:8080
      - 50051:50051
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      ENABLE_API_BASED_MODULES: 'true'
      ENABLE_MODULES: 'text2vec-openai'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_data:/var/lib/weaviate
    restart: on-failure:0

volumes:
  weaviate_data:
```

## Error Handling & Recovery

1. **API Failures**: Retry logic with exponential backoff
2. **Data Validation**: Pydantic models for type safety
3. **Database Connectivity**: Health checks and graceful degradation
4. **Rate Limiting**: Respect API limits with queuing
5. **Logging**: Comprehensive logging for debugging

## Future Enhancements

1. **Semantic Search Interface**: CLI commands for querying experiences
2. **Resume Generation**: Template-based resume creation from search results
3. **Web Interface**: FastAPI-based web UI
4. **Experience Deduplication**: Detect and merge similar experiences
5. **Analytics**: Experience categorization and skill gap analysis
6. **Export Functions**: Export to various resume formats (PDF, JSON, etc.)

This design provides a solid foundation for building a modular, extensible resume builder CLI that can grow with additional features while maintaining clean architecture and configurability. 