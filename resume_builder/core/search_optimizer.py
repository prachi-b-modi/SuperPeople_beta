"""
Search query optimization for job matching in Resume Builder CLI
"""

import re
from typing import List, Dict, Any, Set, Tuple
from collections import Counter

from ..models.job_description import JobDescription
from ..utils.logger import get_logger, ContextualLogger

logger = get_logger(__name__)


class SearchQueryOptimizer:
    """
    Generate optimized search queries from job descriptions
    
    Creates diverse search strategies to find relevant experiences in Weaviate
    using multiple query approaches for comprehensive matching.
    """
    
    def __init__(self, enable_diversity: bool = True):
        """
        Initialize search optimizer
        
        Args:
            enable_diversity: Whether to generate diverse query types
        """
        self.enable_diversity = enable_diversity
        self.logger = ContextualLogger(logger, {"component": "search_optimizer"})
        
        # Technical skill categories for better grouping
        self.skill_categories = {
            'programming_languages': {
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 
                'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala', 'r'
            },
            'web_frameworks': {
                'react', 'angular', 'vue', 'node.js', 'express', 'django', 
                'flask', 'spring', 'laravel', 'rails', 'next.js', 'nuxt'
            },
            'databases': {
                'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
                'cassandra', 'dynamodb', 'sqlite', 'oracle', 'sqlserver'
            },
            'cloud_platforms': {
                'aws', 'azure', 'gcp', 'google cloud', 'amazon web services',
                'microsoft azure', 'digital ocean', 'heroku'
            },
            'devops_tools': {
                'docker', 'kubernetes', 'terraform', 'jenkins', 'gitlab',
                'github actions', 'ci/cd', 'ansible', 'chef', 'puppet'
            },
            'data_science': {
                'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn',
                'spark', 'hadoop', 'tableau', 'power bi', 'jupyter'
            }
        }
        
        self.logger.info("SearchQueryOptimizer initialized")
    
    def generate_search_queries(self, job_description: JobDescription, 
                              max_queries: int = 8) -> List[Dict[str, Any]]:
        """
        Generate optimized search queries from job description
        
        Args:
            job_description: Job description to analyze
            max_queries: Maximum number of queries to generate
            
        Returns:
            List of query dictionaries with metadata
        """
        self.logger.info(f"Generating search queries for: {job_description.title}")
        
        queries = []
        
        # Strategy 1: Primary skills query
        primary_query = self._generate_primary_skills_query(job_description)
        if primary_query:
            queries.append(primary_query)
        
        # Strategy 2: Technology stack queries
        tech_queries = self._generate_technology_queries(job_description)
        queries.extend(tech_queries)
        
        # Strategy 3: Responsibility-based queries
        responsibility_queries = self._generate_responsibility_queries(job_description)
        queries.extend(responsibility_queries)
        
        # Strategy 4: Experience level queries
        if self.enable_diversity:
            level_queries = self._generate_experience_level_queries(job_description)
            queries.extend(level_queries)
        
        # Strategy 5: Industry-specific queries
        industry_queries = self._generate_industry_queries(job_description)
        queries.extend(industry_queries)
        
        # Strategy 6: Combined keyword queries
        keyword_queries = self._generate_keyword_queries(job_description)
        queries.extend(keyword_queries)
        
        # Rank and filter queries
        ranked_queries = self._rank_and_filter_queries(queries, max_queries)
        
        self.logger.info(f"Generated {len(ranked_queries)} optimized search queries")
        return ranked_queries
    
    def _generate_primary_skills_query(self, job_desc: JobDescription) -> Dict[str, Any]:
        """Generate primary skills-based query"""
        if not job_desc.skills_mentioned:
            return None
        
        # Take top 4-5 most important skills
        primary_skills = job_desc.skills_mentioned[:5]
        
        return {
            'query': ' '.join(primary_skills),
            'type': 'primary_skills',
            'priority': 1.0,
            'skills_count': len(primary_skills),
            'description': f"Primary skills: {', '.join(primary_skills)}"
        }
    
    def _generate_technology_queries(self, job_desc: JobDescription) -> List[Dict[str, Any]]:
        """Generate technology stack-based queries"""
        queries = []
        
        # Group skills by category
        skill_groups = self._group_skills_by_category(job_desc.skills_mentioned)
        
        for category, skills in skill_groups.items():
            if len(skills) >= 2:  # Need at least 2 skills in category
                query_text = ' '.join(skills[:3])  # Max 3 skills per query
                queries.append({
                    'query': query_text,
                    'type': 'technology_stack',
                    'category': category,
                    'priority': 0.9,
                    'skills_count': len(skills),
                    'description': f"{category.replace('_', ' ').title()}: {', '.join(skills[:3])}"
                })
        
        return queries
    
    def _generate_responsibility_queries(self, job_desc: JobDescription) -> List[Dict[str, Any]]:
        """Generate responsibility-based queries"""
        queries = []
        
        for i, responsibility in enumerate(job_desc.responsibilities[:3]):
            # Extract key action words and concepts
            key_phrases = self._extract_action_phrases(responsibility)
            if key_phrases:
                query_text = ' '.join(key_phrases[:4])  # Max 4 phrases
                queries.append({
                    'query': query_text,
                    'type': 'responsibility',
                    'priority': 0.8 - (i * 0.1),  # Decreasing priority
                    'original_text': responsibility[:100] + '...' if len(responsibility) > 100 else responsibility,
                    'description': f"Responsibility {i+1}: {query_text}"
                })
        
        return queries
    
    def _generate_experience_level_queries(self, job_desc: JobDescription) -> List[Dict[str, Any]]:
        """Generate experience level-based queries"""
        queries = []
        
        # Look for experience indicators in text
        experience_indicators = self._extract_experience_indicators(job_desc.full_text)
        
        if experience_indicators:
            for indicator in experience_indicators[:2]:  # Max 2 experience queries
                # Combine with top skills
                top_skills = job_desc.skills_mentioned[:3]
                if top_skills:
                    query_text = f"{indicator} {' '.join(top_skills)}"
                    queries.append({
                        'query': query_text,
                        'type': 'experience_level',
                        'priority': 0.7,
                        'experience_indicator': indicator,
                        'description': f"Experience level: {query_text}"
                    })
        
        return queries
    
    def _generate_industry_queries(self, job_desc: JobDescription) -> List[Dict[str, Any]]:
        """Generate industry-specific queries"""
        queries = []
        
        # Infer industry from job description
        industry_terms = self._infer_industry_context(job_desc)
        
        if industry_terms:
            # Combine industry terms with technical skills
            top_skills = job_desc.skills_mentioned[:3]
            if top_skills:
                query_text = f"{' '.join(industry_terms)} {' '.join(top_skills)}"
                queries.append({
                    'query': query_text,
                    'type': 'industry_context',
                    'priority': 0.6,
                    'industry_terms': industry_terms,
                    'description': f"Industry context: {' '.join(industry_terms)}"
                })
        
        return queries
    
    def _generate_keyword_queries(self, job_desc: JobDescription) -> List[Dict[str, Any]]:
        """Generate keyword-based queries"""
        queries = []
        
        # Combine extracted keywords with skills
        all_keywords = job_desc.extracted_keywords + job_desc.skills_mentioned
        keyword_scores = self._score_keywords(all_keywords, job_desc.full_text)
        
        # Create queries from high-scoring keyword combinations
        top_keywords = [kw for kw, score in keyword_scores[:6]]
        
        if len(top_keywords) >= 3:
            # Create 2-3 keyword combinations
            for i in range(0, len(top_keywords), 3):
                keyword_group = top_keywords[i:i+3]
                if len(keyword_group) >= 2:
                    query_text = ' '.join(keyword_group)
                    queries.append({
                        'query': query_text,
                        'type': 'keyword_combination',
                        'priority': 0.5,
                        'keywords': keyword_group,
                        'description': f"Keywords: {', '.join(keyword_group)}"
                    })
        
        return queries
    
    def _group_skills_by_category(self, skills: List[str]) -> Dict[str, List[str]]:
        """Group skills by technical category"""
        grouped = {}
        
        for skill in skills:
            skill_lower = skill.lower()
            for category, category_skills in self.skill_categories.items():
                if skill_lower in category_skills:
                    if category not in grouped:
                        grouped[category] = []
                    grouped[category].append(skill)
                    break
        
        return grouped
    
    def _extract_action_phrases(self, text: str) -> List[str]:
        """Extract key action phrases from responsibility text"""
        # Common action words in job responsibilities
        action_patterns = [
            r'\b(develop|design|implement|build|create|manage|lead|coordinate)\s+([^,\n.]+)',
            r'\b(work\s+with|collaborate\s+with|partner\s+with)\s+([^,\n.]+)',
            r'\b(responsible\s+for|accountable\s+for)\s+([^,\n.]+)',
            r'\b(analyze|optimize|improve|enhance)\s+([^,\n.]+)'
        ]
        
        phrases = []
        for pattern in action_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                phrase = match.group(0).strip()
                # Clean and limit phrase length
                cleaned_phrase = re.sub(r'\s+', ' ', phrase)[:50]
                if len(cleaned_phrase) > 10:
                    phrases.append(cleaned_phrase)
        
        return phrases[:5]  # Max 5 phrases
    
    def _extract_experience_indicators(self, text: str) -> List[str]:
        """Extract experience level indicators from text"""
        indicators = []
        
        # Experience patterns
        exp_patterns = [
            r'(\d+\+?\s*years?\s*(?:of\s*)?(?:experience|exp))',
            r'(senior|lead|principal|staff|junior|entry[- ]?level)',
            r'(expert|proficient|experienced|skilled|beginner)'
        ]
        
        for pattern in exp_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            indicators.extend([match.lower() if isinstance(match, str) else match[0].lower() 
                             for match in matches])
        
        # Deduplicate and clean
        unique_indicators = []
        seen = set()
        for indicator in indicators:
            if indicator not in seen and len(indicator) > 2:
                unique_indicators.append(indicator)
                seen.add(indicator)
        
        return unique_indicators[:3]  # Max 3 indicators
    
    def _infer_industry_context(self, job_desc: JobDescription) -> List[str]:
        """Infer industry context from job description"""
        industry_keywords = {
            'fintech': ['finance', 'fintech', 'banking', 'payment', 'trading', 'investment'],
            'healthcare': ['health', 'medical', 'healthcare', 'clinical', 'patient', 'pharma'],
            'ecommerce': ['ecommerce', 'retail', 'marketplace', 'shopping', 'commerce'],
            'gaming': ['gaming', 'game', 'entertainment', 'mobile', 'console'],
            'enterprise': ['enterprise', 'b2b', 'saas', 'platform', 'business'],
            'media': ['media', 'content', 'publishing', 'streaming', 'video'],
            'security': ['security', 'cybersecurity', 'privacy', 'compliance', 'audit']
        }
        
        text_analysis = f"{job_desc.company} {job_desc.title} {job_desc.summary}".lower()
        
        detected_industries = []
        for industry, keywords in industry_keywords.items():
            if any(keyword in text_analysis for keyword in keywords):
                detected_industries.append(industry)
        
        return detected_industries[:2]  # Max 2 industries
    
    def _score_keywords(self, keywords: List[str], full_text: str) -> List[Tuple[str, float]]:
        """Score keywords by importance in the job description"""
        keyword_scores = []
        text_lower = full_text.lower()
        
        for keyword in keywords:
            if not keyword:
                continue
                
            keyword_lower = keyword.lower()
            
            # Base score from frequency
            frequency = text_lower.count(keyword_lower)
            score = frequency * 0.1
            
            # Boost score for technical terms
            if self._is_technical_term(keyword):
                score += 0.5
            
            # Boost score for skills in categories
            if any(keyword_lower in skills for skills in self.skill_categories.values()):
                score += 0.3
            
            # Boost score for longer terms (likely more specific)
            if len(keyword) > 6:
                score += 0.2
            
            keyword_scores.append((keyword, score))
        
        return sorted(keyword_scores, key=lambda x: x[1], reverse=True)
    
    def _is_technical_term(self, term: str) -> bool:
        """Check if term is likely technical"""
        term_lower = term.lower()
        
        # Check if it's in our skill categories
        for skills in self.skill_categories.values():
            if term_lower in skills:
                return True
        
        # Check patterns that suggest technical terms
        technical_patterns = [
            r'\b[A-Z]{2,}\b',  # Acronyms
            r'\w+\.\w+',       # Terms with dots (Node.js, Vue.js)
            r'\w+[-_]\w+',     # Hyphenated/underscored terms
        ]
        
        for pattern in technical_patterns:
            if re.match(pattern, term):
                return True
        
        return False
    
    def _rank_and_filter_queries(self, queries: List[Dict[str, Any]], 
                                max_queries: int) -> List[Dict[str, Any]]:
        """Rank queries by priority and filter to max count"""
        if not queries:
            return []
        
        # Sort by priority (higher first)
        sorted_queries = sorted(queries, key=lambda q: q.get('priority', 0), reverse=True)
        
        # Remove duplicates while preserving order
        unique_queries = []
        seen_queries = set()
        
        for query in sorted_queries:
            query_text = query['query'].lower()
            if query_text not in seen_queries:
                unique_queries.append(query)
                seen_queries.add(query_text)
                
                if len(unique_queries) >= max_queries:
                    break
        
        # Add final ranking and metadata
        for i, query in enumerate(unique_queries):
            query['rank'] = i + 1
            query['final_priority'] = query.get('priority', 0) * (1 - i * 0.05)  # Slight penalty for lower ranks
        
        self.logger.debug(f"Ranked and filtered to {len(unique_queries)} queries")
        return unique_queries


def create_search_optimizer(enable_diversity: bool = True) -> SearchQueryOptimizer:
    """
    Factory function to create search optimizer
    
    Args:
        enable_diversity: Whether to generate diverse query types
        
    Returns:
        Configured SearchQueryOptimizer instance
    """
    optimizer = SearchQueryOptimizer(enable_diversity)
    logger.info("SearchQueryOptimizer created successfully")
    return optimizer 