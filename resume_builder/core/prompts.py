"""
Prompt engineering for AI-powered experience refinement
"""

from typing import Dict, List, Optional
from ..models.job_description import JobDescription
from ..models.experience import Experience


class PromptTemplates:
    """Collection of prompt templates for experience refinement"""
    
    # System prompts for different refinement types
    EXPERIENCE_REFINEMENT_SYSTEM = """
You are an expert resume writer and career coach. Your job is to take raw professional experiences and transform them into polished, compelling resume accomplishments that highlight impact, quantifiable results, and relevant skills.

Guidelines:
1. Use action verbs and quantifiable metrics whenever possible
2. Focus on achievements and outcomes, not just responsibilities
3. Tailor language to be professional yet engaging
4. Highlight leadership, problem-solving, and technical skills
5. Use bullet points for clarity and readability
6. Keep each accomplishment concise but impactful (1-2 lines max)
7. Ensure all claims are truthful and based on the original experience

Output format: Return a JSON object with:
{
    "refined_accomplishments": ["accomplishment 1", "accomplishment 2", ...],
    "key_skills": ["skill1", "skill2", ...],
    "tools_technologies": ["tool1", "tool2", ...],
    "impact_metrics": ["metric1", "metric2", ...],
    "confidence_score": 0.0-1.0
}
"""

    SKILLS_EXTRACTION_SYSTEM = """
You are an expert at identifying professional skills and technologies from work experiences. Extract both technical and soft skills mentioned or implied in the experience description.

Guidelines:
1. Include both explicitly mentioned and reasonably inferred skills
2. Categorize as technical skills, soft skills, and tools/technologies
3. Use industry-standard terminology
4. Be comprehensive but relevant
5. Consider transferable skills

Output format: Return a JSON object with:
{
    "technical_skills": ["skill1", "skill2", ...],
    "soft_skills": ["skill1", "skill2", ...],
    "tools_technologies": ["tool1", "tool2", ...],
    "certifications": ["cert1", "cert2", ...],
    "methodologies": ["method1", "method2", ...]
}
"""

    JOB_SPECIFIC_REFINEMENT_SYSTEM = """
You are an expert resume writer specializing in tailoring experiences to specific job requirements. Your task is to refine professional experiences to align with a target job description while maintaining truthfulness.

Guidelines:
1. Emphasize skills and experiences most relevant to the target job
2. Use terminology and keywords from the job description when appropriate
3. Highlight transferable skills that match job requirements
4. Quantify achievements that demonstrate required competencies
5. Structure accomplishments to showcase job-relevant strengths
6. Maintain authenticity - don't invent experiences or exaggerate

Target Job Context:
- Position: {job_title}
- Company: {company}
- Key Requirements: {key_skills}
- Industry: {industry}

Output format: Return a JSON object with:
{
    "tailored_accomplishments": ["accomplishment 1", "accomplishment 2", ...],
    "relevant_skills": ["skill1", "skill2", ...],
    "matching_keywords": ["keyword1", "keyword2", ...],
    "relevance_score": 0.0-1.0,
    "tailoring_notes": "explanation of key changes made"
}
"""


