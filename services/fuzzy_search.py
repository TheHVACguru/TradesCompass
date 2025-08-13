"""
Fuzzy Search Service for TalentCompass AI
Implements semantic, fuzzy, and Boolean search capabilities
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional
from sqlalchemy import or_, and_, func, text
from models import ResumeAnalysis, CandidateSkill, CandidateTag, TalentPool
import logging

class FuzzySearchService:
    """Enhanced search with fuzzy matching, semantic understanding, and Boolean operators"""
    
    def __init__(self):
        self.skill_synonyms = {
            'ml': ['machine learning', 'ml', 'deep learning', 'ai'],
            'machine learning': ['ml', 'machine learning', 'deep learning', 'ai'],
            'js': ['javascript', 'js', 'ecmascript'],
            'javascript': ['javascript', 'js', 'ecmascript'],
            'python': ['python', 'py', 'python3'],
            'react': ['react', 'reactjs', 'react.js'],
            'aws': ['aws', 'amazon web services', 'ec2', 's3'],
            'k8s': ['kubernetes', 'k8s', 'k8'],
            'kubernetes': ['kubernetes', 'k8s', 'k8'],
            'ci/cd': ['cicd', 'ci/cd', 'continuous integration', 'continuous deployment'],
            'devops': ['devops', 'dev ops', 'sre', 'site reliability'],
            'frontend': ['frontend', 'front-end', 'front end', 'ui'],
            'backend': ['backend', 'back-end', 'back end', 'server-side'],
            'fullstack': ['fullstack', 'full-stack', 'full stack'],
            'sql': ['sql', 'mysql', 'postgresql', 'database'],
            'nosql': ['nosql', 'mongodb', 'cassandra', 'dynamodb'],
            'pm': ['product manager', 'pm', 'product management'],
            'ux': ['ux', 'user experience', 'ux design'],
            'ui': ['ui', 'user interface', 'ui design'],
        }
        
    def fuzzy_search(
        self,
        query: str,
        threshold: float = 0.7,
        search_fields: List[str] = None
    ) -> List[ResumeAnalysis]:
        """
        Perform fuzzy search across candidate database
        
        Args:
            query: Search query string
            threshold: Similarity threshold (0-1)
            search_fields: Fields to search in
        """
        if not search_fields:
            search_fields = ['resume_text', 'candidate_strengths', 'candidate_weaknesses']
        
        # Clean and tokenize query
        query_tokens = self._tokenize(query.lower())
        
        # Expand query with synonyms
        expanded_tokens = self._expand_with_synonyms(query_tokens)
        
        # Build search conditions
        conditions = []
        for token in expanded_tokens:
            for field in search_fields:
                # Use PostgreSQL's similarity functions if available
                conditions.append(
                    func.lower(getattr(ResumeAnalysis, field)).contains(token)
                )
        
        # Execute search
        candidates = ResumeAnalysis.query.filter(or_(*conditions)).all()
        
        # Score and rank results
        scored_results = []
        for candidate in candidates:
            score = self._calculate_similarity_score(query, candidate, search_fields)
            if score >= threshold:
                scored_results.append((score, candidate))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [candidate for _, candidate in scored_results]
    
    def boolean_search(self, query: str) -> List[ResumeAnalysis]:
        """
        Perform Boolean search with AND, OR, NOT operators
        
        Examples:
            "python AND (machine learning OR data science)"
            "java NOT spring"
            "senior developer AND NOT junior"
        """
        # Parse Boolean query
        parsed_query = self._parse_boolean_query(query)
        
        # Build SQLAlchemy conditions
        conditions = self._build_boolean_conditions(parsed_query)
        
        # Execute search
        return ResumeAnalysis.query.filter(conditions).all()
    
    def semantic_search(
        self,
        query: str,
        context: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using AI understanding
        
        Args:
            query: Natural language search query
            context: Additional context (job description, requirements)
            limit: Maximum results to return
        """
        # Expand query semantically
        semantic_terms = self._get_semantic_terms(query)
        
        # Search for candidates with semantic terms
        candidates = self.fuzzy_search(' '.join(semantic_terms), threshold=0.6)
        
        # Rank by semantic relevance
        ranked_results = []
        for candidate in candidates[:limit]:
            relevance_score = self._calculate_semantic_relevance(
                query, candidate, context
            )
            ranked_results.append({
                'candidate': candidate,
                'relevance_score': relevance_score,
                'matching_skills': self._extract_matching_skills(query, candidate)
            })
        
        # Sort by relevance
        ranked_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return ranked_results
    
    def search_by_talent_pool(
        self,
        pool_id: int,
        additional_filters: Dict = None
    ) -> List[ResumeAnalysis]:
        """Search within a specific talent pool"""
        pool = TalentPool.query.get(pool_id)
        if not pool:
            return []
        
        query = ResumeAnalysis.query.join(
            pool.candidates
        )
        
        # Apply additional filters
        if additional_filters:
            if 'min_rating' in additional_filters:
                query = query.filter(
                    ResumeAnalysis.overall_fit_rating >= additional_filters['min_rating']
                )
            if 'status' in additional_filters:
                query = query.filter(
                    ResumeAnalysis.status == additional_filters['status']
                )
        
        return query.all()
    
    def proximity_search(
        self,
        location: str,
        radius_miles: int = 50
    ) -> List[ResumeAnalysis]:
        """
        Search candidates within geographic proximity
        Note: Simplified implementation - in production, use geocoding
        """
        # For now, simple text matching on location
        # In production, integrate with geocoding service
        location_keywords = location.lower().split()
        
        conditions = []
        for keyword in location_keywords:
            conditions.append(
                func.lower(ResumeAnalysis.location).contains(keyword)
            )
        
        return ResumeAnalysis.query.filter(or_(*conditions)).all()
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into searchable terms"""
        # Remove special characters except for common tech terms
        text = re.sub(r'[^\w\s\+\#\-/]', ' ', text)
        return text.split()
    
    def _expand_with_synonyms(self, tokens: List[str]) -> List[str]:
        """Expand tokens with known synonyms"""
        expanded = set(tokens)
        for token in tokens:
            if token in self.skill_synonyms:
                expanded.update(self.skill_synonyms[token])
        return list(expanded)
    
    def _calculate_similarity_score(
        self,
        query: str,
        candidate: ResumeAnalysis,
        fields: List[str]
    ) -> float:
        """Calculate similarity score between query and candidate"""
        max_score = 0
        query_lower = query.lower()
        
        for field in fields:
            field_value = getattr(candidate, field, '')
            if field_value:
                field_lower = str(field_value).lower()
                # Use SequenceMatcher for fuzzy matching
                score = SequenceMatcher(None, query_lower, field_lower).ratio()
                
                # Boost score for exact matches
                if query_lower in field_lower:
                    score = min(1.0, score + 0.3)
                
                max_score = max(max_score, score)
        
        return max_score
    
    def _parse_boolean_query(self, query: str) -> Dict:
        """Parse Boolean query into structured format"""
        # Simplified Boolean parser
        # In production, use a proper query parser
        query = query.upper()
        
        # Replace operators with tokens
        query = query.replace(' AND ', ' & ')
        query = query.replace(' OR ', ' | ')
        query = query.replace(' NOT ', ' ! ')
        
        return {'raw': query, 'tokens': query.split()}
    
    def _build_boolean_conditions(self, parsed_query: Dict):
        """Build SQLAlchemy conditions from parsed Boolean query"""
        # Simplified implementation
        # In production, build proper expression tree
        conditions = []
        tokens = parsed_query['tokens']
        
        for i, token in enumerate(tokens):
            if token not in ['&', '|', '!']:
                # Search in resume text
                condition = func.lower(ResumeAnalysis.resume_text).contains(token.lower())
                
                # Check for NOT operator
                if i > 0 and tokens[i-1] == '!':
                    condition = ~condition
                
                conditions.append(condition)
        
        # Combine with OR by default (simplified)
        return or_(*conditions) if conditions else True
    
    def _get_semantic_terms(self, query: str) -> List[str]:
        """Extract semantic terms from natural language query"""
        # Simplified semantic extraction
        # In production, use NLP/AI for better understanding
        
        # Common job-related terms mapping
        semantic_mappings = {
            'senior': ['senior', 'lead', 'principal', 'architect', 'expert'],
            'junior': ['junior', 'entry', 'associate', 'trainee'],
            'developer': ['developer', 'engineer', 'programmer', 'coder'],
            'manager': ['manager', 'lead', 'director', 'head'],
            'remote': ['remote', 'distributed', 'work from home', 'wfh'],
            'startup': ['startup', 'early stage', 'fast-paced', 'entrepreneurial'],
            'enterprise': ['enterprise', 'corporate', 'fortune 500', 'large scale'],
        }
        
        terms = set(self._tokenize(query.lower()))
        
        # Add semantic expansions
        for term in list(terms):
            if term in semantic_mappings:
                terms.update(semantic_mappings[term])
        
        return list(terms)
    
    def _calculate_semantic_relevance(
        self,
        query: str,
        candidate: ResumeAnalysis,
        context: str = None
    ) -> float:
        """Calculate semantic relevance score"""
        # Simplified scoring
        # In production, use embeddings or AI for better relevance
        
        base_score = self._calculate_similarity_score(
            query, candidate, ['resume_text', 'candidate_strengths']
        )
        
        # Boost based on ratings if available
        if candidate.overall_fit_rating:
            base_score *= (1 + candidate.overall_fit_rating / 20)
        
        # Consider context if provided
        if context and candidate.resume_text:
            context_score = SequenceMatcher(
                None, context.lower(), candidate.resume_text.lower()
            ).ratio()
            base_score = (base_score + context_score) / 2
        
        return min(1.0, base_score)
    
    def _extract_matching_skills(
        self,
        query: str,
        candidate: ResumeAnalysis
    ) -> List[str]:
        """Extract skills that match the query"""
        matching_skills = []
        query_tokens = set(self._tokenize(query.lower()))
        
        # Check candidate skills
        for skill in candidate.skills:
            if any(token in skill.skill_name.lower() for token in query_tokens):
                matching_skills.append(skill.skill_name)
        
        return matching_skills