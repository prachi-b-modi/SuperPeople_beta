#!/usr/bin/env python3
"""
Semantic Job Search Script

This script takes a job URL as input, extracts the job description using Exa.ai,
and performs semantic search on experiences stored in Weaviate using embeddings.

Usage:
    python semantic_job_search.py --url "https://company.com/job-posting"
    python semantic_job_search.py --url "..." --limit 5 --min-score 0.7
    python semantic_job_search.py --url "..." --format json
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

try:
    import weaviate
    from weaviate.classes.query import Filter
except ImportError:
    print("Error: weaviate-client is required. Install with: pip install weaviate-client")
    sys.exit(1)

try:
    import openai
    import requests
    import time
except ImportError as e:
    print(f"Error: Required packages missing: {e}")
    print("Install with: pip install openai requests")
    sys.exit(1)


def check_environment_variables():
    """Check required environment variables"""
    required_vars = ['OPENAI_API_KEY', 'EXA_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment.")
        sys.exit(1)
    
    print("✅ Environment variables validated")


class SimpleExaClient:
    """Simple Exa.ai client for content extraction"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.exa.ai"
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'Semantic-Job-Search/1.0'
        })
        print("🔗 Exa client initialized")
    
    def extract_content(self, url: str) -> Dict[str, Any]:
        """Extract content from URL using Exa.ai"""
        print(f"🔍 Extracting content from: {url}")
        # breakpoint()
        payload = {
            "urls": [url],
            "text": {
                "maxCharacters": 8000,
                "includeHtmlTags": False
            },
            "summary": {
                "query": "job requirements skills responsibilities"
            },
            "highlights": {
                "query": "technical skills programming languages frameworks tools",
                "highlightsPerUrl": 5,
                "numSentences": 2
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/contents",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 429:
                print("⚠️  Rate limit exceeded, waiting...")
                time.sleep(5)
                response = self.session.post(
                    f"{self.base_url}/contents",
                    json=payload,
                    timeout=30
                )
            
            response.raise_for_status()
            data = response.json()
            
            if not data.get('results'):
                raise Exception("No content extracted")
            
            result = data['results'][0]
            
            extracted = {
                'url': url,
                'title': result.get('title', ''),
                'text': result.get('text', ''),
                'summary': result.get('summary', ''),
                'highlights': result.get('highlights', []),
                'author': result.get('author', ''),
                'domain': url.split('/')[2] if '/' in url else ''
            }
            
            print(f"✅ Content extracted successfully")
            print(f"   Title: {extracted['title'][:60]}{'...' if len(extracted['title']) > 60 else ''}")
            print(f"   Text length: {len(extracted['text'])} characters")
            print(f"   Summary length: {len(extracted['summary'])} characters")
            print(f"   Highlights: {len(extracted['highlights'])} items")
            
            return extracted
            
        except Exception as e:
            print(f"❌ Failed to extract content: {e}")
            raise


class SimpleJobProcessor:
    """Simple job content processor using OpenAI"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        print("🤖 OpenAI client initialized")
    
    def extract_keywords_and_entities(self, job_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract keywords and entities from job content using OpenAI"""
        print("\n🧠 Processing job content with OpenAI...")
        
        # Combine all text sources
        combined_text = self._combine_text_sources(job_content)
        print(f"   Combined text length: {len(combined_text)} characters")
        
        # Create prompt for keyword extraction
        prompt = self._create_extraction_prompt(job_content, combined_text)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing job descriptions and extracting structured information for semantic search. "},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            print(f"✅ OpenAI processing completed")
            print(f"   Response length: {len(content)} characters")
            
            # Parse JSON response
            try:
                import json
                parsed = json.loads(content)
                print(f"✅ JSON parsing successful")
                return parsed
            except json.JSONDecodeError:
                print("⚠️  JSON parsing failed, extracting manually")
                return self._manual_parse_response(content)
                
        except Exception as e:
            print(f"❌ OpenAI processing failed: {e}")
            return self._fallback_extraction(job_content)
    
    def _combine_text_sources(self, job_content: Dict[str, Any]) -> str:
        """Combine all text sources"""
        sources = [
            job_content.get('title', ''),
            job_content.get('text', ''),
            job_content.get('summary', ''),
            ' '.join(job_content.get('highlights', []))
        ]
        
        combined = '\n\n'.join(filter(None, sources))
        return combined[:6000]  # Limit for token constraints
    
    def _create_extraction_prompt(self, job_content: Dict[str, Any], combined_text: str) -> str:
        """Create prompt for OpenAI extraction"""
        return f"""Analyze this job posting and extract structured information for semantic search.

Job Title: {job_content.get('title', 'Unknown')}
Company Domain: {job_content.get('domain', 'Unknown')}

Job Content:
{combined_text}

Extract the following information and return as valid JSON:

{{
    "job_title": "cleaned job title",
    "company_name": "extracted company name",
    "technical_skills": ["list of technical skills, programming languages, frameworks"],
    "tools_and_technologies": ["list of tools, platforms, software mentioned"],
    "key_requirements": ["list of key requirements as short phrases"],
    "responsibilities": ["list of main responsibilities as short phrases"],
    "search_keywords": ["list of important keywords for semantic search"],
    "experience_level": "junior/mid/senior/lead/executive",
    "domain_keywords": ["industry-specific terms and concepts"],
    "summary": "2-3 sentence summary of the role"
}}

Focus on:
- Technical skills and technologies (programming languages, frameworks, tools)
- Key requirements that would match candidate experiences
- Important keywords that would be useful for semantic search
- Industry-specific terminology
- Avoid generic terms, focus on specific, searchable content

Return only valid JSON, no additional intro or extro"""
    
    def _manual_parse_response(self, content: str) -> Dict[str, Any]:
        """Manually parse response if JSON parsing fails"""
        print("   Attempting manual parsing...")
        
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                import json
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback to basic extraction
        return {
            "technical_skills": [],
            "search_keywords": ["software engineer", "programming"],
            "key_requirements": [],
            "summary": "Job analysis failed"
        }
    
    def _fallback_extraction(self, job_content: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback extraction without OpenAI"""
        print("   Using fallback extraction...")
        
        text = job_content.get('text', '').lower()
        title = job_content.get('title', '')
        
        # Basic skill extraction
        common_skills = ['python', 'java', 'javascript', 'react', 'node.js', 'sql', 'aws', 'docker', 'kubernetes']
        found_skills = [skill for skill in common_skills if skill in text]
        
        return {
            "job_title": title,
            "technical_skills": found_skills,
            "search_keywords": [title, "software engineer"] + found_skills,
            "key_requirements": [],
            "summary": f"Job posting for {title}"
        }


def connect_to_weaviate():
    """Connect to Weaviate instance"""
    try:
        # Try local connection first
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            grpc_port=50051,
            headers={
                "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")
            }
        )
        
        if client.is_ready():
            print("✅ Connected to local Weaviate instance")
            return client
        else:
            raise Exception("Local Weaviate not ready")
            
    except Exception as e:
        print(f"❌ Failed to connect to local Weaviate: {e}")
        
        # Try cloud connection if local fails
        cluster_url = os.getenv('WEAVIATE_CLUSTER_URL')
        api_key = os.getenv('WEAVIATE_API_KEY')
        
        if cluster_url and api_key:
            try:
                from weaviate.auth import AuthApiKey
                auth_credentials = AuthApiKey(api_key=api_key)
                
                client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=cluster_url,
                    auth_credentials=auth_credentials,
                    headers={
                        "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")
                    }
                )
                
                if client.is_ready():
                    print("✅ Connected to Weaviate Cloud instance")
                    return client
                else:
                    raise Exception("Cloud Weaviate not ready")
                    
            except Exception as cloud_e:
                print(f"❌ Failed to connect to Weaviate Cloud: {cloud_e}")
        
        print("❌ Could not connect to any Weaviate instance")
        print("Make sure Weaviate is running locally or set WEAVIATE_CLUSTER_URL and WEAVIATE_API_KEY for cloud.")
        sys.exit(1)


# This function is no longer needed as we use SimpleExaClient directly


# Duplicate main function removed - using the comprehensive one above


def generate_search_queries(processed_job: Dict[str, Any]) -> List[str]:
    """Generate search queries from processed job data"""
    queries = []
    
    # Job title
    if processed_job.get('job_title'):
        queries.append(processed_job['job_title'])
    
    # Technical skills as combined query
    technical_skills = processed_job.get('technical_skills', [])
    if technical_skills:
        queries.append(' '.join(technical_skills[:5]))  # Limit to avoid too long queries
    
    # Tools and technologies
    tools = processed_job.get('tools_and_technologies', [])
    if tools:
        queries.append(' '.join(tools[:5]))
    
    # Key requirements as individual queries
    requirements = processed_job.get('key_requirements', [])
    for req in requirements[:3]:  # Limit to 3 requirements
        if len(req) > 10:  # Only meaningful requirements
            queries.append(req)
    
    # Search keywords
    search_keywords = processed_job.get('search_keywords', [])
    if search_keywords:
        queries.append(' '.join(search_keywords[:5]))
    
    # Domain-specific keywords
    domain_keywords = processed_job.get('domain_keywords', [])
    if domain_keywords:
        queries.append(' '.join(domain_keywords[:3]))
    
    # Summary as a query
    if processed_job.get('summary'):
        queries.append(processed_job['summary'])
    
    # Clean and filter queries
    cleaned_queries = []
    for query in queries:
        if query and len(query.strip()) > 5:
            cleaned = query.strip().replace('\n', ' ').replace('\t', ' ')
            cleaned = ' '.join(cleaned.split())  # Remove extra spaces
            if cleaned:
                cleaned_queries.append(cleaned)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for query in cleaned_queries:
        if query.lower() not in seen:
            seen.add(query.lower())
            unique_queries.append(query)
    
    return unique_queries[:6]  # Limit to 6 queries


def search_experiences(client, queries: List[str], limit: int = 10, min_score: float = 0.0) -> List[Dict[str, Any]]:
    """Perform semantic search on experiences using multiple queries"""
    try:
        collection = client.collections.get("Experience")
        all_results = []
        seen_ids = set()
        
        print(f"🔍 Searching with {len(queries)} optimized queries...")
        
        for i, query in enumerate(queries, 1):
            print(f"  Query {i}: {query[:60]}{'...' if len(query) > 60 else ''}")
            
            try:
                # Perform semantic search
                search_query = collection.query.near_text(
                    query=query,
                    limit=limit * 2,  # Search for more to account for deduplication
                    return_metadata=["score", "distance"]
                )
                
                results = search_query.objects
                
                # Process results
                for result in results:
                    if str(result.uuid) not in seen_ids:
                        exp_dict = result.properties.copy()
                        exp_dict['id'] = str(result.uuid)
                        exp_dict['score'] = result.metadata.score if result.metadata else 0.0
                        exp_dict['distance'] = result.metadata.distance if result.metadata else 1.0
                        exp_dict['matched_query'] = query
                        exp_dict['query_index'] = i
                        
                        # Apply minimum score filter
                        if exp_dict['score'] >= min_score:
                            all_results.append(exp_dict)
                            seen_ids.add(str(result.uuid))
                            
            except Exception as e:
                print(f"    ⚠️  Query {i} failed: {e}")
                continue
        
        # Sort by score (descending) and limit results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        final_results = all_results[:limit]
        
        print(f"✅ Found {len(final_results)} relevant experiences")
        return final_results
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []


def format_experience(exp: Dict[str, Any], index: int) -> str:
    """Format experience for display"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"MATCH #{index + 1} (Score: {exp.get('score', 0):.3f})")
    lines.append(f"{'='*60}")
    
    # Basic info
    lines.append(f"ID: {exp.get('id', 'N/A')}")
    lines.append(f"Company: {exp.get('company_name', 'N/A')}")
    lines.append(f"Role: {exp.get('role', 'N/A')}")
    
    # Dates
    start_date = exp.get('start_date', 'N/A')
    end_date = exp.get('end_date', 'N/A')
    lines.append(f"Duration: {start_date} to {end_date}")
    
    # Accomplishment
    accomplishment = exp.get('accomplishment', '')
    if accomplishment:
        lines.append(f"\nAccomplishment:")
        lines.append(f"{accomplishment}")
    
    # Skills
    skills = exp.get('skills', [])
    if skills:
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except:
                skills = [skills]
        lines.append(f"\nSkills: {', '.join(skills) if skills else 'N/A'}")
    
    # Tools
    tools = exp.get('tools', [])
    if tools:
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except:
                tools = [tools]
        lines.append(f"Tools: {', '.join(tools) if tools else 'N/A'}")
    
    # Match info
    lines.append(f"\nMatched Query: {exp.get('matched_query', 'N/A')[:100]}{'...' if len(exp.get('matched_query', '')) > 100 else ''}")
    lines.append(f"Distance: {exp.get('distance', 'N/A')}")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Job Search - Find relevant experiences for a job posting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python semantic_job_search.py --url "https://company.com/job-posting"
  python semantic_job_search.py --url "..." --limit 5 --min-score 0.7
  python semantic_job_search.py --url "..." --format json
  python semantic_job_search.py --url "..." --format json --output results.json
        """
    )
    
    parser.add_argument(
        '--url',
        required=True,
        help='Job posting URL to analyze'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of experiences to return (default: 10)'
    )
    
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.0,
        help='Minimum relevance score (0.0-1.0, default: 0.0)'
    )
    
    parser.add_argument(
        '--format',
        choices=['detailed', 'json'],
        default='detailed',
        help='Output format (default: detailed)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file path (for JSON format)'
    )
    
    parser.add_argument(
        '--show-job',
        action='store_true',
        help='Show extracted job description details'
    )
    
    args = parser.parse_args()
    
    print("🚀 Semantic Job Search Tool")
    print("=" * 50)
    
    # Check environment variables
    check_environment_variables()
    
    # Initialize clients

    print("EXA_API_KEY", os.getenv('EXA_API_KEY'))
    exa_client = SimpleExaClient(os.getenv('EXA_API_KEY'))
    job_processor = SimpleJobProcessor(os.getenv('OPENAI_API_KEY'))
    
    # Connect to Weaviate
    client = connect_to_weaviate()
    
    try:
        # Extract job content using Exa
        print(f"\n📄 Step 1: Extracting job content")
        job_content = exa_client.extract_content(args.url)
        
        # Process with OpenAI
        print(f"\n🔍 Step 2: Processing with OpenAI")
        processed_job = job_processor.extract_keywords_and_entities(job_content)
        
        # Show job details if requested
        if args.show_job:
            print("\n📋 Job Description Details:")
            print(f"Title: {processed_job.get('job_title', 'N/A')}")
            print(f"Company: {processed_job.get('company_name', 'N/A')}")
            print(f"Summary: {processed_job.get('summary', '')[:200]}{'...' if len(processed_job.get('summary', '')) > 200 else ''}")
            print(f"Skills: {', '.join(processed_job.get('technical_skills', [])[:10])}")
            print(f"Keywords: {', '.join(processed_job.get('search_keywords', [])[:10])}")
        
        # Generate search queries
        queries = generate_search_queries(processed_job)
        print(f"\n🎯 Generated {len(queries)} search queries")
        
        # Search experiences
        experiences = search_experiences(client, queries, args.limit, args.min_score)
        
        if not experiences:
            print("\n❌ No relevant experiences found")
            return
        
        # Output results
        if args.format == 'json':
            result = {
                'job_description': processed_job,
                'search_queries': queries,
                'matching_experiences': experiences,
                'search_metadata': {
                    'total_found': len(experiences),
                    'min_score_filter': args.min_score,
                    'search_timestamp': datetime.now().isoformat()
                }
            }
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"\n💾 Results saved to {args.output}")
            else:
                print(json.dumps(result, indent=2, default=str))
        else:
            # Detailed format
            print(f"\n🎯 Top {len(experiences)} Matching Experiences:")
            for i, exp in enumerate(experiences):
                print(format_experience(exp, i))
            
            # Summary
            print(f"\n\n📊 Search Summary:")
            print(f"Job: {processed_job.get('job_title', 'N/A')} at {processed_job.get('company_name', 'N/A')}")
            print(f"Total matches found: {len(experiences)}")
            print(f"Average score: {sum(exp['score'] for exp in experiences) / len(experiences):.3f}")
            print(f"Score range: {min(exp['score'] for exp in experiences):.3f} - {max(exp['score'] for exp in experiences):.3f}")
    
    finally:
        client.close()
        print("\n👋 Disconnected from Weaviate")


if __name__ == "__main__":
    main()