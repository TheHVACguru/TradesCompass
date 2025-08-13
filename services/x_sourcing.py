import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI

class XCandidateSourcer:
    """
    Service for sourcing candidates from X (formerly Twitter)
    Uses X's search functionality to find job seekers and analyzes them with xAI Grok
    """
    
    def __init__(self):
        self.xai_api_key = os.environ.get('XAI_API_KEY')
        self.rapidapi_key = os.environ.get('RAPIDAPI_KEY')
        
        # Initialize xAI client for Grok
        if self.xai_api_key:
            self.grok_client = OpenAI(
                base_url="https://api.x.ai/v1",
                api_key=self.xai_api_key
            )
        else:
            self.grok_client = None
            
    def search_x_candidates(
        self,
        query: str,
        skills: List[str] = None,
        location: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search X for potential candidates using keywords
        
        Common search patterns:
        - "looking for [job title] position"
        - "seeking [job type] opportunity"
        - "[skill] developer available"
        - "open to work"
        - "#OpenToWork"
        - "hiring [job title]" (reverse search)
        """
        
        candidates = []
        
        # Build search queries for X
        search_queries = self._build_x_search_queries(query, skills, location)
        
        for search_query in search_queries[:3]:  # Limit to 3 queries
            try:
                results = self._search_x_posts(search_query, limit=limit//3)
                
                for post in results:
                    candidate = self._extract_candidate_from_post(post, query, skills)
                    if candidate:
                        candidates.append(candidate)
                        
            except Exception as e:
                logging.error(f"X search error for query '{search_query}': {str(e)}")
        
        # Analyze candidates with Grok AI
        if self.grok_client and candidates:
            candidates = self._analyze_with_grok(candidates, query, skills)
        
        # Remove duplicates
        unique_candidates = self._deduplicate_x_candidates(candidates)
        
        return unique_candidates[:limit]
    
    def _build_x_search_queries(self, job_title: str, skills: List[str], location: str) -> List[str]:
        """Build optimized search queries for X"""
        queries = []
        
        # Job seeker queries
        queries.append(f'"{job_title}" "looking for" OR "seeking" OR "open to work"')
        queries.append(f'"#OpenToWork" {job_title}')
        
        # Skills-based queries
        if skills:
            top_skill = skills[0] if skills else ""
            queries.append(f'"{top_skill}" developer available OR "looking for work"')
        
        # Location-based query
        if location:
            queries.append(f'"{job_title}" "{location}" "hiring" OR "looking"')
        
        # Tech community queries
        queries.append(f'"need a job" {job_title} OR "laid off"')
        queries.append(f'"DM me" "opportunities" {job_title}')
        
        return queries
    
    def _search_x_posts(self, query: str, limit: int = 10) -> List[Dict]:
        """Search X posts using RapidAPI Twitter/X API"""
        if not self.rapidapi_key:
            logging.warning("RapidAPI key not found for X search")
            return []
        
        try:
            # Using Twitter/X Search API via RapidAPI
            url = "https://twitter-api45.p.rapidapi.com/search.php"
            
            headers = {
                'X-RapidAPI-Key': self.rapidapi_key,
                'X-RapidAPI-Host': 'twitter-api45.p.rapidapi.com'
            }
            
            params = {
                'query': query,
                'count': str(limit)
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                logging.error(f"X API error: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"X search API error: {str(e)}")
            return []
    
    def _extract_candidate_from_post(self, post: Dict, job_title: str, skills: List[str]) -> Optional[Dict]:
        """Extract candidate information from X post"""
        try:
            # Extract user info
            user = post.get('user', {})
            text = post.get('text', '')
            
            # Basic filtering - check if post is relevant
            relevant_keywords = ['looking for', 'seeking', 'open to work', 'available', 
                               'hire me', 'need a job', 'laid off', '#OpenToWork']
            
            if not any(keyword.lower() in text.lower() for keyword in relevant_keywords):
                return None
            
            candidate = {
                'source': 'X',
                'platform_id': user.get('id_str', ''),
                'name': user.get('name', 'Unknown'),
                'username': user.get('screen_name', ''),
                'title': self._extract_job_title_from_bio(user.get('description', '')),
                'location': user.get('location', ''),
                'bio': user.get('description', ''),
                'post_text': text[:500],  # First 500 chars
                'profile_url': f"https://x.com/{user.get('screen_name', '')}" if user.get('screen_name') else '',
                'profile_image': user.get('profile_image_url_https', ''),
                'followers': user.get('followers_count', 0),
                'verified': user.get('verified', False),
                'created_at': post.get('created_at', ''),
                'skills': [],  # Will be extracted by Grok
                'estimated_fit': 5.0,  # Base score, will be updated by Grok
                'contact_info': {
                    'x_handle': f"@{user.get('screen_name', '')}",
                    'website': user.get('url', ''),
                    'email': ''  # Not available from X
                }
            }
            
            return candidate
            
        except Exception as e:
            logging.error(f"Error extracting candidate from X post: {str(e)}")
            return None
    
    def _extract_job_title_from_bio(self, bio: str) -> str:
        """Extract likely job title from X bio"""
        # Common patterns in bios
        titles = [
            'Software Engineer', 'Developer', 'Designer', 'Product Manager',
            'Data Scientist', 'DevOps', 'Full Stack', 'Frontend', 'Backend',
            'Machine Learning', 'AI Engineer', 'Cloud Architect', 'SRE'
        ]
        
        bio_lower = bio.lower()
        for title in titles:
            if title.lower() in bio_lower:
                return title
        
        return 'Professional'  # Default
    
    def _analyze_with_grok(self, candidates: List[Dict], job_title: str, skills: List[str]) -> List[Dict]:
        """Use xAI Grok to analyze and score candidates"""
        if not self.grok_client:
            return candidates
        
        for candidate in candidates:
            try:
                # Prepare context for Grok analysis
                analysis_prompt = f"""
                Analyze this potential candidate from X (Twitter) for a {job_title} position.
                
                Required skills: {', '.join(skills) if skills else 'Not specified'}
                
                Candidate Information:
                Name: {candidate.get('name')}
                Bio: {candidate.get('bio')}
                Location: {candidate.get('location')}
                Recent Post: {candidate.get('post_text')}
                Followers: {candidate.get('followers')}
                
                Based on this information, provide:
                1. Estimated fit score (1-10) for the {job_title} role
                2. Likely technical skills (extract from bio and post)
                3. Seniority level (junior/mid/senior/executive)
                4. Key strengths
                5. Potential concerns or gaps
                
                Respond in JSON format:
                {{
                    "fit_score": number,
                    "skills": ["skill1", "skill2"],
                    "seniority": "level",
                    "strengths": ["strength1", "strength2"],
                    "concerns": ["concern1"]
                }}
                """
                
                response = self.grok_client.chat.completions.create(
                    model="grok-2-1212",
                    messages=[
                        {"role": "system", "content": "You are an expert recruiter analyzing social media profiles for job candidates."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=500
                )
                
                analysis = json.loads(response.choices[0].message.content)
                
                # Update candidate with Grok analysis
                candidate['estimated_fit'] = analysis.get('fit_score', 5.0)
                candidate['skills'] = analysis.get('skills', [])
                candidate['seniority_level'] = analysis.get('seniority', 'unknown')
                candidate['ai_strengths'] = analysis.get('strengths', [])
                candidate['ai_concerns'] = analysis.get('concerns', [])
                
            except Exception as e:
                logging.error(f"Grok analysis error: {str(e)}")
                # Keep default values if analysis fails
        
        return candidates
    
    def _deduplicate_x_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Remove duplicate candidates based on username"""
        seen = set()
        unique = []
        
        for candidate in candidates:
            identifier = candidate.get('username', candidate.get('name', ''))
            if identifier and identifier not in seen:
                seen.add(identifier)
                unique.append(candidate)
        
        # Sort by estimated fit score
        unique.sort(key=lambda x: x.get('estimated_fit', 0), reverse=True)
        
        return unique
    
    def get_x_job_listings(self, query: str, location: str = None) -> List[Dict]:
        """
        Search X job listings (companies posting jobs)
        This searches for companies hiring, not candidates
        """
        job_listings = []
        
        # Search for hiring posts
        hiring_queries = [
            f'"we are hiring" {query}',
            f'"now hiring" {query}',
            f'"job opening" {query}',
            f'"join our team" {query}'
        ]
        
        for search_query in hiring_queries[:2]:
            try:
                results = self._search_x_posts(search_query, limit=10)
                
                for post in results:
                    job = self._extract_job_from_post(post, query)
                    if job:
                        job_listings.append(job)
                        
            except Exception as e:
                logging.error(f"X job search error: {str(e)}")
        
        return job_listings
    
    def _extract_job_from_post(self, post: Dict, job_title: str) -> Optional[Dict]:
        """Extract job listing information from X post"""
        try:
            user = post.get('user', {})
            text = post.get('text', '')
            
            # Check if it's actually a job posting
            if not any(word in text.lower() for word in ['hiring', 'job', 'opening', 'position']):
                return None
            
            return {
                'source': 'X',
                'company': user.get('name', 'Unknown Company'),
                'company_handle': f"@{user.get('screen_name', '')}",
                'job_title': job_title,
                'description': text[:500],
                'posted_date': post.get('created_at', ''),
                'application_url': f"https://x.com/{user.get('screen_name', '')}/status/{post.get('id_str', '')}",
                'company_verified': user.get('verified', False),
                'company_followers': user.get('followers_count', 0)
            }
            
        except Exception as e:
            logging.error(f"Error extracting job from X post: {str(e)}")
            return None


def search_x_for_candidates(
    query: str,
    skills: List[str] = None,
    location: str = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Main function to search X for candidates
    """
    sourcer = XCandidateSourcer()
    candidates = sourcer.search_x_candidates(query, skills, location, limit)
    
    return {
        'candidates': candidates,
        'total_found': len(candidates),
        'source': 'X',
        'search_query': query,
        'timestamp': datetime.utcnow().isoformat()
    }


def search_x_job_listings(query: str, location: str = None) -> List[Dict]:
    """
    Search for job listings posted on X
    """
    sourcer = XCandidateSourcer()
    return sourcer.get_x_job_listings(query, location)