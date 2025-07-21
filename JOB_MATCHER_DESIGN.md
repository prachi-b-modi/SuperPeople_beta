# Design Document: Job Matcher Feature for Resume Builder CLI

## Overview

This document outlines the design for a job matching feature that extends the existing Resume Builder CLI. The feature will accept job description URLs, extract relevant context using Exa.ai, perform semantic search through the user's professional experiences in Weaviate, and use OpenAI to refine and format the matched accomplishments.

## Functional Requirements

### Core Workflow
1. **URL Input**: User provides a job description URL
2. **Content Extraction**: Use Exa.ai API to extract job description content and requirements
3. **Semantic Search**: Search user's experiences in Weaviate for relevant accomplishments
4. **AI Refinement**: Use OpenAI to refine raw accomplishments into polished format
5. **Skill Extraction**: Extract relevant skills and tools from matched experiences
6. **Formatted Output**: Return structured list of accomplishments, skills, and tools

### Integration Requirements
- Build upon existing Resume Builder CLI architecture
- Leverage existing Weaviate database and OpenAI integration
- Add Exa.ai integration for web content extraction
- Maintain consistency with current CLI patterns and error handling

## Architecture

### High-Level Data Flow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ Job URL     │───▶│   Exa.ai     │───▶│   Weaviate  │───▶│   OpenAI     │
│ Input       │    │ Extraction   │    │ Semantic    │    │ Refinement   │
└─────────────┘    └──────────────┘    │ Search      │    └──────────────┘
                            │           └─────────────┘            │
                            ▼                   │                  ▼
                   ┌──────────────┐            ▼        ┌──────────────┐
                   │ Job Context  │   ┌─────────────┐   │ Refined      │
                   │ & Keywords   │   │ Relevant    │   │ Output       │
                   └──────────────┘   │ Experiences │   └──────────────┘
                                      └─────────────┘
```

### Component Architecture

```
resume_builder/
├── core/
│   ├── job_matcher.py          # NEW - Main job matching orchestrator
│   ├── job_extractor.py        # NEW - Exa.ai integration for job content
│   ├── experience_refiner.py   # NEW - OpenAI-based accomplishment refinement
│   └── extractor.py            # EXISTING - Experience extraction
├── models/
│   ├── job_description.py      # NEW - Job description data model
│   ├── match_result.py         # NEW - Job matching result model
│   └── experience.py           # EXISTING - Experience data model
├── cli/
│   └── commands.py             # MODIFIED - Add job matching commands
├── config/
│   └── config.yaml             # MODIFIED - Add Exa.ai configuration
└── utils/
    └── exa_client.py           # NEW - Exa.ai client wrapper
```

## Data Models

### JobDescription Model
```python
@dataclass
class JobDescription:
    url: str
    title: str
    company: str
    full_text: str
    requirements: List[str]
    skills_mentioned: List[str]
    responsibilities: List[str]
    extracted_keywords: List[str]
    summary: str
    created_date: datetime = field(default_factory=datetime.now)
```

### JobMatchResult Model
```python
@dataclass
class JobMatchResult:
    job_url: str
    matched_experiences: List[RefinedExperience]
    aggregated_skills: List[str]
    aggregated_tools: List[str]
    match_score: float
    processing_metadata: Dict[str, Any]
    created_date: datetime = field(default_factory=datetime.now)

@dataclass 
class RefinedExperience:
    original_experience_id: str
    refined_accomplishment: str
    extracted_skills: List[str]
    extracted_tools: List[str]
    relevance_score: float
    refinement_notes: str
```

## Implementation Details

### 1. Exa.ai Integration (JobExtractor)

```python
class JobExtractor:
    """Extract job description content using Exa.ai"""
    
    def extract_job_content(self, url: str) -> JobDescription:
        """
        Extract job description from URL using Exa.ai
        - Use /contents endpoint to get full page content
        - Extract job requirements, skills, and responsibilities
        - Generate summary using Exa.ai's summary feature
        """
        
    def _parse_job_requirements(self, content: str) -> List[str]:
        """Parse specific requirements from job content"""
        
    def _extract_skills_keywords(self, content: str) -> List[str]:
        """Extract technical skills and keywords mentioned"""
```

**Exa.ai API Usage**:
- **Endpoint**: `/contents`
- **Parameters**: 
  - `urls`: [job_url]
  - `text`: true (get full content)
  - `summary`: {"query": "job requirements and key qualifications"}
  - `highlights`: {"query": "required skills and experience", "numSentences": 3}

### 2. Enhanced Semantic Search

```python
class JobMatcher:
    """Main orchestrator for job matching workflow"""
    
    def match_job_to_experiences(self, job_url: str) -> JobMatchResult:
        """
        Complete job matching workflow:
        1. Extract job content with Exa.ai
        2. Generate search queries from job requirements
        3. Search experiences in Weaviate
        4. Refine matches with OpenAI
        5. Aggregate skills and tools
        """
        
    def _generate_search_queries(self, job_desc: JobDescription) -> List[str]:
        """Generate multiple search queries from job requirements"""
        
    def _search_relevant_experiences(self, queries: List[str]) -> List[Dict]:
        """Search user experiences with multiple queries"""
