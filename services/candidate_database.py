import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import and_, or_, func
from app import db
from models import ResumeAnalysis, CandidateSkill, CandidateTag

def search_candidates(
    skills: List[str] = None,
    min_fit_rating: float = None,
    max_risk_score: float = None,
    min_reward_score: float = None,
    location: str = None,
    status: str = None,
    sort_by: str = 'date_desc',
    experience_keywords: List[str] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    Advanced candidate search with multiple filters
    
    Args:
        skills: List of required skills
        min_fit_rating: Minimum overall fit rating
        max_risk_score: Maximum acceptable risk score
        min_reward_score: Minimum reward score
        location: Location filter
        status: Filter by candidate status (active, contacted, archived)
        sort_by: Sort order (date_desc, date_asc, fit_desc, risk_asc)
        experience_keywords: Keywords to search in resume text
        page: Page number for pagination
        per_page: Results per page
    
    Returns:
        Dictionary with candidates and pagination info
    """
    
    query = ResumeAnalysis.query
    
    # Filter by fit rating
    if min_fit_rating is not None:
        query = query.filter(ResumeAnalysis.overall_fit_rating >= min_fit_rating)
    
    # Filter by risk score
    if max_risk_score is not None:
        query = query.filter(ResumeAnalysis.risk_factor_score <= max_risk_score)
    
    # Filter by reward score
    if min_reward_score is not None:
        query = query.filter(ResumeAnalysis.reward_factor_score >= min_reward_score)
    
    # Search by skills in resume text (basic implementation)
    if skills:
        skill_conditions = []
        for skill in skills:
            skill_conditions.append(ResumeAnalysis.resume_text.ilike(f'%{skill}%'))
        query = query.filter(or_(*skill_conditions))
    
    # Search by experience keywords
    if experience_keywords:
        keyword_conditions = []
        for keyword in experience_keywords:
            keyword_conditions.append(ResumeAnalysis.resume_text.ilike(f'%{keyword}%'))
        query = query.filter(or_(*keyword_conditions))
    
    # Location search (basic implementation - search in resume text)
    if location:
        query = query.filter(ResumeAnalysis.resume_text.ilike(f'%{location}%'))
    
    # Filter by status
    if status and status in ['active', 'contacted', 'archived']:
        query = query.filter(ResumeAnalysis.status == status)
    
    # Apply sorting based on sort_by parameter
    if sort_by == 'date_asc':
        query = query.order_by(ResumeAnalysis.upload_date.asc())
    elif sort_by == 'fit_desc':
        query = query.order_by(
            ResumeAnalysis.overall_fit_rating.desc().nulls_last(),
            ResumeAnalysis.upload_date.desc()
        )
    elif sort_by == 'risk_asc':
        query = query.order_by(
            ResumeAnalysis.risk_factor_score.asc().nulls_last(),
            ResumeAnalysis.upload_date.desc()
        )
    else:  # date_desc (default)
        query = query.order_by(ResumeAnalysis.upload_date.desc())
    
    # Paginate results
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Process candidates for response
    candidates = []
    for analysis in pagination.items:
        # Get skills for this candidate - using correct field names
        skills = CandidateSkill.query.filter_by(candidate_id=analysis.id).all()
        skill_data = [{'skill': s.skill_name, 'proficiency': s.skill_level, 'years': s.years_experience} for s in skills]
        
        # Get tags for this candidate - using correct field names
        tags = CandidateTag.query.filter_by(candidate_id=analysis.id).all()
        tag_data = [{'tag': t.tag_name, 'color': t.tag_color} for t in tags]
        
        candidate_data = {
            'id': analysis.id,
            'name': f"{analysis.first_name or 'Unknown'} {analysis.last_name or ''}".strip(),
            'email': analysis.email,
            'phone': analysis.phone,
            'location': analysis.location,
            'filename': analysis.filename,
            'upload_date': analysis.upload_date.isoformat() if analysis.upload_date else None,
            'overall_fit_rating': analysis.overall_fit_rating,
            'risk_factor_score': analysis.risk_factor_score,
            'reward_factor_score': analysis.reward_factor_score,
            'strengths': json.loads(analysis.candidate_strengths) if analysis.candidate_strengths else [],
            'weaknesses': json.loads(analysis.candidate_weaknesses) if analysis.candidate_weaknesses else [],
            'resume_snippet': analysis.resume_text[:200] + '...' if analysis.resume_text and len(analysis.resume_text) > 200 else analysis.resume_text,
            'status': analysis.status or 'active',
            'source': analysis.source or 'manual_upload',
            'skills': skill_data,
            'tags': tag_data
        }
        candidates.append(candidate_data)
    
    return {
        'candidates': candidates,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'per_page': pagination.per_page,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num
    }

def get_candidate_statistics() -> Dict[str, Any]:
    """Get overview statistics of the candidate database"""
    
    total_candidates = ResumeAnalysis.query.count()
    
    # Fit rating distribution
    high_fit = ResumeAnalysis.query.filter(ResumeAnalysis.overall_fit_rating >= 8.0).count()
    medium_fit = ResumeAnalysis.query.filter(
        and_(ResumeAnalysis.overall_fit_rating >= 6.0, ResumeAnalysis.overall_fit_rating < 8.0)
    ).count()
    low_fit = ResumeAnalysis.query.filter(ResumeAnalysis.overall_fit_rating < 6.0).count()
    
    # Risk distribution
    low_risk = ResumeAnalysis.query.filter(ResumeAnalysis.risk_factor_score <= 3.0).count()
    medium_risk = ResumeAnalysis.query.filter(
        and_(ResumeAnalysis.risk_factor_score > 3.0, ResumeAnalysis.risk_factor_score <= 6.0)
    ).count()
    high_risk = ResumeAnalysis.query.filter(ResumeAnalysis.risk_factor_score > 6.0).count()
    
    # Recent uploads (last 30 days)
    from datetime import datetime, timedelta
    recent_date = datetime.utcnow() - timedelta(days=30)
    recent_uploads = ResumeAnalysis.query.filter(ResumeAnalysis.upload_date >= recent_date).count()
    
    # Top skills mentioned (basic implementation)
    common_skills = extract_common_skills()
    
    return {
        'total_candidates': total_candidates,
        'fit_distribution': {
            'high_fit': high_fit,
            'medium_fit': medium_fit,
            'low_fit': low_fit
        },
        'risk_distribution': {
            'low_risk': low_risk,
            'medium_risk': medium_risk,
            'high_risk': high_risk
        },
        'recent_uploads': recent_uploads,
        'common_skills': common_skills[:10]  # Top 10 skills
    }

def extract_common_skills(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Extract most commonly mentioned skills from all resumes
    This is a basic implementation - could be enhanced with NLP
    """
    
    # Common tech skills to look for
    tech_skills = [
        'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'SQL', 'PostgreSQL',
        'MongoDB', 'Redis', 'Git', 'Linux', 'HTML', 'CSS', 'TypeScript',
        'Machine Learning', 'AI', 'Data Science', 'TensorFlow', 'PyTorch',
        'Pandas', 'NumPy', 'Scikit-learn', 'Django', 'Flask', 'Spring Boot',
        'REST API', 'GraphQL', 'Microservices', 'Agile', 'Scrum', 'DevOps',
        'CI/CD', 'Jenkins', 'Terraform', 'Ansible', 'Elasticsearch'
    ]
    
    skill_counts = {}
    
    # Get all resume texts
    resumes = ResumeAnalysis.query.with_entities(ResumeAnalysis.resume_text).all()
    
    for resume in resumes:
        if resume.resume_text:
            text = resume.resume_text.lower()
            for skill in tech_skills:
                if skill.lower() in text:
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    # Sort by count and return top skills
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    
    return [{'skill': skill, 'count': count} for skill, count in sorted_skills[:limit]]

def get_similar_candidates(candidate_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find candidates similar to a given candidate based on skills and ratings
    """
    
    # Get the reference candidate
    reference = ResumeAnalysis.query.get(candidate_id)
    if not reference:
        return []
    
    # Extract skills from reference candidate's strengths
    reference_skills = []
    if reference.candidate_strengths:
        try:
            strengths = json.loads(reference.candidate_strengths)
            # Simple keyword extraction from strengths
            for strength in strengths:
                reference_skills.extend(strength.lower().split())
        except:
            pass
    
    # Find candidates with similar skills (basic implementation)
    similar_candidates = []
    candidates = ResumeAnalysis.query.filter(ResumeAnalysis.id != candidate_id).all()
    
    for candidate in candidates:
        if candidate.candidate_strengths:
            try:
                strengths = json.loads(candidate.candidate_strengths)
                candidate_skills = []
                for strength in strengths:
                    candidate_skills.extend(strength.lower().split())
                
                # Calculate simple similarity score based on common words
                common_skills = set(reference_skills) & set(candidate_skills)
                similarity_score = len(common_skills) / max(len(set(reference_skills)), 1)
                
                # Also factor in fit rating similarity
                rating_similarity = 0
                if reference.overall_fit_rating and candidate.overall_fit_rating:
                    rating_diff = abs(reference.overall_fit_rating - candidate.overall_fit_rating)
                    rating_similarity = max(0, 1 - rating_diff / 10)
                
                total_similarity = (similarity_score + rating_similarity) / 2
                
                if total_similarity > 0.1:  # Minimum threshold
                    similar_candidates.append({
                        'candidate': candidate,
                        'similarity_score': total_similarity
                    })
            except:
                continue
    
    # Sort by similarity and return top candidates
    similar_candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    result = []
    for item in similar_candidates[:limit]:
        candidate = item['candidate']
        result.append({
            'id': candidate.id,
            'name': f"{candidate.first_name or 'Unknown'} {candidate.last_name or ''}".strip(),
            'email': candidate.email,
            'filename': candidate.filename,
            'overall_fit_rating': candidate.overall_fit_rating,
            'similarity_score': round(item['similarity_score'], 2),
            'strengths': json.loads(candidate.candidate_strengths) if candidate.candidate_strengths else []
        })
    
    return result