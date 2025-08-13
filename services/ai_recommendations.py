"""
AI-Powered Candidate Recommendation Service for TalentCompass AI
Uses OpenAI to provide intelligent candidate recommendations
"""

import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os
from models import ResumeAnalysis, CandidateSkill, ScoringScheme
from sqlalchemy import and_, or_, func
from app import db

class AIRecommendationService:
    """AI-powered candidate recommendation engine"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
    def recommend_candidates_for_job(
        self,
        job_description: str,
        required_skills: List[str] = None,
        location_preference: str = None,
        limit: int = 10,
        scoring_scheme_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend top candidates for a specific job using AI analysis
        
        Args:
            job_description: Full job description text
            required_skills: List of required skills
            location_preference: Preferred location
            limit: Maximum candidates to return
            scoring_scheme_id: Custom scoring scheme to use
        """
        
        # Get initial candidate pool
        candidates = self._get_candidate_pool(required_skills, location_preference)
        
        if not candidates:
            return []
        
        # Get scoring scheme
        scoring_scheme = None
        if scoring_scheme_id:
            scoring_scheme = ScoringScheme.query.get(scoring_scheme_id)
        
        # Rank candidates using AI
        ranked_candidates = []
        for candidate in candidates[:limit * 2]:  # Process more to filter later
            ranking = self._ai_rank_candidate(
                candidate, job_description, required_skills, scoring_scheme
            )
            if ranking:
                ranked_candidates.append(ranking)
        
        # Sort by AI score
        ranked_candidates.sort(key=lambda x: x['ai_score'], reverse=True)
        
        return ranked_candidates[:limit]
    
    def find_similar_candidates(
        self,
        candidate_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find candidates similar to a given candidate
        
        Args:
            candidate_id: ID of reference candidate
            limit: Maximum similar candidates to return
        """
        reference = ResumeAnalysis.query.get(candidate_id)
        if not reference:
            return []
        
        # Extract key attributes
        reference_skills = [skill.skill_name for skill in reference.skills]
        reference_text = reference.resume_text or ''
        
        # Find candidates with similar skills
        similar_candidates = []
        
        if reference_skills:
            # Query candidates with overlapping skills
            skill_matches = db.session.query(
                ResumeAnalysis,
                func.count(CandidateSkill.id).label('matching_skills')
            ).join(
                CandidateSkill
            ).filter(
                and_(
                    CandidateSkill.skill_name.in_(reference_skills),
                    ResumeAnalysis.id != candidate_id
                )
            ).group_by(
                ResumeAnalysis.id
            ).order_by(
                func.count(CandidateSkill.id).desc()
            ).limit(limit * 2).all()
            
            for candidate, match_count in skill_matches:
                similarity_score = self._calculate_similarity(
                    reference, candidate, reference_skills
                )
                similar_candidates.append({
                    'candidate': candidate,
                    'similarity_score': similarity_score,
                    'matching_skills': match_count,
                    'comparison': self._generate_comparison(reference, candidate)
                })
        
        # Sort by similarity score
        similar_candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return similar_candidates[:limit]
    
    def generate_candidate_insights(
        self,
        candidate_id: int,
        job_context: str = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights about a candidate
        
        Args:
            candidate_id: Candidate to analyze
            job_context: Optional job context for targeted insights
        """
        candidate = ResumeAnalysis.query.get(candidate_id)
        if not candidate:
            return {}
        
        try:
            prompt = f"""
            Analyze this candidate and provide strategic insights:
            
            Candidate Information:
            - Name: {candidate.first_name} {candidate.last_name}
            - Location: {candidate.location}
            - Strengths: {candidate.candidate_strengths}
            - Weaknesses: {candidate.candidate_weaknesses}
            - Overall Rating: {candidate.overall_fit_rating}/10
            
            {"Job Context: " + job_context if job_context else ""}
            
            Provide insights in JSON format:
            {{
                "key_differentiators": ["list of unique strengths"],
                "potential_concerns": ["list of areas to probe"],
                "interview_questions": ["3 targeted questions"],
                "negotiation_leverage": "what candidate might want",
                "flight_risk": "low/medium/high with reason",
                "growth_potential": "assessment of future potential",
                "team_fit_analysis": "how they might fit in team",
                "recommended_next_steps": ["actionable recommendations"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert recruiter providing strategic candidate insights."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            insights = json.loads(response.choices[0].message.content)
            insights['candidate_id'] = candidate_id
            insights['candidate_name'] = f"{candidate.first_name} {candidate.last_name}"
            
            return insights
            
        except Exception as e:
            logging.error(f"Error generating insights: {str(e)}")
            return {
                'error': 'Unable to generate insights',
                'candidate_id': candidate_id
            }
    
    def optimize_candidate_pool(
        self,
        job_requirements: Dict[str, Any],
        current_pool: List[int],
        target_size: int = 20
    ) -> Dict[str, Any]:
        """
        Optimize a candidate pool for diversity and quality
        
        Args:
            job_requirements: Job requirements and preferences
            current_pool: Current candidate IDs in pool
            target_size: Target pool size
        """
        # Get current pool candidates
        current_candidates = ResumeAnalysis.query.filter(
            ResumeAnalysis.id.in_(current_pool)
        ).all() if current_pool else []
        
        # Analyze current pool
        pool_analysis = self._analyze_pool_diversity(current_candidates)
        
        # Find candidates to add for better diversity/quality
        recommendations = {
            'current_pool_analysis': pool_analysis,
            'recommended_additions': [],
            'recommended_removals': [],
            'diversity_score': pool_analysis.get('diversity_score', 0),
            'quality_score': pool_analysis.get('quality_score', 0)
        }
        
        # Find high-quality candidates not in pool
        if len(current_candidates) < target_size:
            additional_candidates = self._find_complementary_candidates(
                job_requirements,
                current_pool,
                target_size - len(current_candidates)
            )
            recommendations['recommended_additions'] = additional_candidates
        
        # Identify weak candidates to potentially remove
        if len(current_candidates) > target_size:
            weak_candidates = self._identify_weak_candidates(
                current_candidates,
                job_requirements,
                len(current_candidates) - target_size
            )
            recommendations['recommended_removals'] = weak_candidates
        
        return recommendations
    
    def _get_candidate_pool(
        self,
        required_skills: List[str] = None,
        location: str = None
    ) -> List[ResumeAnalysis]:
        """Get initial candidate pool based on filters"""
        query = ResumeAnalysis.query.filter(
            ResumeAnalysis.status == 'active'
        )
        
        if required_skills:
            # Filter by skills
            query = query.join(CandidateSkill).filter(
                CandidateSkill.skill_name.in_(required_skills)
            ).group_by(
                ResumeAnalysis.id
            ).having(
                func.count(CandidateSkill.id) >= len(required_skills) * 0.5
            )
        
        if location:
            query = query.filter(
                func.lower(ResumeAnalysis.location).contains(location.lower())
            )
        
        return query.all()
    
    def _ai_rank_candidate(
        self,
        candidate: ResumeAnalysis,
        job_description: str,
        required_skills: List[str],
        scoring_scheme: Optional[ScoringScheme]
    ) -> Dict[str, Any]:
        """Use AI to rank a candidate for a specific job"""
        try:
            # Prepare candidate summary
            candidate_skills = [skill.skill_name for skill in candidate.skills]
            
            prompt = f"""
            Score this candidate's fit for the job (0-100):
            
            Job Description: {job_description[:1000]}
            Required Skills: {', '.join(required_skills) if required_skills else 'Not specified'}
            
            Candidate:
            - Skills: {', '.join(candidate_skills)}
            - Location: {candidate.location}
            - Strengths: {candidate.candidate_strengths}
            - Current Rating: {candidate.overall_fit_rating}/10
            
            Provide a JSON response with:
            {{
                "fit_score": 0-100,
                "skill_match_score": 0-100,
                "experience_match": 0-100,
                "reasons_to_hire": ["list of reasons"],
                "concerns": ["list of concerns"],
                "missing_skills": ["skills they lack"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert recruiter scoring candidates."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            ai_analysis = json.loads(response.choices[0].message.content)
            
            # Apply custom scoring scheme if provided
            final_score = ai_analysis['fit_score']
            if scoring_scheme:
                final_score = self._apply_scoring_scheme(
                    ai_analysis, scoring_scheme
                )
            
            return {
                'candidate': candidate.to_dict(),
                'ai_score': final_score,
                'ai_analysis': ai_analysis,
                'matching_skills': [s for s in candidate_skills if s in required_skills] if required_skills else []
            }
            
        except Exception as e:
            logging.error(f"Error ranking candidate {candidate.id}: {str(e)}")
            return None
    
    def _calculate_similarity(
        self,
        reference: ResumeAnalysis,
        candidate: ResumeAnalysis,
        reference_skills: List[str]
    ) -> float:
        """Calculate similarity between two candidates"""
        score = 0.0
        
        # Skill overlap
        candidate_skills = [skill.skill_name for skill in candidate.skills]
        skill_overlap = len(set(reference_skills) & set(candidate_skills))
        if reference_skills:
            score += (skill_overlap / len(reference_skills)) * 40
        
        # Rating similarity
        if reference.overall_fit_rating and candidate.overall_fit_rating:
            rating_diff = abs(reference.overall_fit_rating - candidate.overall_fit_rating)
            score += max(0, 30 - rating_diff * 3)
        
        # Location match
        if reference.location and candidate.location:
            if reference.location.lower() == candidate.location.lower():
                score += 15
            elif any(loc in candidate.location.lower() 
                    for loc in reference.location.lower().split()):
                score += 10
        
        # Risk/reward similarity
        if reference.risk_factor_score and candidate.risk_factor_score:
            risk_diff = abs(reference.risk_factor_score - candidate.risk_factor_score)
            score += max(0, 15 - risk_diff * 1.5)
        
        return min(100, score)
    
    def _generate_comparison(
        self,
        reference: ResumeAnalysis,
        candidate: ResumeAnalysis
    ) -> Dict[str, Any]:
        """Generate detailed comparison between candidates"""
        return {
            'rating_difference': (candidate.overall_fit_rating or 0) - (reference.overall_fit_rating or 0),
            'location_match': reference.location == candidate.location if reference.location else False,
            'risk_comparison': {
                'reference': reference.risk_factor_score,
                'candidate': candidate.risk_factor_score
            },
            'reward_comparison': {
                'reference': reference.reward_factor_score,
                'candidate': candidate.reward_factor_score
            }
        }
    
    def _analyze_pool_diversity(
        self,
        candidates: List[ResumeAnalysis]
    ) -> Dict[str, Any]:
        """Analyze diversity and quality of candidate pool"""
        if not candidates:
            return {'diversity_score': 0, 'quality_score': 0}
        
        # Analyze locations
        locations = [c.location for c in candidates if c.location]
        location_diversity = len(set(locations)) / len(candidates) if locations else 0
        
        # Analyze skills
        all_skills = []
        for candidate in candidates:
            all_skills.extend([s.skill_name for s in candidate.skills])
        skill_diversity = len(set(all_skills)) / len(all_skills) if all_skills else 0
        
        # Analyze ratings
        ratings = [c.overall_fit_rating for c in candidates if c.overall_fit_rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            'diversity_score': (location_diversity + skill_diversity) * 50,
            'quality_score': avg_rating * 10,
            'location_diversity': location_diversity,
            'skill_diversity': skill_diversity,
            'average_rating': avg_rating,
            'pool_size': len(candidates)
        }
    
    def _find_complementary_candidates(
        self,
        job_requirements: Dict[str, Any],
        exclude_ids: List[int],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find candidates that complement the existing pool"""
        # Get candidates not in current pool
        query = ResumeAnalysis.query.filter(
            and_(
                ResumeAnalysis.status == 'active',
                ~ResumeAnalysis.id.in_(exclude_ids) if exclude_ids else True
            )
        ).order_by(
            ResumeAnalysis.overall_fit_rating.desc()
        ).limit(limit)
        
        candidates = query.all()
        
        return [
            {
                'candidate_id': c.id,
                'name': f"{c.first_name} {c.last_name}",
                'rating': c.overall_fit_rating,
                'reason': 'High overall rating'
            }
            for c in candidates
        ]
    
    def _identify_weak_candidates(
        self,
        candidates: List[ResumeAnalysis],
        job_requirements: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        """Identify weakest candidates in pool"""
        # Sort by rating
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.overall_fit_rating or 0
        )
        
        weak_candidates = sorted_candidates[:count]
        
        return [
            {
                'candidate_id': c.id,
                'name': f"{c.first_name} {c.last_name}",
                'rating': c.overall_fit_rating,
                'reason': 'Low rating compared to pool'
            }
            for c in weak_candidates
        ]
    
    def _apply_scoring_scheme(
        self,
        ai_analysis: Dict[str, Any],
        scheme: ScoringScheme
    ) -> float:
        """Apply custom scoring scheme to AI analysis"""
        weighted_score = 0
        total_weight = 0
        
        # Apply skill weight
        if 'skill_match_score' in ai_analysis:
            weighted_score += ai_analysis['skill_match_score'] * scheme.skills_weight
            total_weight += scheme.skills_weight
        
        # Apply experience weight
        if 'experience_match' in ai_analysis:
            weighted_score += ai_analysis['experience_match'] * scheme.experience_weight
            total_weight += scheme.experience_weight
        
        # Apply other weights based on fit score
        weighted_score += ai_analysis.get('fit_score', 0) * scheme.culture_fit_weight
        total_weight += scheme.culture_fit_weight
        
        # Calculate final weighted score
        return (weighted_score / total_weight) if total_weight > 0 else ai_analysis.get('fit_score', 0)