class PromptBuilder:
    """Dynamic prompt builder for experience refinement"""
    
    def __init__(self):
        self.templates = PromptTemplates()
    
    def build_experience_refinement_prompt(
        self, 
        experience: Experience,
        refinement_type: str = "general",
        job_context: Optional[JobDescription] = None
    ) -> str:
        """
        Build prompt for experience refinement
        
        Args:
            experience: Raw experience to refine
            refinement_type: Type of refinement ("general", "job_specific", "skills_focused")
            job_context: Job description for job-specific refinement
            
        Returns:
            Complete prompt for OpenAI
        """
        if refinement_type == "job_specific" and job_context:
            system_prompt = self.templates.JOB_SPECIFIC_REFINEMENT_SYSTEM.format(
                job_title=job_context.title,
                company=job_context.company,
                key_skills=", ".join(job_context.skills_mentioned[:10]),  # Top 10 skills
                industry=job_context.inferred_industry or "Technology"
            )
        else:
            system_prompt = self.templates.EXPERIENCE_REFINEMENT_SYSTEM
        
        user_prompt = self._create_experience_user_prompt(experience, job_context)
        
        return f"{system_prompt}\n\nUser Input:\n{user_prompt}"
    
    def build_skills_extraction_prompt(self, experience: Experience) -> str:
        """
        Build prompt for skills extraction
        
        Args:
            experience: Experience to extract skills from
            
        Returns:
            Complete prompt for skills extraction
        """
        system_prompt = self.templates.SKILLS_EXTRACTION_SYSTEM
        
        user_prompt = f"""
Experience to analyze:
Company: {experience.company}
Role: {experience.role or 'Not specified'}
Duration: {experience.duration or 'Not specified'}

Description:
{experience.text}

Extract all relevant skills, technologies, and competencies demonstrated in this experience.
"""
        
        return f"{system_prompt}\n\nUser Input:\n{user_prompt}"
    
    def build_batch_refinement_prompt(
        self, 
        experiences: List[Experience],
        job_context: Optional[JobDescription] = None
    ) -> str:
        """
        Build prompt for batch experience refinement
        
        Args:
            experiences: List of experiences to refine
            job_context: Optional job context for tailoring
            
        Returns:
            Complete batch refinement prompt
        """
        system_prompt = """
You are refining multiple professional experiences for a resume. Process each experience separately and provide refined accomplishments for each.

Guidelines:
1. Maintain consistency in writing style across all experiences
2. Avoid repetition of similar accomplishments
3. Ensure each experience contributes unique value
4. Rank experiences by relevance if job context is provided

Output format: Return a JSON object with:
{
    "refined_experiences": [
        {
            "original_index": 0,
            "company": "company name",
            "refined_accomplishments": ["accomplishment 1", "accomplishment 2"],
            "key_skills": ["skill1", "skill2"],
            "relevance_score": 0.0-1.0
        }
    ],
    "overall_skills": ["consolidated skill list"],
    "recommendations": "suggestions for improvement"
}
"""
        
        user_prompt = "Experiences to refine:\n\n"
        for i, exp in enumerate(experiences):
            user_prompt += f"Experience {i+1}:\n"
            user_prompt += f"Company: {exp.company}\n"
            user_prompt += f"Role: {exp.role or 'Not specified'}\n"
            user_prompt += f"Text: {exp.text}\n\n"
        
        if job_context:
            user_prompt += f"\nTarget Job Context:\n"
            user_prompt += f"Position: {job_context.title}\n"
            user_prompt += f"Company: {job_context.company}\n"
            user_prompt += f"Key Requirements: {', '.join(job_context.skills_mentioned[:10])}\n"
        
        return f"{system_prompt}\n\nUser Input:\n{user_prompt}"
    
    def _create_experience_user_prompt(
        self, 
        experience: Experience,
        job_context: Optional[JobDescription] = None
    ) -> str:
        """Create user prompt section for experience refinement"""
        
        prompt = f"""
Raw Experience:
Company: {experience.company}
Role: {experience.role or 'Not specified'}
Duration: {experience.duration or 'Not specified'}
Category: {', '.join(experience.categories) if experience.categories else 'Not specified'}

Description:
{experience.text}

Current Skills: {', '.join(experience.skills) if experience.skills else 'None identified'}
"""
        
        if job_context:
            prompt += f"""

Target Job Requirements:
Position: {job_context.title}
Company: {job_context.company}
Key Skills Needed: {', '.join(job_context.skills_mentioned[:10])}
Required Keywords: {', '.join(job_context.extracted_keywords[:10])}
"""
        
        prompt += "\nPlease refine this experience into compelling resume accomplishments."
        
        return prompt


