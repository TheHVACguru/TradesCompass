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
from config import Config

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
        Search for candidates using multiple data sources
        
        Args:
            job_title: Target job title/role
            location: Target location
            skills: Required skills
            experience_years: Minimum years of experience
        
        Returns:
            List of candidate profiles from multiple sources, deduplicated
        """
        all_candidates = []
        
        # Build search query
        query_parts = [job_title]
        if location:
            query_parts.append(location)
        if skills:
            query_parts.extend(skills[:3])  # Top 3 skills
        
        search_query = ' '.join(query_parts)
        
        # Search using multiple providers
        providers = [
            ('GitHub', self._search_github_profiles),
            ('PeopleDataLabs', self._search_peopledata),
            ('SeekOut', self._search_seekout),
            ('SourceHub', self._search_sourcehub)
        ]
        
        sources_searched = []
        for provider_name, search_method in providers:
            try:
                self.logger.info(f"Searching {provider_name} for: {search_query}")
                candidates = search_method(search_query, location, skills)
                if candidates:
                    all_candidates.extend(candidates)
                    sources_searched.append(provider_name)
                    self.logger.info(f"Found {len(candidates)} candidates from {provider_name}")
            except Exception as e:
                self.logger.error(f"Error searching {provider_name}: {e}")
        
        # Deduplicate candidates by email or name
        deduped_candidates = self._deduplicate_candidates(all_candidates)
        
        # Add metadata about sources searched
        for candidate in deduped_candidates:
            candidate['sources_searched'] = sources_searched
        
        return deduped_candidates
    
    def _search_github_profiles(self, query: str, location: str = None, skills: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search GitHub for developer profiles (public data)
        """
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
                    if Config.GITHUB_TOKEN:
                        headers['Authorization'] = f'token {Config.GITHUB_TOKEN}'
                    
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
                                'skills': [skill],
                                'location': location or 'Not specified'
                            }
                            candidates.append(candidate)
        
        except Exception as e:
            self.logger.error(f"Error searching GitHub profiles: {e}")
        
        return candidates
    
    def _search_peopledata(self, query: str, location: str = None, skills: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search PeopleDataLabs for candidate profiles
        """
        if not Config.PEOPLEDATA_KEY:
            self.logger.warning('PEOPLEDATA_KEY is not set - skipping PeopleDataLabs search')
            return []
        
        candidates = []
        try:
            # Build search parameters
            params = {
                'api_key': Config.PEOPLEDATA_KEY,
                'query': query,
                'size': 10  # Limit results
            }
            
            if location:
                params['location'] = location
            
            if skills:
                params['skills'] = ','.join(skills[:5])  # Include top 5 skills
            
            # Make API request
            response = requests.get(
                'https://api.peopledatalabs.com/v5/person/search',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for person in data.get('data', []):
                    candidate = {
                        'source': 'PeopleDataLabs',
                        'first_name': person.get('first_name', ''),
                        'last_name': person.get('last_name', ''),
                        'name': person.get('full_name', ''),
                        'email': person.get('email', ''),
                        'phone': person.get('phone', ''),
                        'location': person.get('location', {}).get('name', location or ''),
                        'title': person.get('job_title', ''),
                        'company': person.get('job_company_name', ''),
                        'skills': person.get('skills', []),
                        'summary': person.get('summary', ''),
                        'experience': person.get('experience', []),
                        'education': person.get('education', []),
                        'linkedin_url': person.get('linkedin_url', ''),
                        'estimated_fit': self._estimate_fit_score(person, query, skills)
                    }
                    candidates.append(candidate)
            elif response.status_code == 401:
                self.logger.error('PeopleDataLabs API key is invalid')
            elif response.status_code == 429:
                self.logger.warning('PeopleDataLabs rate limit exceeded')
            else:
                self.logger.error(f'PeopleDataLabs API error: {response.status_code}')
        
        except Exception as e:
            self.logger.error(f"Error searching PeopleDataLabs: {e}")
        
        return candidates
    
    def _search_seekout(self, query: str, location: str = None, skills: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search SeekOut for candidate profiles
        """
        if not Config.SEEKOUT_API_KEY:
            self.logger.warning('SEEKOUT_API_KEY is not set - skipping SeekOut search')
            return []
        
        candidates = []
        try:
            # Build search request
            headers = {
                'Authorization': f'Bearer {Config.SEEKOUT_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            search_data = {
                'query': query,
                'filters': {
                    'location': location,
                    'skills': skills[:5] if skills else [],
                    'actively_looking': True  # Focus on active job seekers
                },
                'limit': 10
            }
            
            # Make API request
            response = requests.post(
                'https://api.seekout.com/v1/talent/search',
                headers=headers,
                json=search_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for profile in data.get('profiles', []):
                    candidate = {
                        'source': 'SeekOut',
                        'first_name': profile.get('firstName', ''),
                        'last_name': profile.get('lastName', ''),
                        'name': f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip(),
                        'email': profile.get('email', ''),
                        'phone': profile.get('phoneNumber', ''),
                        'location': profile.get('location', location or ''),
                        'title': profile.get('currentTitle', ''),
                        'company': profile.get('currentCompany', ''),
                        'skills': profile.get('skills', []),
                        'summary': profile.get('bio', ''),
                        'linkedin_url': profile.get('linkedinUrl', ''),
                        'github_url': profile.get('githubUrl', ''),
                        'experience_years': profile.get('yearsOfExperience', 0),
                        'estimated_fit': self._estimate_fit_score(profile, query, skills)
                    }
                    candidates.append(candidate)
            elif response.status_code == 401:
                self.logger.error('SeekOut API key is invalid')
            elif response.status_code == 429:
                self.logger.warning('SeekOut rate limit exceeded')
            else:
                self.logger.error(f'SeekOut API error: {response.status_code}')
        
        except Exception as e:
            self.logger.error(f"Error searching SeekOut: {e}")
        
        return candidates
    
    def _search_sourcehub(self, query: str, location: str = None, skills: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search SourceHub for candidate profiles
        """
        if not Config.SOURCEHUB_API_KEY:
            self.logger.warning('SOURCEHUB_API_KEY is not set - skipping SourceHub search')
            return []
        
        candidates = []
        try:
            # Build search parameters
            headers = {
                'X-API-Key': Config.SOURCEHUB_API_KEY,
                'Accept': 'application/json'
            }
            
            params = {
                'q': query,
                'location': location,
                'skills': ','.join(skills[:5]) if skills else '',
                'limit': 10,
                'active_only': 'true'  # Focus on active candidates
            }
            
            # Make API request
            response = requests.get(
                'https://api.sourcehub.com/v1/candidates/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for candidate_data in data.get('candidates', []):
                    candidate = {
                        'source': 'SourceHub',
                        'first_name': candidate_data.get('first_name', ''),
                        'last_name': candidate_data.get('last_name', ''),
                        'name': candidate_data.get('full_name', ''),
                        'email': candidate_data.get('email', ''),
                        'phone': candidate_data.get('phone', ''),
                        'location': candidate_data.get('location', location or ''),
                        'title': candidate_data.get('job_title', ''),
                        'company': candidate_data.get('company', ''),
                        'skills': candidate_data.get('skills', []),
                        'summary': candidate_data.get('summary', ''),
                        'resume_text': candidate_data.get('resume_snippet', ''),
                        'linkedin_url': candidate_data.get('linkedin', ''),
                        'availability': candidate_data.get('availability', 'Unknown'),
                        'salary_expectation': candidate_data.get('salary_range', ''),
                        'estimated_fit': self._estimate_fit_score(candidate_data, query, skills)
                    }
                    candidates.append(candidate)
            elif response.status_code == 401:
                self.logger.error('SourceHub API key is invalid')
            elif response.status_code == 429:
                self.logger.warning('SourceHub rate limit exceeded')
            else:
                self.logger.error(f'SourceHub API error: {response.status_code}')
        
        except Exception as e:
            self.logger.error(f"Error searching SourceHub: {e}")
        
        return candidates
    
    def _estimate_fit_score(self, candidate_data: Dict, query: str, required_skills: List[str] = None) -> float:
        """
        Estimate a fit score for a candidate based on available data
        """
        score = 5.0  # Base score
        
        # Check job title match
        if candidate_data.get('title') or candidate_data.get('job_title'):
            title = (candidate_data.get('title') or candidate_data.get('job_title', '')).lower()
            if query.lower() in title:
                score += 2.0
        
        # Check skills match
        if required_skills and candidate_data.get('skills'):
            candidate_skills = [s.lower() for s in candidate_data.get('skills', [])]
            matched_skills = sum(1 for skill in required_skills if skill.lower() in candidate_skills)
            score += min(matched_skills * 0.5, 2.0)  # Max 2 points for skills
        
        # Check experience
        if candidate_data.get('yearsOfExperience') or candidate_data.get('experience_years'):
            years = candidate_data.get('yearsOfExperience') or candidate_data.get('experience_years', 0)
            if years >= 5:
                score += 1.0
        
        return min(score, 10.0)  # Cap at 10
    
    def _deduplicate_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate candidates by email or name
        """
        seen_emails = set()
        seen_names = set()
        unique_candidates = []
        
        for candidate in candidates:
            # Check email uniqueness
            email = candidate.get('email', '').lower().strip()
            if email and email in seen_emails:
                continue
            
            # Check name uniqueness (for candidates without email)
            name = candidate.get('name', '').lower().strip()
            if not email and name and name in seen_names:
                continue
            
            # Add to unique list
            if email:
                seen_emails.add(email)
            if name:
                seen_names.add(name)
            
            unique_candidates.append(candidate)
        
        return unique_candidates
    
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
        
        # Trades-specific skill keywords
        skill_patterns = [
            # Construction
            'framing', 'drywall', 'concrete', 'masonry', 'roofing', 'siding', 'flooring',
            'carpentry', 'demolition', 'excavation', 'foundation', 'steel erection', 'scaffolding',
            # HVAC
            'hvac installation', 'hvac repair', 'ductwork', 'refrigeration', 'heat pump', 
            'air conditioning', 'furnace', 'boiler', 'ventilation', 'sheet metal', 'brazing',
            # Electrical
            'electrical wiring', 'panel installation', 'circuit breaker', 'conduit', 'voltage',
            'residential electrical', 'commercial electrical', 'industrial electrical', 'troubleshooting',
            # Plumbing
            'pipe fitting', 'soldering', 'drain cleaning', 'water heater', 'fixture installation',
            'pex', 'copper', 'pvc', 'sewage', 'gas line', 'backflow prevention',
            # Windows/Doors/Hurricane
            'window installation', 'door installation', 'hurricane shutters', 'impact windows',
            'sliding doors', 'garage doors', 'storm doors', 'weatherproofing', 'caulking',
            # General skills
            'blueprint reading', 'osha compliance', 'power tools', 'hand tools', 'measuring',
            'safety protocols', 'code compliance', 'permit', 'inspection', 'estimation'
        ]
        
        # Education patterns for trades
        education_patterns = [
            'trade school', 'vocational', 'apprenticeship', 'journeyman', 'master',
            'technical college', 'community college', 'certification program'
        ]
        
        # Trades certification patterns
        cert_patterns = [
            'osha 10', 'osha 30', 'epa certified', 'nate certified', 'journeyman license',
            'master license', 'contractor license', 'electrical license', 'plumbing license',
            'hvac license', 'cfc certification', 'backflow certification', 'welding certification',
            'forklift certified', 'boom lift certified', 'scissor lift certified'
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


# Standalone function for external candidate search (used by routes.py)
def search_external_candidates(query: str, 
                              location: str = None,
                              skills: List[str] = None,
                              limit: int = 20) -> Dict[str, Any]:
    """
    Search for external candidates through public sources
    
    Args:
        query: Search query string (job title or keywords)
        location: Target location
        skills: List of required skills
        limit: Maximum number of results
    
    Returns:
        Dictionary containing candidates, total found, and sources searched
    """
    sourcing_service = CandidateSourcingService()
    
    # Extract job title from query (use the query as job title)
    job_title = query
    
    # Search public profiles
    candidates = sourcing_service.search_public_profiles(
        job_title=job_title,
        location=location,
        skills=skills,
        experience_years=None  # Could be extracted from query if needed
    )
    
    # Limit results
    limited_candidates = candidates[:limit] if len(candidates) > limit else candidates
    
    return {
        'candidates': limited_candidates,
        'total_found': len(limited_candidates),
        'sources_searched': ['GitHub', 'Public Profiles']
    }