```

### 3. Experience Refinement (OpenAI)

```python
class ExperienceRefiner:
    """Refine raw experiences into polished accomplishments"""
    
    def refine_experiences(self, experiences: List[Dict], 
                          job_context: JobDescription) -> List[RefinedExperience]:
        """
        Use OpenAI to refine experiences:
        - Convert raw text into polished accomplishments
        - Extract relevant skills and tools
        - Tailor language to job requirements
        - Score relevance to the job
        """
        
    def _create_refinement_prompt(self, experience: Dict, 
                                 job_context: JobDescription) -> str:
        """Create targeted prompt for experience refinement"""
```

**OpenAI Prompt Strategy**:
```
System: You are an expert resume writer helping tailor professional accomplishments to job requirements.

Task: Refine the following experience into a polished accomplishment statement that highlights relevance to the target job.

Job Context: {job_requirements_and_skills}

Raw Experience: {original_experience_text}

Output Format:
{
  "refined_accomplishment": "Polished 1-2 sentence accomplishment",
  "extracted_skills": ["skill1", "skill2", "skill3"],
  "extracted_tools": ["tool1", "tool2", "tool3"],
  "relevance_score": 0.85,
  "refinement_notes": "Why this experience is relevant to the job"
}
```

### 4. CLI Commands

```bash
# Match experiences to a job posting
resume-builder match-job --url "https://company.com/job-posting" 

# Match with custom output format
resume-builder match-job --url "..." --format json --limit 5

# Save match results for later use  
resume-builder match-job --url "..." --save matches.json

# Load and display previous match results
resume-builder show-matches --input matches.json
```

## Configuration Updates

### Add Exa.ai Configuration
```yaml
# Exa.ai Configuration
exa:
  api_key: ${EXA_API_KEY}
  base_url: "https://api.exa.ai"
  timeout: 30
  max_retries: 3
  
  # Content extraction settings
  content_extraction:
    text: true
    max_characters: 5000
    summary_query: "job requirements, qualifications, and key skills"
    highlights_query: "required experience and technical skills"
    highlights_per_url: 3
    
# Job Matching Configuration  
job_matching:
  max_experiences_to_match: 10
  min_relevance_score: 0.3
  search_diversity: true  # Use multiple search strategies
  refinement_enabled: true
```

## Error Handling & Edge Cases

### URL Validation and Access
- **Invalid URLs**: Validate URL format before processing
- **Access Denied**: Handle authentication-required job pages
- **Content Blocked**: Graceful fallback for pages that block crawlers
- **Rate Limiting**: Respect Exa.ai rate limits with retry logic

### Content Processing
- **Empty Content**: Handle pages with minimal content
- **Non-Job Pages**: Detect and warn if URL doesn't contain job description
- **Multiple Job Listings**: Handle pages with multiple job postings

### Search and Matching
- **No Relevant Experiences**: Provide helpful message when no matches found
- **Poor Match Quality**: Set minimum thresholds and provide feedback
- **OpenAI Failures**: Graceful degradation when refinement fails

## API Cost Optimization

### Exa.ai Cost Management
- Use targeted summary queries to reduce content processing costs
- Implement caching for previously processed job URLs
- Optimize highlight extraction parameters

### OpenAI Cost Control
- Batch refinement requests when possible
- Use efficient prompt engineering to minimize token usage
- Implement result caching for similar job descriptions

## Future Enhancements

### Phase 2 Features
1. **Job Description Caching**: Store processed job descriptions for reuse
2. **Multi-URL Support**: Process multiple job URLs in batch
3. **Similarity Scoring**: Find similar job postings using Exa.ai's findSimilar
4. **Experience Ranking**: Advanced relevance scoring algorithms

### Phase 3 Features  
1. **Resume Generation**: Auto-generate resumes from match results
2. **Cover Letter Helper**: Generate cover letter content from matches
3. **Skills Gap Analysis**: Identify missing skills for target roles
4. **Interview Prep**: Generate potential interview questions

## Testing Strategy

### Unit Tests
- Job content extraction from various URL formats
- Search query generation and optimization
- Experience refinement prompt engineering
- Error handling for edge cases

### Integration Tests
- End-to-end job matching workflow
- Exa.ai API integration with various job sites
- Weaviate search result quality
- OpenAI refinement consistency

### Performance Tests
- Response time for complete workflow
- Cost efficiency across different job posting types
- Memory usage with large experience databases

## Security Considerations

### API Key Management
- Secure storage of Exa.ai API key
- Environment variable validation
- Key rotation support

### Data Privacy
- No storage of job posting content beyond session
- User experience data remains private
- Audit logging for API usage

## Success Metrics

### Functionality Metrics
- **Match Accuracy**: Percentage of relevant experiences found
- **Refinement Quality**: Human assessment of polished accomplishments
- **Processing Speed**: End-to-end workflow completion time

### Cost Metrics  
- **API Cost per Match**: Combined Exa.ai + OpenAI costs
- **Cost Efficiency**: Cost vs. value of match results
- **Resource Usage**: Memory and compute efficiency

### User Experience Metrics
- **CLI Usability**: Command completion time and error rates
- **Output Quality**: User satisfaction with refined accomplishments
- **Feature Adoption**: Usage frequency and patterns

This design provides a comprehensive framework for implementing intelligent job matching capabilities that leverage the existing Resume Builder infrastructure while adding powerful new functionality through Exa.ai integration. 