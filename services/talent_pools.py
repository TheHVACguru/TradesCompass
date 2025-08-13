"""
Talent Pool Management Service for TalentCompass AI
Manages specialized talent pools for efficient candidate organization
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, or_
from models import TalentPool, TalentPoolMember, ResumeAnalysis, CandidateSkill, db
import logging

class TalentPoolService:
    """Manage talent pools for candidate organization"""
    
    def create_pool(self, 
                   pool_name: str,
                   pool_type: str,
                   description: Optional[str] = None,
                   criteria: Optional[Dict] = None,
                   created_by: str = 'System') -> TalentPool:
        """Create a new talent pool"""
        try:
            pool = TalentPool(
                pool_name=pool_name,
                pool_type=pool_type,
                description=description,
                pool_criteria=criteria,
                created_by=created_by,
                is_active=True
            )
            
            db.session.add(pool)
            db.session.commit()
            
            logging.info(f"Created talent pool: {pool_name}")
            return pool
            
        except Exception as e:
            logging.error(f"Error creating talent pool: {e}")
            db.session.rollback()
            raise
    
    def add_candidate_to_pool(self, 
                             pool_id: int,
                             candidate_id: int,
                             added_by: str = 'System',
                             notes: Optional[str] = None) -> bool:
        """Add a candidate to a talent pool"""
        try:
            # Check if already in pool
            existing = TalentPoolMember.query.filter_by(
                pool_id=pool_id,
                candidate_id=candidate_id
            ).first()
            
            if existing:
                logging.info(f"Candidate {candidate_id} already in pool {pool_id}")
                return False
            
            member = TalentPoolMember(
                pool_id=pool_id,
                candidate_id=candidate_id,
                added_by=added_by,
                notes=notes
            )
            
            db.session.add(member)
            
            # Update pool member count
            pool = TalentPool.query.get(pool_id)
            if pool:
                pool.member_count = TalentPoolMember.query.filter_by(pool_id=pool_id).count() + 1
            
            db.session.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error adding candidate to pool: {e}")
            db.session.rollback()
            return False
    
    def remove_candidate_from_pool(self, pool_id: int, candidate_id: int) -> bool:
        """Remove a candidate from a talent pool"""
        try:
            member = TalentPoolMember.query.filter_by(
                pool_id=pool_id,
                candidate_id=candidate_id
            ).first()
            
            if not member:
                return False
            
            db.session.delete(member)
            
            # Update pool member count
            pool = TalentPool.query.get(pool_id)
            if pool:
                pool.member_count = TalentPoolMember.query.filter_by(pool_id=pool_id).count() - 1
            
            db.session.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error removing candidate from pool: {e}")
            db.session.rollback()
            return False
    
    def get_pool_members(self, pool_id: int) -> List[ResumeAnalysis]:
        """Get all candidates in a talent pool"""
        members = db.session.query(ResumeAnalysis).join(
            TalentPoolMember,
            TalentPoolMember.candidate_id == ResumeAnalysis.id
        ).filter(
            TalentPoolMember.pool_id == pool_id
        ).all()
        
        return members
    
    def get_active_pools(self) -> List[TalentPool]:
        """Get all active talent pools"""
        return TalentPool.query.filter_by(is_active=True).order_by(
            TalentPool.created_date.desc()
        ).all()
    
    def get_pool_statistics(self, pool_id: int) -> Dict[str, Any]:
        """Get statistics for a specific talent pool"""
        pool = TalentPool.query.get(pool_id)
        if not pool:
            return {}
        
        members = self.get_pool_members(pool_id)
        
        if not members:
            return {
                'pool_name': pool.pool_name,
                'member_count': 0,
                'average_rating': 0,
                'skills': [],
                'locations': [],
                'status_breakdown': {}
            }
        
        # Calculate average rating
        ratings = [m.overall_fit_rating for m in members if m.overall_fit_rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Get top skills
        skills = db.session.query(
            CandidateSkill.skill_name,
            func.count(CandidateSkill.id).label('count')
        ).join(
            TalentPoolMember,
            TalentPoolMember.candidate_id == CandidateSkill.candidate_id
        ).filter(
            TalentPoolMember.pool_id == pool_id
        ).group_by(
            CandidateSkill.skill_name
        ).order_by(
            func.count(CandidateSkill.id).desc()
        ).limit(10).all()
        
        # Status breakdown
        status_counts = {}
        for member in members:
            status = member.status or 'unknown'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Location distribution
        locations = {}
        for member in members:
            if member.location:
                locations[member.location] = locations.get(member.location, 0) + 1
        
        return {
            'pool_name': pool.pool_name,
            'pool_type': pool.pool_type,
            'member_count': len(members),
            'average_rating': round(avg_rating, 2),
            'top_skills': [{'skill': s, 'count': c} for s, c in skills],
            'locations': sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5],
            'status_breakdown': status_counts,
            'created_date': pool.created_date,
            'created_by': pool.created_by
        }
    
    def auto_populate_pool(self, pool_id: int) -> int:
        """Automatically populate pool based on defined criteria"""
        pool = TalentPool.query.get(pool_id)
        if not pool or not pool.pool_criteria:
            return 0
        
        criteria = pool.pool_criteria if isinstance(pool.pool_criteria, dict) else {}
        
        # Build query based on criteria
        query = ResumeAnalysis.query
        
        # Apply filters based on criteria
        if 'min_rating' in criteria:
            query = query.filter(ResumeAnalysis.overall_fit_rating >= criteria['min_rating'])
        
        if 'skills' in criteria and criteria['skills']:
            # Find candidates with any of the specified skills
            skill_candidates = db.session.query(
                CandidateSkill.candidate_id
            ).filter(
                CandidateSkill.skill_name.in_(criteria['skills'])
            ).distinct()
            
            query = query.filter(ResumeAnalysis.id.in_(skill_candidates))
        
        if 'location' in criteria and criteria['location']:
            query = query.filter(ResumeAnalysis.location == criteria['location'])
        
        if 'status' in criteria and criteria['status']:
            query = query.filter(ResumeAnalysis.status == criteria['status'])
        
        candidates = query.all()
        
        # Add candidates to pool
        added_count = 0
        for candidate in candidates:
            if self.add_candidate_to_pool(pool_id, candidate.id, 'Auto-populated'):
                added_count += 1
        
        logging.info(f"Auto-populated pool {pool_id} with {added_count} candidates")
        return added_count
    
    def suggest_pools_for_candidate(self, candidate_id: int) -> List[TalentPool]:
        """Suggest relevant talent pools for a candidate"""
        candidate = ResumeAnalysis.query.get(candidate_id)
        if not candidate:
            return []
        
        # Get candidate's skills
        candidate_skills = [s.skill_name for s in candidate.skills]
        
        suggested_pools = []
        active_pools = self.get_active_pools()
        
        for pool in active_pools:
            # Check if candidate already in pool
            existing = TalentPoolMember.query.filter_by(
                pool_id=pool.id,
                candidate_id=candidate_id
            ).first()
            
            if existing:
                continue
            
            # Score pool relevance
            relevance_score = 0
            
            if pool.pool_criteria and isinstance(pool.pool_criteria, dict):
                criteria = pool.pool_criteria
                
                # Check rating match
                if 'min_rating' in criteria and candidate.overall_fit_rating:
                    if candidate.overall_fit_rating >= criteria['min_rating']:
                        relevance_score += 2
                
                # Check skill match
                if 'skills' in criteria and criteria['skills'] and candidate_skills:
                    matching_skills = set(criteria['skills']) & set(candidate_skills)
                    if matching_skills:
                        relevance_score += len(matching_skills)
                
                # Check location match
                if 'location' in criteria and candidate.location:
                    if criteria['location'] == candidate.location:
                        relevance_score += 1
                
                # Check status match
                if 'status' in criteria and candidate.status:
                    if criteria['status'] == candidate.status:
                        relevance_score += 1
            
            if relevance_score > 0:
                suggested_pools.append((pool, relevance_score))
        
        # Sort by relevance score
        suggested_pools.sort(key=lambda x: x[1], reverse=True)
        
        return [pool for pool, score in suggested_pools[:5]]
    
    def merge_pools(self, source_pool_id: int, target_pool_id: int) -> bool:
        """Merge one talent pool into another"""
        try:
            source_members = TalentPoolMember.query.filter_by(pool_id=source_pool_id).all()
            
            moved_count = 0
            for member in source_members:
                # Check if already in target pool
                existing = TalentPoolMember.query.filter_by(
                    pool_id=target_pool_id,
                    candidate_id=member.candidate_id
                ).first()
                
                if not existing:
                    member.pool_id = target_pool_id
                    moved_count += 1
            
            # Update member counts
            target_pool = TalentPool.query.get(target_pool_id)
            if target_pool:
                target_pool.member_count = TalentPoolMember.query.filter_by(
                    pool_id=target_pool_id
                ).count()
            
            # Deactivate source pool
            source_pool = TalentPool.query.get(source_pool_id)
            if source_pool:
                source_pool.is_active = False
                source_pool.member_count = 0
            
            db.session.commit()
            logging.info(f"Merged {moved_count} members from pool {source_pool_id} to {target_pool_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error merging pools: {e}")
            db.session.rollback()
            return False