class PromptOptimizer:
    """Optimizes prompts for token efficiency and effectiveness"""
    
    @staticmethod
    def optimize_for_tokens(prompt: str, max_tokens: int = 3000) -> str:
        """
        Optimize prompt to fit within token limits
        
        Args:
            prompt: Original prompt
            max_tokens: Maximum token limit (rough estimation)
            
        Returns:
            Optimized prompt
        """
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(prompt) <= max_chars:
            return prompt
        
        # Truncate user input section while preserving system prompt
        lines = prompt.split('\n')
        system_lines = []
        user_lines = []
        in_user_section = False
        
        for line in lines:
            if "User Input:" in line:
                in_user_section = True
                user_lines.append(line)
            elif in_user_section:
                user_lines.append(line)
            else:
                system_lines.append(line)
        
        system_prompt = '\n'.join(system_lines)
        user_prompt = '\n'.join(user_lines)
        
        # If system prompt itself is too long, we have a problem
        if len(system_prompt) > max_chars * 0.7:
            return prompt[:max_chars]
        
        # Truncate user prompt to fit
        available_chars = max_chars - len(system_prompt) - 100  # Buffer
        if len(user_prompt) > available_chars:
            user_prompt = user_prompt[:available_chars] + "\n...[truncated]"
        
        return system_prompt + '\n' + user_prompt
    
    @staticmethod
    def validate_prompt_structure(prompt: str) -> Dict[str, bool]:
        """
        Validate prompt structure and completeness
        
        Args:
            prompt: Prompt to validate
            
        Returns:
            Validation results
        """
        return {
            "has_system_instructions": "Guidelines:" in prompt or "You are" in prompt,
            "has_output_format": "Output format:" in prompt or "Return a JSON" in prompt,
            "has_user_input": "User Input:" in prompt or "Experience" in prompt,
            "reasonable_length": 500 <= len(prompt) <= 8000,
            "has_json_structure": "{" in prompt and "}" in prompt
        }


# Predefined prompt variations for different scenarios
PROMPT_VARIATIONS = {
    "entry_level": {
        "system_addition": "\nNote: This is for an entry-level professional. Focus on potential, learning ability, and transferable skills from internships, projects, or part-time work.",
        "emphasis": ["learning", "potential", "enthusiasm", "foundational skills"]
    },
    
    "senior_level": {
        "system_addition": "\nNote: This is for a senior professional. Emphasize leadership, strategic impact, mentoring, and advanced technical expertise.",
        "emphasis": ["leadership", "strategy", "mentoring", "expertise", "business impact"]
    },
    
    "career_change": {
        "system_addition": "\nNote: This person is changing careers. Focus on transferable skills and relevant experiences that apply to the new field.",
        "emphasis": ["transferable skills", "adaptability", "relevant experience", "cross-functional"]
    },
    
    "technical_role": {
        "system_addition": "\nNote: This is for a technical role. Emphasize technical skills, methodologies, tools, and quantifiable technical achievements.",
        "emphasis": ["technical skills", "tools", "methodologies", "systems", "performance"]
    },
    
    "management_role": {
        "system_addition": "\nNote: This is for a management role. Focus on team leadership, project management, decision-making, and business results.",
        "emphasis": ["leadership", "management", "decision-making", "business results", "team building"]
    }
}


def get_specialized_prompt(
    base_prompt: str, 
    specialization: str,
    job_level: str = "mid_level"
) -> str:
    """
    Get specialized prompt based on role type and level
    
    Args:
        base_prompt: Base prompt template
        specialization: Type of specialization needed
        job_level: Level of the position
        
    Returns:
        Specialized prompt
    """
    variations = PROMPT_VARIATIONS.get(specialization, {})
    level_variations = PROMPT_VARIATIONS.get(job_level, {})
    
    specialized_prompt = base_prompt
    
    # Add specialization-specific instructions
    if "system_addition" in variations:
        specialized_prompt += variations["system_addition"]
    
    if "system_addition" in level_variations:
        specialized_prompt += level_variations["system_addition"]
    
    return specialized_prompt 