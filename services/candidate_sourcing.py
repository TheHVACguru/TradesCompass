"""
Candidate Sourcing Service for TalentCompass AI
Provides legitimate methods to source external candidates
"""

import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import db, ResumeAnalysis, CandidateSkill

class CandidateSourcingService:
    """Service for sourcing external candidates through legitimate channels"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def search_public_profiles(self, 
                              job_title: str, 
                              location: str = None,
                              skills: List[str] = None,
                              experience_years: int = None) -> List[Dict[str, Any]]:
        """
        Search for candidates using public data sources
        
        Args:
            job_title: Target job title/role
            location: Target location
            skills: Required skills
            experience_years: Minimum years of experience
        
        Returns:
            List of candidate profiles from public sources
        """
        candidates = []
        
        # Build search query
        query_parts = [job_title]
        if location:
            query_parts.append(location)
        if skills:
            query_parts.extend(skills[:3])  # Top 3 skills
        
        search_query = ' '.join(query_parts)
        
        # Search using GitHub Jobs API (if available)
        github_candidates = self._search_github_profiles(search_query, skills)
        candidates.extend(github_candidates)
        
        # Search using other public APIs
        # Note: Many APIs require authentication
        
        return candidates
    
    def _search_github_profiles(self, query: str, skills: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search GitHub for developer profiles (public data)
        """
        import os
        candidates = []
        
        try:
            # GitHub search API (public repositories and users)
            # This searches for users with specific languages/skills
            if skills:
                for skill in skills[:2]:  # Limit to avoid rate limiting
                    search_url = f"https://api.github.com/search/users"
                    params = {
                        'q': f"{skill} language:{skill}",
                        'per_page': 5
                    }
                    
                    headers = {
                        'Accept': 'application/vnd.github.v3+json'
                    }
                    
                    # Add GitHub token if available for higher rate limits
                    github_token = os.environ.get('GITHUB_TOKEN')
                    if github_token:
                        headers['Authorization'] = f'token {github_token}'
                    
                    response = requests.get(search_url, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        for user in data.get('items', []):
                            candidate = {
                                'source': 'GitHub',
                                'profile_url': user.get('html_url'),
                                'username': user.get('login'),
                                'avatar_url': user.get('avatar_url'),
                                'type': 'Developer',
                                'skills': [skill]
                            }
                            candidates.append(candidate)
        
        except Exception as e:
            self.logger.error(f"Error searching GitHub profiles: {e}")
        
        return candidates
    
    def import_candidate_profile(self, profile_data: Dict[str, Any]) -> Optional[ResumeAnalysis]:
        """
        Import an external candidate profile into the system
        
        Args:
            profile_data: Dictionary containing candidate information
        
        Returns:
            Created ResumeAnalysis object or None
        """
        try:
            # Extract basic information
            first_name = profile_data.get('first_name', '')
            last_name = profile_data.get('last_name', '')
            email = profile_data.get('email', '')
            
            # Check if candidate already exists
            if email:
                existing = ResumeAnalysis.query.filter_by(email=email).first()
                if existing:
                    self.logger.info(f"Candidate already exists: {email}")
                    return existing
            
            # Create profile summary
            profile_summary = self._create_profile_summary(profile_data)
            
            # Create new candidate record
            candidate = ResumeAnalysis(
                first_name=first_name,
                last_name=last_name,
                email=email or f"{first_name.lower()}.{last_name.lower()}@sourced.example.com",
                phone=profile_data.get('phone', ''),
                location=profile_data.get('location', ''),
                resume_text=profile_summary,
                source='external_sourcing',
                status='sourced',
                filename=f"sourced_profile_{datetime.utcnow().timestamp()}.txt",
                upload_date=datetime.utcnow()
            )
            
            # Set default values for now
            # Could integrate with AI analysis later if needed
            candidate.candidate_strengths = json.dumps(["To be analyzed"])
            candidate.candidate_weaknesses = json.dumps(["To be analyzed"])
            candidate.overall_fit_rating = 5.0
            
            db.session.add(candidate)
            db.session.flush()
            
            # Add skills
            skills = profile_data.get('skills', [])
            for skill_name in skills:
                skill = CandidateSkill(
                    candidate_id=candidate.id,
                    skill_name=skill_name,
                    skill_level='unknown'
                )
                db.session.add(skill)
            
            db.session.commit()
            return candidate
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error importing candidate profile: {e}")
            return None
    
    def _create_profile_summary(self, profile_data: Dict[str, Any]) -> str:
        """Create a text summary from profile data"""
        parts = []
        
        # Name and title
        if profile_data.get('first_name'):
            parts.append(f"Name: {profile_data.get('first_name')} {profile_data.get('last_name', '')}")
        
        if profile_data.get('title'):
            parts.append(f"Current Role: {profile_data.get('title')}")
        
        if profile_data.get('company'):
            parts.append(f"Company: {profile_data.get('company')}")
        
        if profile_data.get('location'):
            parts.append(f"Location: {profile_data.get('location')}")
        
        # Experience
        if profile_data.get('experience'):
            parts.append(f"\nExperience:\n{profile_data.get('experience')}")
        
        # Skills
        if profile_data.get('skills'):
            skills_text = ', '.join(profile_data.get('skills', []))
            parts.append(f"\nSkills: {skills_text}")
        
        # Education
        if profile_data.get('education'):
            parts.append(f"\nEducation:\n{profile_data.get('education')}")
        
        # Summary
        if profile_data.get('summary'):
            parts.append(f"\nSummary:\n{profile_data.get('summary')}")
        
        return '\n'.join(parts)
    
    def bulk_import_candidates(self, candidates_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk import multiple candidate profiles
        
        Args:
            candidates_data: List of candidate profile dictionaries
        
        Returns:
            Import results summary
        """
        results = {
            'total': len(candidates_data),
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'candidates': []
        }
        
        for profile_data in candidates_data:
            try:
                candidate = self.import_candidate_profile(profile_data)
                if candidate:
                    results['imported'] += 1
                    results['candidates'].append({
                        'id': candidate.id,
                        'name': f"{candidate.first_name} {candidate.last_name}",
                        'email': candidate.email
                    })
                else:
                    results['skipped'] += 1
            except Exception as e:
                results['errors'] += 1
                self.logger.error(f"Error importing candidate: {e}")
        
        return results
    
    def create_sourcing_campaign(self, 
                                job_title: str,
                                requirements: str,
                                location: str = None) -> Dict[str, Any]:
        """
        Create a targeted sourcing campaign
        
        Args:
            job_title: Target job title
            requirements: Job requirements text
            location: Target location
        
        Returns:
            Campaign configuration and search parameters
        """
        # Extract key skills from requirements (simple keyword extraction for now)
        extracted = self._extract_requirements_simple(requirements)
        
        campaign = {
            'job_title': job_title,
            'location': location,
            'created_date': datetime.utcnow().isoformat(),
            'status': 'active',
            'search_parameters': {
                'primary_skills': extracted.get('required_skills', []),
                'nice_to_have_skills': extracted.get('preferred_skills', []),
                'experience_range': extracted.get('experience_range', '3-5 years'),
                'education': extracted.get('education', []),
                'certifications': extracted.get('certifications', [])
            },
            'search_queries': self._generate_search_queries(
                job_title, 
                location,
                extracted.get('required_skills', [])
            )
        }
        
        return campaign
    
    def _generate_search_queries(self, 
                                job_title: str, 
                                location: str,
                                skills: List[str]) -> List[str]:
        """Generate optimized search queries for different platforms"""
        queries = []
        
        # Basic query
        base_query = f'"{job_title}"'
        if location:
            base_query += f' "{location}"'
        queries.append(base_query)
        
        # Skill-focused queries
        for skill in skills[:3]:
            skill_query = f'"{job_title}" "{skill}"'
            if location:
                skill_query += f' "{location}"'
            queries.append(skill_query)
        
        # Boolean search query
        if skills:
            skills_formatted = [f'"{s}"' for s in skills[:3]]
            boolean_query = f'"{job_title}" AND ({" OR ".join(skills_formatted)})'
            if location:
                boolean_query += f' AND "{location}"'
            queries.append(boolean_query)
        
        return queries
    
    def _extract_requirements_simple(self, requirements: str) -> Dict[str, Any]:
        """Simple keyword extraction from requirements text"""
        import re
        
        # Common skill keywords
        skill_patterns = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node.js', 'nodejs', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'sql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'machine learning', 'ai', 'data science', 'analytics',
            'ci/cd', 'devops', 'git', 'agile', 'scrum',
            'flask', 'django', 'spring', 'express', '.net', 'rails'
        ]
        
        # Education patterns
        education_patterns = [
            "bachelor's", "master's", "phd", "computer science", "engineering",
            "mathematics", "statistics", "mba"
        ]
        
        # Certification patterns
        cert_patterns = [
            'aws certified', 'azure certified', 'gcp certified', 'pmp',
            'scrum master', 'cissp', 'comptia', 'cisco'
        ]
        
        requirements_lower = requirements.lower()
        
        # Extract skills
        found_skills = []
        for skill in skill_patterns:
            if skill in requirements_lower:
                found_skills.append(skill.title() if len(skill) > 3 else skill.upper())
        
        # Extract education
        found_education = []
        for edu in education_patterns:
            if edu in requirements_lower:
                found_education.append(edu.title())
        
        # Extract certifications
        found_certs = []
        for cert in cert_patterns:
            if cert in requirements_lower:
                found_certs.append(cert.upper() if len(cert) <= 4 else cert.title())
        
        # Extract experience range (look for patterns like "3-5 years", "5+ years")
        exp_pattern = r'(\d+)[\s\-to]+(\d+)?\s*\+?\s*years?'
        exp_match = re.search(exp_pattern, requirements_lower)
        experience_range = '3-5 years'  # default
        if exp_match:
            if exp_match.group(2):
                experience_range = f"{exp_match.group(1)}-{exp_match.group(2)} years"
            else:
                experience_range = f"{exp_match.group(1)}+ years"
        
        # Classify skills as required vs preferred
        required_keywords = ['required', 'must have', 'essential', 'mandatory']
        preferred_keywords = ['preferred', 'nice to have', 'bonus', 'plus']
        
        required_skills = found_skills[:5] if found_skills else []
        preferred_skills = found_skills[5:] if len(found_skills) > 5 else []
        
        return {
            'required_skills': required_skills,
            'preferred_skills': preferred_skills,
            'experience_range': experience_range,
            'education': found_education,
            'certifications': found_certs
        }