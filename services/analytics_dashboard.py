"""
Analytics Dashboard Service for TalentCompass AI
Provides comprehensive recruitment metrics and insights
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import func, and_, or_
from models import (
    ResumeAnalysis, CandidateReferral, RecruiterTask, 
    CommunicationLog, CandidateAssessment, TalentPool,
    CandidateSkill, db
)
import json

class AnalyticsDashboardService:
    """Generate analytics and metrics for recruitment dashboard"""
    
    def get_overview_metrics(self) -> Dict[str, Any]:
        """Get high-level overview metrics"""
        # Total candidates
        total_candidates = ResumeAnalysis.query.count()
        active_candidates = ResumeAnalysis.query.filter_by(status='active').count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_candidates = ResumeAnalysis.query.filter(
            ResumeAnalysis.upload_date >= thirty_days_ago
        ).count()
        
        # Average ratings
        avg_rating = db.session.query(
            func.avg(ResumeAnalysis.overall_fit_rating)
        ).filter(
            ResumeAnalysis.overall_fit_rating.isnot(None)
        ).scalar() or 0
        
        # Task metrics
        total_tasks = RecruiterTask.query.count()
        completed_tasks = RecruiterTask.query.filter_by(status='completed').count()
        overdue_tasks = RecruiterTask.query.filter(
            and_(
                RecruiterTask.status != 'completed',
                RecruiterTask.due_date < datetime.utcnow()
            )
        ).count()
        
        # Referral metrics
        total_referrals = CandidateReferral.query.count()
        hired_referrals = CandidateReferral.query.filter_by(referral_status='hired').count()
        
        return {
            'total_candidates': total_candidates,
            'active_candidates': active_candidates,
            'new_candidates_30d': new_candidates,
            'average_rating': round(avg_rating, 2),
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'task_completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'total_referrals': total_referrals,
            'referral_success_rate': (hired_referrals / total_referrals * 100) if total_referrals > 0 else 0
        }
    
    def get_candidate_pipeline_metrics(self) -> Dict[str, Any]:
        """Get metrics for candidate pipeline stages"""
        pipeline_stages = db.session.query(
            ResumeAnalysis.status,
            func.count(ResumeAnalysis.id).label('count')
        ).group_by(
            ResumeAnalysis.status
        ).all()
        
        # Calculate conversion rates
        stages = {stage: count for stage, count in pipeline_stages}
        total = sum(stages.values())
        
        return {
            'stages': stages,
            'total': total,
            'conversion_rates': {
                stage: (count / total * 100) if total > 0 else 0
                for stage, count in stages.items()
            }
        }
    
    def get_source_effectiveness(self) -> Dict[str, Any]:
        """Analyze effectiveness of different candidate sources"""
        sources = db.session.query(
            ResumeAnalysis.source,
            func.count(ResumeAnalysis.id).label('count'),
            func.avg(ResumeAnalysis.overall_fit_rating).label('avg_rating')
        ).group_by(
            ResumeAnalysis.source
        ).all()
        
        source_metrics = []
        for source, count, avg_rating in sources:
            # Get hired count for this source
            hired_count = ResumeAnalysis.query.filter(
                and_(
                    ResumeAnalysis.source == source,
                    ResumeAnalysis.status == 'hired'
                )
            ).count()
            
            source_metrics.append({
                'source': source or 'Unknown',
                'total_candidates': count,
                'average_rating': round(avg_rating or 0, 2),
                'hired_count': hired_count,
                'hire_rate': (hired_count / count * 100) if count > 0 else 0
            })
        
        # Sort by effectiveness (hire rate * volume)
        source_metrics.sort(
            key=lambda x: x['hire_rate'] * x['total_candidates'],
            reverse=True
        )
        
        return {
            'sources': source_metrics,
            'best_source': source_metrics[0] if source_metrics else None
        }
    
    def get_skill_demand_analysis(self) -> Dict[str, Any]:
        """Analyze most in-demand skills"""
        # Get skill frequency
        skills = db.session.query(
            CandidateSkill.skill_name,
            func.count(CandidateSkill.id).label('count')
        ).group_by(
            CandidateSkill.skill_name
        ).order_by(
            func.count(CandidateSkill.id).desc()
        ).limit(20).all()
        
        skill_metrics = []
        for skill_name, count in skills:
            # Get average rating for candidates with this skill
            avg_rating = db.session.query(
                func.avg(ResumeAnalysis.overall_fit_rating)
            ).join(
                CandidateSkill
            ).filter(
                CandidateSkill.skill_name == skill_name
            ).scalar() or 0
            
            skill_metrics.append({
                'skill': skill_name,
                'candidate_count': count,
                'average_rating': round(avg_rating, 2)
            })
        
        return {
            'top_skills': skill_metrics[:10],
            'skill_distribution': skill_metrics
        }
    
    def get_time_to_fill_metrics(self) -> Dict[str, Any]:
        """Calculate time-to-fill metrics"""
        # Get candidates who were hired
        hired_candidates = ResumeAnalysis.query.filter_by(status='hired').all()
        
        if not hired_candidates:
            return {
                'average_time_to_fill': 0,
                'median_time_to_fill': 0,
                'fastest_hire': 0,
                'slowest_hire': 0
            }
        
        time_to_fill_days = []
        for candidate in hired_candidates:
            # Calculate days from upload to hire
            # In production, you'd track actual hire date
            days = (datetime.utcnow() - candidate.upload_date).days
            time_to_fill_days.append(days)
        
        time_to_fill_days.sort()
        
        return {
            'average_time_to_fill': sum(time_to_fill_days) / len(time_to_fill_days),
            'median_time_to_fill': time_to_fill_days[len(time_to_fill_days) // 2],
            'fastest_hire': min(time_to_fill_days),
            'slowest_hire': max(time_to_fill_days),
            'sample_size': len(hired_candidates)
        }
    
    def get_diversity_metrics(self) -> Dict[str, Any]:
        """Calculate diversity metrics for candidate pool"""
        # Location diversity
        locations = db.session.query(
            ResumeAnalysis.location,
            func.count(ResumeAnalysis.id).label('count')
        ).filter(
            ResumeAnalysis.location.isnot(None)
        ).group_by(
            ResumeAnalysis.location
        ).all()
        
        unique_locations = len(locations)
        total_with_location = sum(count for _, count in locations)
        
        # Skill diversity
        unique_skills = db.session.query(
            func.count(func.distinct(CandidateSkill.skill_name))
        ).scalar() or 0
        
        # Rating distribution
        rating_distribution = db.session.query(
            func.floor(ResumeAnalysis.overall_fit_rating).label('rating_band'),
            func.count(ResumeAnalysis.id).label('count')
        ).filter(
            ResumeAnalysis.overall_fit_rating.isnot(None)
        ).group_by(
            func.floor(ResumeAnalysis.overall_fit_rating)
        ).all()
        
        return {
            'location_diversity': {
                'unique_locations': unique_locations,
                'top_locations': locations[:5] if locations else [],
                'geographic_spread': unique_locations / total_with_location if total_with_location > 0 else 0
            },
            'skill_diversity': {
                'unique_skills': unique_skills,
                'skill_variety_index': unique_skills / 100  # Normalized to 0-1
            },
            'rating_distribution': {
                str(int(band)): count for band, count in rating_distribution
            }
        }
    
    def get_recruiter_performance(self) -> Dict[str, Any]:
        """Analyze recruiter performance metrics"""
        # Task completion by recruiter
        task_performance = db.session.query(
            RecruiterTask.assigned_to,
            func.count(RecruiterTask.id).label('total_tasks'),
            func.sum(func.cast(RecruiterTask.status == 'completed', db.Integer)).label('completed_tasks')
        ).filter(
            RecruiterTask.assigned_to.isnot(None)
        ).group_by(
            RecruiterTask.assigned_to
        ).all()
        
        recruiter_metrics = []
        for recruiter, total, completed in task_performance:
            recruiter_metrics.append({
                'recruiter': recruiter,
                'total_tasks': total,
                'completed_tasks': completed or 0,
                'completion_rate': (completed / total * 100) if total > 0 else 0
            })
        
        # Sort by completion rate
        recruiter_metrics.sort(key=lambda x: x['completion_rate'], reverse=True)
        
        return {
            'recruiter_performance': recruiter_metrics,
            'top_performer': recruiter_metrics[0] if recruiter_metrics else None
        }
    
    def get_referral_analytics(self) -> Dict[str, Any]:
        """Analyze referral program effectiveness"""
        # Referral sources
        referral_sources = db.session.query(
            CandidateReferral.referrer_department,
            func.count(CandidateReferral.id).label('count'),
            func.sum(func.cast(CandidateReferral.referral_status == 'hired', db.Integer)).label('hired')
        ).filter(
            CandidateReferral.referrer_department.isnot(None)
        ).group_by(
            CandidateReferral.referrer_department
        ).all()
        
        department_metrics = []
        for dept, count, hired in referral_sources:
            department_metrics.append({
                'department': dept,
                'total_referrals': count,
                'hired_referrals': hired or 0,
                'success_rate': (hired / count * 100) if count > 0 and hired else 0
            })
        
        # Top referrers
        top_referrers = db.session.query(
            CandidateReferral.referrer_name,
            func.count(CandidateReferral.id).label('count'),
            func.sum(CandidateReferral.reward_points).label('total_points')
        ).group_by(
            CandidateReferral.referrer_name
        ).order_by(
            func.count(CandidateReferral.id).desc()
        ).limit(10).all()
        
        return {
            'department_performance': department_metrics,
            'top_referrers': [
                {
                    'name': name,
                    'referral_count': count,
                    'reward_points': points or 0
                }
                for name, count, points in top_referrers
            ]
        }
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate comprehensive weekly report"""
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        
        # New candidates this week
        new_candidates = ResumeAnalysis.query.filter(
            ResumeAnalysis.upload_date >= one_week_ago
        ).count()
        
        # Tasks completed this week
        tasks_completed = RecruiterTask.query.filter(
            and_(
                RecruiterTask.completed_date >= one_week_ago,
                RecruiterTask.status == 'completed'
            )
        ).count()
        
        # High-rated candidates added
        high_rated = ResumeAnalysis.query.filter(
            and_(
                ResumeAnalysis.upload_date >= one_week_ago,
                ResumeAnalysis.overall_fit_rating >= 8.0
            )
        ).count()
        
        return {
            'week_ending': datetime.utcnow().strftime('%Y-%m-%d'),
            'new_candidates': new_candidates,
            'tasks_completed': tasks_completed,
            'high_rated_candidates': high_rated,
            'overview_metrics': self.get_overview_metrics(),
            'source_effectiveness': self.get_source_effectiveness(),
            'top_skills': self.get_skill_demand_analysis()['top_skills'][:5]
        }