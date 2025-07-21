# Resume Builder CLI

A Python CLI tool for managing professional experiences and building resumes using OpenAI for information extraction and Weaviate for vector storage.

## 🚧 Implementation Status

This project is currently under development. The following components have been implemented:

### ✅ Completed Components

**Phase 1: Project Setup and Core Infrastructure**
- [x] Project directory structure
- [x] Package initialization files  
- [x] Requirements.txt with dependencies
- [x] Setup.py for package installation
- [x] .gitignore configuration
- [x] Configuration management with environment variable expansion
- [x] Logging utilities with Rich formatting
- [x] General utility helper functions
- [x] Custom exception hierarchy

**Phase 2: Data Models and Schema**
- [x] ExperienceData dataclass with validation
- [x] Weaviate schema definition and management
- [x] Schema property definitions
- [x] Collection configuration utilities

**Phase 3: OpenAI Integration**
- [x] ExperienceExtractor with retry logic
- [x] Structured information extraction (skills, categories, relevant jobs)
- [x] Error handling and rate limiting
- [x] Batch processing capabilities

**Phase 4: Weaviate Database Layer**
- [x] Abstract database interface
- [x] Local Weaviate implementation
- [x] Cloud Weaviate implementation
- [x] CRUD operations with filtering
- [x] Semantic search functionality
- [x] Backup and restore capabilities

**Phase 5: Core Processing Pipeline**
- [x] ExperienceProcessor orchestration
- [x] End-to-end processing workflow
- [x] Health monitoring and statistics
- [x] Context managers and resource cleanup

**Phase 6: CLI Interface**
- [x] Click-based command structure
- [x] Rich console output formatting
- [x] Comprehensive command set
- [x] Error handling and user feedback

### 🎉 Implementation Complete!

### 🎯 Project Architecture

```
resume_builder/
├── cli/                 # CLI interface (Click framework)
├── core/               # Core business logic
│   ├── extractor.py    # OpenAI integration
│   ├── processor.py    # Main processing pipeline
│   └── exceptions.py   # Custom exceptions ✅
├── database/           # Database abstraction layer
│   ├── base.py        # Abstract interface
│   ├── local_weaviate.py   # Local implementation
│   └── cloud_weaviate.py   # Cloud implementation
├── models/             # Data models and schemas
│   ├── experience.py   # Experience data model ✅
│   └── schemas.py      # Weaviate schemas ✅
├── config/             # Configuration management
│   ├── settings.py     # Config classes ✅
│   └── config.yaml     # Default config ✅
└── utils/              # Utility functions
    ├── logger.py       # Logging setup ✅
    └── helpers.py      # General utilities ✅
```

## 🔧 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Docker (for local Weaviate)
- OpenAI API key

### Local Development Setup

1. **Clone and setup environment:**
```bash
git clone <repository>
cd resume-builder-cli
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp env.example .env
# Edit .env file with your OpenAI API key
```

3. **Start local Weaviate:**
```bash
docker-compose up -d
```

4. **Install the package:**
```bash
pip install -e .
```

## 📋 Configuration

The application uses a YAML configuration file with environment variable substitution:

```yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: "gpt-4.1-mini"

weaviate:
  type: "local"  # or "cloud"
  local:
    host: "localhost"
    port: 8080
```

## 🎯 Usage

### Quick Start

```bash
# 1. Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# 2. Start local Weaviate (if using local setup)
docker-compose up -d

# 3. Initialize the database
resume-builder init-db

# 4. Add your first experience
resume-builder add-experience \
  --text "Led a team of 5 developers to build a microservices architecture using Python, Docker, and Kubernetes. Implemented CI/CD pipelines and reduced deployment time by 60%." \
  --company "TechCorp Inc"

# 5. List your experiences
resume-builder list-experiences

# 6. Search for relevant experiences
resume-builder search --query "Python microservices leadership"
```

### Available Commands

```bash
# Core functionality
resume-builder add-experience     # Add new professional experience
resume-builder list-experiences   # List stored experiences  
resume-builder search            # Semantic search through experiences

# Database management
resume-builder init-db           # Initialize database schema
resume-builder health-check      # Check system health
resume-builder stats             # Show usage statistics

# Data management
resume-builder backup            # Backup experiences to JSON
resume-builder restore           # Restore from backup

# Information
resume-builder version           # Show version info
resume-builder config-info       # Show current configuration
```

