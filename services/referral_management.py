"""
Referral Management Service for TalentCompass AI
Handles employee referral tracking, rewards, and analytics
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, or_
from models import CandidateReferral, ResumeAnalysis, db
import logging

class ReferralManagementService:
    """Manage employee referral program"""
    
    def create_referral(self, 
                       candidate_id: int,
                       referrer_name: str,
                       referrer_email: str,
                       referrer_department: Optional[str] = None,
                       relationship: Optional[str] = None,
                       notes: Optional[str] = None) -> CandidateReferral:
        """Create a new referral"""
        try:
            referral = CandidateReferral(
                candidate_id=candidate_id,
                referrer_name=referrer_name,
                referrer_email=referrer_email,
                referrer_department=referrer_department,
                relationship_to_candidate=relationship,
                referral_notes=notes,
                referral_status='pending',
                reward_points=0
            )
            
            db.session.add(referral)
            db.session.commit()
            
            # Update candidate source
            candidate = ResumeAnalysis.query.get(candidate_id)
            if candidate and not candidate.source:
                candidate.source = 'Employee Referral'
                db.session.commit()
            
            logging.info(f"Created referral for candidate {candidate_id} by {referrer_name}")
            return referral
            
        except Exception as e:
            logging.error(f"Error creating referral: {e}")
            db.session.rollback()
            raise
    
    def update_referral_status(self, referral_id: int, new_status: str, 
                              reward_points: Optional[int] = None) -> bool:
        """Update referral status and optionally assign reward points"""
        try:
            referral = CandidateReferral.query.get(referral_id)
            if not referral:
                return False
            
            referral.referral_status = new_status
            
            # Assign reward points based on status
            if new_status == 'interviewed' and not referral.reward_points:
                referral.reward_points = 50  # Points for getting to interview
            elif new_status == 'hired':
                referral.reward_points = 500  # Bonus points for successful hire
                referral.hired_date = datetime.utcnow()
            
            # Override with custom points if provided
            if reward_points is not None:
                referral.reward_points = reward_points
            
            db.session.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error updating referral status: {e}")
            db.session.rollback()
            return False
    
    def get_referral_by_candidate(self, candidate_id: int) -> Optional[CandidateReferral]:
        """Get referral information for a specific candidate"""
        return CandidateReferral.query.filter_by(candidate_id=candidate_id).first()
    
    def get_referrals_by_referrer(self, referrer_email: str) -> List[CandidateReferral]:
        """Get all referrals made by a specific referrer"""
        return CandidateReferral.query.filter_by(
            referrer_email=referrer_email
        ).order_by(CandidateReferral.referral_date.desc()).all()
    
    def get_pending_referrals(self) -> List[CandidateReferral]:
        """Get all pending referrals that need review"""
        return CandidateReferral.query.filter_by(
            referral_status='pending'
        ).order_by(CandidateReferral.referral_date.desc()).all()
    
    def get_top_referrers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top referrers by points and successful hires"""
        results = db.session.query(
            CandidateReferral.referrer_name,
            CandidateReferral.referrer_email,
            CandidateReferral.referrer_department,
            func.count(CandidateReferral.id).label('total_referrals'),
            func.sum(CandidateReferral.reward_points).label('total_points'),
            func.sum(func.cast(CandidateReferral.referral_status == 'hired', db.Integer)).label('successful_hires')
        ).group_by(
            CandidateReferral.referrer_name,
            CandidateReferral.referrer_email,
            CandidateReferral.referrer_department
        ).order_by(
            func.sum(CandidateReferral.reward_points).desc()
        ).limit(limit).all()
        
        return [
            {
                'name': name,
                'email': email,
                'department': dept,
                'total_referrals': total,
                'total_points': points or 0,
                'successful_hires': hires or 0,
                'success_rate': (hires / total * 100) if total > 0 else 0
            }
            for name, email, dept, total, points, hires in results
        ]
    
    def get_referral_statistics(self) -> Dict[str, Any]:
        """Get comprehensive referral program statistics"""
        total_referrals = CandidateReferral.query.count()
        
        if total_referrals == 0:
            return {
                'total_referrals': 0,
                'pending': 0,
                'interviewed': 0,
                'hired': 0,
                'rejected': 0,
                'success_rate': 0,
                'total_points_awarded': 0,
                'average_time_to_hire': 0
            }
        
        # Status breakdown
        status_counts = db.session.query(
            CandidateReferral.referral_status,
            func.count(CandidateReferral.id)
        ).group_by(
            CandidateReferral.referral_status
        ).all()
        
        status_dict = dict(status_counts)
        
        # Calculate average time to hire for successful referrals
        hired_referrals = CandidateReferral.query.filter_by(
            referral_status='hired'
        ).all()
        
        avg_time_to_hire = 0
        if hired_referrals:
            total_days = sum(
                (r.hired_date - r.referral_date).days 
                for r in hired_referrals 
                if r.hired_date
            )
            avg_time_to_hire = total_days / len(hired_referrals) if hired_referrals else 0
        
        # Total points awarded
        total_points = db.session.query(
            func.sum(CandidateReferral.reward_points)
        ).scalar() or 0
        
        hired_count = status_dict.get('hired', 0)
        
        return {
            'total_referrals': total_referrals,
            'pending': status_dict.get('pending', 0),
            'interviewed': status_dict.get('interviewed', 0),
            'hired': hired_count,
            'rejected': status_dict.get('rejected', 0),
            'success_rate': (hired_count / total_referrals * 100) if total_referrals > 0 else 0,
            'total_points_awarded': total_points,
            'average_time_to_hire': round(avg_time_to_hire, 1)
        }
    
    def get_department_performance(self) -> List[Dict[str, Any]]:
        """Analyze referral performance by department"""
        results = db.session.query(
            CandidateReferral.referrer_department,
            func.count(CandidateReferral.id).label('total'),
            func.sum(func.cast(CandidateReferral.referral_status == 'hired', db.Integer)).label('hired'),
            func.sum(CandidateReferral.reward_points).label('points')
        ).filter(
            CandidateReferral.referrer_department.isnot(None)
        ).group_by(
            CandidateReferral.referrer_department
        ).all()
        
        return [
            {
                'department': dept,
                'total_referrals': total,
                'successful_hires': hired or 0,
                'success_rate': (hired / total * 100) if total > 0 else 0,
                'total_points': points or 0
            }
            for dept, total, hired, points in results
        ]
    
    def calculate_referral_bonus(self, referral_id: int) -> Dict[str, Any]:
        """Calculate referral bonus based on company policy"""
        referral = CandidateReferral.query.get(referral_id)
        if not referral:
            return {'error': 'Referral not found'}
        
        # Example bonus structure (customizable)
        bonus_structure = {
            'pending': 0,
            'interviewed': 100,  # $100 for getting to interview
            'hired': 1000,       # $1000 for successful hire
            'rejected': 0
        }
        
        bonus_amount = bonus_structure.get(referral.referral_status, 0)
        
        # Additional bonus for hard-to-fill positions
        candidate = ResumeAnalysis.query.get(referral.candidate_id)
        if candidate and candidate.overall_fit_rating and candidate.overall_fit_rating >= 9:
            bonus_amount *= 1.5  # 50% bonus for exceptional candidates
        
        return {
            'referral_id': referral_id,
            'referrer': referral.referrer_name,
            'status': referral.referral_status,
            'base_bonus': bonus_structure.get(referral.referral_status, 0),
            'total_bonus': bonus_amount,
            'reward_points': referral.reward_points
        }
    
    def send_referral_update(self, referral_id: int, message: str) -> bool:
        """Send update to referrer about their referral status"""
        # In production, this would integrate with email service
        referral = CandidateReferral.query.get(referral_id)
        if not referral:
            return False
        
        logging.info(f"Referral update for {referral.referrer_email}: {message}")
        # Here you would send actual email notification
        return True