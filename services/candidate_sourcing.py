import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

class CandidateSourcer:
    """
    Service for sourcing new candidates from external APIs
    Uses multiple candidate databases and professional networks
    """
    
    def __init__(self):
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        self.base_headers = {
            'X-RapidAPI-Key': self.rapidapi_key,
            'X-RapidAPI-Host': ''
        }
        
    def search_candidates(
        self, 
        query: str,
        location: str = None,
        skills: List[str] = None,
        experience_level: str = None,
        limit: int = 20,
        include_x: bool = True
    ) -> Dict[str, Any]:
        """
        Search for candidates across multiple professional networks
        
        Args:
            query: Job title or role description
            location: Geographic location
            skills: Required skills
            experience_level: junior, mid, senior, executive
            limit: Number of results to return
            include_x: Whether to include X (Twitter) in search
            
        Returns:
            Dictionary with candidate results from multiple sources
        """
        
        all_candidates = []
        sources_used = []
        
        # Search X (Twitter) for candidates - prioritize this for active job seekers
        if include_x:
            try:
                from services.x_sourcing import search_x_for_candidates
                x_results = search_x_for_candidates(query, skills, location, limit//3)
                x_candidates = x_results.get('candidates', [])
                if x_candidates:
                    all_candidates.extend(x_candidates)
                    sources_used.append('X')
                    logging.info(f"Found {len(x_candidates)} candidates from X")
            except Exception as e:
                logging.error(f"X search error: {str(e)}")
        
        # Search LinkedIn profiles via RapidAPI
        linkedin_results = self._search_linkedin_profiles(query, location, skills, limit//3)
        if linkedin_results:
            all_candidates.extend(linkedin_results)
            sources_used.append('LinkedIn')
        
        # Search GitHub profiles for technical roles
        if any(tech_skill in (skills or []) for tech_skill in ['Python', 'JavaScript', 'Java', 'React', 'Node.js']):
            github_results = self._search_github_profiles(query, skills, limit//3)
            if github_results:
                all_candidates.extend(github_results)
                sources_used.append('GitHub')
        
        # Search AngelList for startup candidates (disabled for now)
        # angellist_results = self._search_angellist_profiles(query, location, limit//4)
        # if angellist_results:
        #     all_candidates.extend(angellist_results)
        #     sources_used.append('AngelList')
            
        # Remove duplicates based on email/profile URL
        unique_candidates = self._deduplicate_candidates(all_candidates)
        
        return {
            'candidates': unique_candidates[:limit],
            'total_found': len(unique_candidates),
            'sources_searched': sources_used,
            'search_query': query,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _search_linkedin_profiles(self, query: str, location: str, skills: List[str], limit: int) -> List[Dict]:
        """Search LinkedIn profiles using RapidAPI LinkedIn scraper"""
        if not self.rapidapi_key:
            logging.warning("RapidAPI key not found for LinkedIn search")
            return []
            
        try:
            # LinkedIn Profile Search API
            url = "https://linkedin-profiles-and-company-data.p.rapidapi.com/search-profiles"
            
            headers = self.base_headers.copy()
            headers['X-RapidAPI-Host'] = 'linkedin-profiles-and-company-data.p.rapidapi.com'
            
            params = {
                'keywords': query,
                'location': location or 'United States',
                'limit': limit
            }
            
            # Add skills to keywords if provided
            if skills:
                params['keywords'] += f" {' '.join(skills[:3])}"  # Add top 3 skills
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                candidates = []
                
                for profile in data.get('profiles', []):
                    candidate = {
                        'source': 'LinkedIn',
                        'name': profile.get('name', 'Unknown'),
                        'title': profile.get('headline', ''),
                        'location': profile.get('location', ''),
                        'profile_url': profile.get('profileUrl', ''),
                        'summary': profile.get('summary', '')[:500],  # Limit summary length
                        'experience': self._extract_experience(profile.get('experience', [])),
                        'skills': self._extract_skills(profile.get('skills', [])),
                        'education': self._extract_education(profile.get('education', [])),
                        'connections': profile.get('connectionsCount', 0),
                        'estimated_fit': self._calculate_fit_score(profile, query, skills),
                        'contact_info': {
                            'linkedin': profile.get('profileUrl', ''),
                            'email': profile.get('email', ''),  # Usually not available
                            'phone': profile.get('phone', '')   # Usually not available
                        }
                    }
                    candidates.append(candidate)
                
                logging.info(f"Found {len(candidates)} LinkedIn candidates")
                return candidates
                
        except Exception as e:
            logging.error(f"LinkedIn search error: {str(e)}")
            
        return []
    
    def _search_github_profiles(self, query: str, skills: List[str], limit: int) -> List[Dict]:
        """Search GitHub profiles for technical candidates"""
        if not self.rapidapi_key:
            return []
            
        try:
            # GitHub User Search API
            url = "https://github-user-scraper.p.rapidapi.com/search-users"
            
            headers = self.base_headers.copy()
            headers['X-RapidAPI-Host'] = 'github-user-scraper.p.rapidapi.com'
            
            # Build search query with programming languages/skills
            tech_skills = [s for s in (skills or []) if s.lower() in 
                          ['python', 'javascript', 'java', 'react', 'node.js', 'django', 'flask']]
            
            search_query = query
            if tech_skills:
                search_query += f" language:{tech_skills[0].lower()}"
            
            params = {
                'query': search_query,
                'per_page': limit
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                candidates = []
                
                for user in data.get('users', []):
                    candidate = {
                        'source': 'GitHub',
                        'name': user.get('name', user.get('login', 'Unknown')),
                        'title': 'Software Developer',  # Inferred from GitHub
                        'location': user.get('location', ''),
                        'profile_url': user.get('html_url', ''),
                        'summary': user.get('bio', '')[:300],
                        'github_stats': {
                            'public_repos': user.get('public_repos', 0),
                            'followers': user.get('followers', 0),
                            'following': user.get('following', 0)
                        },
                        'skills': tech_skills,  # Based on search
                        'estimated_fit': self._calculate_github_fit(user, skills),
                        'contact_info': {
                            'github': user.get('html_url', ''),
                            'email': user.get('email', ''),
                            'blog': user.get('blog', '')
                        }
                    }
                    candidates.append(candidate)
                
                logging.info(f"Found {len(candidates)} GitHub candidates")
                return candidates
                
        except Exception as e:
            logging.error(f"GitHub search error: {str(e)}")
            
        return []
    
    def _search_angellist_profiles(self, query: str, location: str, limit: int) -> List[Dict]:
        """Search AngelList for startup candidates"""
        # Note: This would use AngelList Talent API if available
        # For now, return empty as AngelList has restricted API access
        return []
    
    def _extract_experience(self, experience_data: List[Dict]) -> List[Dict]:
        """Extract and format experience information"""
        formatted_experience = []
        for exp in experience_data[:3]:  # Top 3 experiences
            formatted_experience.append({
                'title': exp.get('title', ''),
                'company': exp.get('company', ''),
                'duration': exp.get('duration', ''),
                'description': exp.get('description', '')[:200]  # Limit description
            })
        return formatted_experience
    
    def _extract_skills(self, skills_data: List) -> List[str]:
        """Extract skills from profile data"""
        if isinstance(skills_data, list):
            return [skill.get('name', skill) if isinstance(skill, dict) else str(skill) 
                   for skill in skills_data[:10]]  # Top 10 skills
        return []
    
    def _extract_education(self, education_data: List[Dict]) -> List[Dict]:
        """Extract education information"""
        formatted_education = []
        for edu in education_data[:2]:  # Top 2 education entries
            formatted_education.append({
                'school': edu.get('school', ''),
                'degree': edu.get('degree', ''),
                'field': edu.get('field', ''),
                'year': edu.get('year', '')
            })
        return formatted_education
    
    def _calculate_fit_score(self, profile: Dict, query: str, required_skills: List[str]) -> float:
        """Calculate estimated fit score based on profile match"""
        score = 5.0  # Base score
        
        # Title/headline match
        headline = profile.get('headline', '').lower()
        if any(word in headline for word in query.lower().split()):
            score += 2.0
        
        # Skills match
        profile_skills = [s.lower() for s in self._extract_skills(profile.get('skills', []))]
        if required_skills:
            matched_skills = sum(1 for skill in required_skills 
                               if skill.lower() in profile_skills)
            skill_ratio = matched_skills / len(required_skills)
            score += skill_ratio * 3.0
        
        # Experience level (based on connections or experience count)
        connections = profile.get('connectionsCount', 0)
        if connections > 500:
            score += 1.0
        elif connections > 100:
            score += 0.5
        
        return min(score, 10.0)  # Cap at 10
    
    def _calculate_github_fit(self, user: Dict, required_skills: List[str]) -> float:
        """Calculate fit score for GitHub users"""
        score = 5.0
        
        # Repository count
        repos = user.get('public_repos', 0)
        if repos > 50:
            score += 2.0
        elif repos > 20:
            score += 1.0
        elif repos > 5:
            score += 0.5
        
        # Followers (indication of reputation)
        followers = user.get('followers', 0)
        if followers > 100:
            score += 1.5
        elif followers > 20:
            score += 0.5
        
        # Has bio (shows professionalism)
        if user.get('bio'):
            score += 0.5
        
        return min(score, 10.0)
    
    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Remove duplicate candidates based on profile URL or email"""
        seen = set()
        unique_candidates = []
        
        for candidate in candidates:
            # Create identifier based on profile URL or name+location
            identifier = (candidate.get('profile_url') or 
                         f"{candidate.get('name', '')}-{candidate.get('location', '')}")
            
            if identifier not in seen and identifier:
                seen.add(identifier)
                unique_candidates.append(candidate)
        
        return unique_candidates

def search_external_candidates(
    query: str,
    location: str = None,
    skills: List[str] = None,
    experience_level: str = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Main function to search for external candidates
    """
    sourcer = CandidateSourcer()
    return sourcer.search_candidates(query, location, skills, experience_level, limit)