### Command Examples

```bash
# Add experience without metadata extraction
resume-builder add-experience \
  --text "Managed customer relationships and sales processes" \
  --company "SalesCorp" \
  --no-extract

# Search with filtering
resume-builder search \
  --query "machine learning data science" \
  --company "TechCorp" \
  --min-score 0.7 \
  --limit 5

# List experiences in different formats
resume-builder list-experiences --format json
resume-builder list-experiences --company "TechCorp" --limit 10

# Backup and restore
resume-builder backup --output my_experiences.json
resume-builder restore --input my_experiences.json
```

## 📊 Data Model

Professional experiences are stored with:

- **original_text**: The raw experience description
- **skills**: Extracted technical and soft skills
- **categories**: Professional domains/categories
- **relevant_jobs**: Job titles that would value this experience
- **company_name**: Company where experience was gained
- **created_date**: Entry timestamp
- **combined_text**: Enhanced text for vectorization

## 🔄 Development Workflow

The implementation follows a phased approach:

1. ✅ **Infrastructure Setup** - Project structure, config, utilities
2. ✅ **Data Models** - Experience model and Weaviate schemas
3. ✅ **OpenAI Integration** - Information extraction from text
4. ✅ **Database Layer** - Weaviate operations (local & cloud)
5. ✅ **Processing Pipeline** - Orchestration of extraction and storage
6. ✅ **CLI Interface** - User-facing commands
7. 🚧 **Documentation & Testing** - Complete documentation and testing

## 🌟 Features

### Core Features
- **AI-Powered Extraction**: Uses OpenAI GPT-4.1 mini to extract skills, categories, and relevant job titles
- **Semantic Search**: Vector-based search to find experiences relevant to job descriptions
- **Dual Database Support**: Works with both local and cloud Weaviate instances
- **Rich CLI Interface**: Beautiful command-line interface with helpful output
- **Data Management**: Backup, restore, and migration capabilities
- **Flexible Configuration**: YAML-based configuration with environment variable support

### Technical Features
- **Modular Architecture**: Easy to extend and modify components
- **Error Handling**: Comprehensive error handling with retry logic
- **Logging**: Contextual logging with Rich formatting
- **Type Safety**: Full type annotations with Pydantic validation
- **Resource Management**: Proper connection management and cleanup
- **Batch Processing**: Support for processing multiple experiences

## 🏗️ Architecture Principles

- **Modular Design**: Easy to swap components (local/cloud Weaviate, different LLMs)
- **Configuration-Driven**: Behavior controlled via YAML config
- **Error Handling**: Comprehensive exception hierarchy
- **Logging**: Rich console output with contextual logging
- **Type Safety**: Pydantic models for validation

## 📈 What's Next

The core functionality is complete! Here are potential enhancements:

### Immediate Improvements
- [ ] **Unit Tests**: Comprehensive test suite for all components
- [ ] **Integration Tests**: End-to-end testing with real APIs
- [ ] **Performance Optimization**: Batch operations and caching
- [ ] **Enhanced Search**: Hybrid search combining semantic + keyword

### Advanced Features
- [ ] **Resume Generation**: Auto-generate resumes from search results
- [ ] **Web Interface**: FastAPI-based web UI for easier interaction
- [ ] **Analytics Dashboard**: Visualize your experience data and trends
- [ ] **Experience Deduplication**: Detect and merge similar experiences
- [ ] **Export Formats**: PDF, Word, LaTeX resume generation
- [ ] **Skills Gap Analysis**: Compare your skills against job requirements

### Enterprise Features  
- [ ] **Multi-user Support**: Team-based experience sharing
- [ ] **API Server**: REST API for integration with other tools
- [ ] **Advanced Security**: Authentication and authorization
- [ ] **Compliance**: GDPR/privacy-compliant data handling

## 🤝 Contributing

This project follows the task-driven development approach outlined in `task.md`. Each phase builds upon the previous one to create a robust, modular system.

## 📄 License

MIT License - see LICENSE file for details. 