"""
Enhanced Candidate Sourcing Service using xAI Grok and RapidAPI
Provides intelligent candidate search with multiple data sources
"""

import json
import logging
import requests
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI
from config import Config

class EnhancedSourcingService:
    """Advanced candidate sourcing using xAI Grok and RapidAPI services"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize xAI client if available
        self.xai_client = None
        if Config.XAI_API_KEY:
            self.xai_client = OpenAI(
                base_url="https://api.x.ai/v1",
                api_key=Config.XAI_API_KEY
            )
            self.logger.info("xAI Grok model initialized for enhanced search")
        
        # Initialize OpenAI as fallback
        self.openai_client = None
        if Config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def intelligent_search(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use AI to understand search intent and find candidates from multiple sources
        
        Args:
            query: Natural language search query
            context: Additional context for the search
        
        Returns:
            Search results with candidates and metadata
        """
        # First, analyze the query with AI to extract structured search parameters
        search_params = self._analyze_search_intent(query, context)
        
        # Search multiple sources
        all_candidates = []
        sources_searched = []
        
        # 1. Search LinkedIn via RapidAPI
        if Config.RAPIDAPI_KEY:
            linkedin_candidates = self._search_linkedin_rapidapi(search_params)
            if linkedin_candidates:
                all_candidates.extend(linkedin_candidates)
                sources_searched.append("LinkedIn")
        
        # 2. Search Indeed Resumes via RapidAPI
        if Config.RAPIDAPI_KEY:
            indeed_candidates = self._search_indeed_resumes(search_params)
            if indeed_candidates:
                all_candidates.extend(indeed_candidates)
                sources_searched.append("Indeed Resumes")
        
        # 3. Search trades-specific job boards via RapidAPI
        if Config.RAPIDAPI_KEY:
            trades_candidates = self._search_trades_boards(search_params)
            if trades_candidates:
                all_candidates.extend(trades_candidates)
                sources_searched.append("Trade Job Boards")
        
        # 4. Search GitHub for technical trades
        if self._is_technical_trade(search_params.get('trade')):
            github_candidates = self._search_github_enhanced(search_params)
            if github_candidates:
                all_candidates.extend(github_candidates)
                sources_searched.append("GitHub")
        
        # Rank candidates using AI
        if all_candidates and (self.xai_client or self.openai_client):
            all_candidates = self._rank_candidates_with_ai(all_candidates, search_params)
        
        return {
            'candidates': all_candidates[:20],  # Top 20 candidates
            'sources_searched': sources_searched,
            'search_params': search_params,
            'total_found': len(all_candidates)
        }
    
    def _analyze_search_intent(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use AI to analyze search intent and extract structured parameters"""
        
        prompt = f"""Analyze this candidate search query and extract structured search parameters.
        
Query: {query}
Context: {json.dumps(context) if context else 'None'}

Extract and return a JSON object with these fields:
- trade: specific trade (electrician, hvac, plumber, carpenter, etc.)
- location: city and state if mentioned
- experience_level: junior/mid/senior
- certifications: list of certifications mentioned
- skills: list of specific skills
- licenses: list of licenses mentioned
- keywords: other important keywords
- hourly_rate_range: if mentioned, as [min, max]
- availability: immediate/flexible/specific date

Return ONLY valid JSON, no other text."""

        try:
            # Try xAI Grok first
            if self.xai_client:
                response = self.xai_client.chat.completions.create(
                    model="grok-2-1212",  # Latest Grok model
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                params = json.loads(response.choices[0].message.content)
            # Fallback to OpenAI
            elif self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                params = json.loads(response.choices[0].message.content)
            else:
                # Basic parsing without AI
                params = {
                    'keywords': query,
                    'trade': self._extract_trade_from_query(query),
                    'location': context.get('location') if context else None
                }
            
            return params
            
        except Exception as e:
            self.logger.error(f"Error analyzing search intent: {e}")
            return {'keywords': query}
    
    def _search_linkedin_rapidapi(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search LinkedIn profiles via RapidAPI"""
        candidates = []
        
        try:
            # Build search query
            search_terms = []
            if params.get('trade'):
                search_terms.append(params['trade'])
            if params.get('certifications'):
                search_terms.extend(params['certifications'][:2])
            if params.get('location'):
                search_terms.append(params['location'])
            
            headers = {
                "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "linkedin-profiles-and-company-data.p.rapidapi.com"
            }
            
            # Search for profiles
            response = requests.get(
                "https://linkedin-profiles-and-company-data.p.rapidapi.com/profile-search",
                headers=headers,
                params={
                    "keywords": " ".join(search_terms),
                    "limit": "10"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for profile in data.get('profiles', []):
                    candidate = {
                        'source': 'LinkedIn',
                        'name': profile.get('name', ''),
                        'title': profile.get('headline', ''),
                        'location': profile.get('location', ''),
                        'profile_url': profile.get('profileUrl', ''),
                        'summary': profile.get('summary', ''),
                        'skills': profile.get('skills', []),
                        'experience': profile.get('experience', [])
                    }
                    candidates.append(candidate)
        
        except Exception as e:
            self.logger.error(f"Error searching LinkedIn via RapidAPI: {e}")
        
        return candidates
    
    def _search_indeed_resumes(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search Indeed resume database via RapidAPI"""
        candidates = []
        
        try:
            # Build search query
            query_parts = []
            if params.get('trade'):
                query_parts.append(params['trade'])
            if params.get('skills'):
                query_parts.extend(params['skills'][:3])
            
            headers = {
                "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "indeed12.p.rapidapi.com"
            }
            
            # Search Indeed resumes
            response = requests.get(
                "https://indeed12.p.rapidapi.com/resumes/search",
                headers=headers,
                params={
                    "query": " ".join(query_parts),
                    "location": params.get('location', 'USA'),
                    "page": "1"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for resume in data.get('resumes', []):
                    candidate = {
                        'source': 'Indeed Resumes',
                        'name': resume.get('name', ''),
                        'title': resume.get('job_title', ''),
                        'location': resume.get('location', ''),
                        'summary': resume.get('summary', ''),
                        'skills': resume.get('skills', []),
                        'experience_years': resume.get('years_experience', 0),
                        'last_updated': resume.get('last_updated', '')
                    }
                    candidates.append(candidate)
        
        except Exception as e:
            self.logger.error(f"Error searching Indeed resumes: {e}")
        
        return candidates
    
    def _search_trades_boards(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search specialized trades job boards"""
        candidates = []
        
        try:
            # Use JSearch API which aggregates from 150,000+ sources including trade-specific boards
            headers = {
                "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }
            
            # Search for candidates mentioning they're looking for work
            trade = params.get('trade', 'tradesman')
            location = params.get('location', 'USA')
            
            response = requests.get(
                "https://jsearch.p.rapidapi.com/search",
                headers=headers,
                params={
                    "query": f"{trade} resume available hire {location}",
                    "num_pages": "1",
                    "page": "1"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Parse job postings that might contain candidate information
                for item in data.get('data', []):
                    # Look for posts where tradesmen advertise availability
                    if 'available' in item.get('job_description', '').lower():
                        candidate = {
                            'source': 'Trade Boards',
                            'title': trade.title(),
                            'location': item.get('job_city', '') + ', ' + item.get('job_state', ''),
                            'description': item.get('job_description', '')[:500],
                            'posted_date': item.get('job_posted_at_datetime_utc', '')
                        }
                        candidates.append(candidate)
        
        except Exception as e:
            self.logger.error(f"Error searching trade boards: {e}")
        
        return candidates
    
    def _search_github_enhanced(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhanced GitHub search for technical trades"""
        candidates = []
        
        try:
            # Search for users with relevant skills
            skills = params.get('skills', [])
            if not skills and params.get('trade'):
                # Map trades to technical skills
                tech_skills = {
                    'electrician': ['arduino', 'plc', 'automation'],
                    'hvac': ['building automation', 'controls', 'iot'],
                    'technical': ['cad', 'autocad', 'revit']
                }
                skills = tech_skills.get(params['trade'], [])
            
            headers = {'Accept': 'application/vnd.github.v3+json'}
            if Config.GITHUB_TOKEN:
                headers['Authorization'] = f'token {Config.GITHUB_TOKEN}'
            
            for skill in skills[:2]:  # Limit to avoid rate limiting
                response = requests.get(
                    "https://api.github.com/search/users",
                    headers=headers,
                    params={'q': f"{skill} in:bio", 'per_page': 5},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for user in data.get('items', []):
                        # Get user details
                        user_response = requests.get(
                            user['url'],
                            headers=headers,
                            timeout=10
                        )
                        
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            candidate = {
                                'source': 'GitHub',
                                'name': user_data.get('name', user_data.get('login', '')),
                                'profile_url': user_data.get('html_url'),
                                'location': user_data.get('location', ''),
                                'bio': user_data.get('bio', ''),
                                'company': user_data.get('company', ''),
                                'email': user_data.get('email', ''),
                                'skills': [skill],
                                'repos_count': user_data.get('public_repos', 0)
                            }
                            candidates.append(candidate)
        
        except Exception as e:
            self.logger.error(f"Error searching GitHub: {e}")
        
        return candidates
    
    def _rank_candidates_with_ai(self, candidates: List[Dict[str, Any]], 
                                 search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use AI to rank candidates based on fit"""
        
        if not candidates:
            return candidates
        
        # Prepare ranking prompt
        prompt = f"""Rank these candidates based on fit for the following requirements:
Search Parameters: {json.dumps(search_params)}

Candidates:
{json.dumps(candidates[:30], indent=2)}  # Limit to 30 for token limits

For each candidate, assign a fit_score from 0-100 based on:
- Trade/role match
- Location match
- Skills/certifications match
- Experience level
- Overall relevance

Return a JSON array with each candidate including their original data plus a 'fit_score' field.
Order by fit_score descending."""

        try:
            # Use xAI Grok or OpenAI
            client = self.xai_client or self.openai_client
            model = "grok-2-1212" if self.xai_client else "gpt-4o"
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Extract candidates array from various possible response formats
            if isinstance(result, dict):
                ranked = result.get('candidates', result.get('results', []))
            else:
                ranked = result
            
            return ranked
            
        except Exception as e:
            self.logger.error(f"Error ranking candidates with AI: {e}")
            # Return unranked if AI fails
            return candidates
    
    def _is_technical_trade(self, trade: str) -> bool:
        """Check if trade has technical/programming aspects"""
        if not trade:
            return False
        
        technical_trades = [
            'electrician', 'automation', 'controls', 
            'hvac', 'technical', 'instrumentation'
        ]
        
        return any(t in trade.lower() for t in technical_trades)
    
    def _extract_trade_from_query(self, query: str) -> Optional[str]:
        """Basic trade extraction from query"""
        query_lower = query.lower()
        
        trades = [
            'electrician', 'plumber', 'hvac', 'carpenter', 
            'welder', 'painter', 'roofer', 'mason', 
            'glazier', 'insulator', 'technician'
        ]
        
        for trade in trades:
            if trade in query_lower:
                return trade
        
        return None