"""
Task and Follow-up Management Service for TalentCompass AI
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from models import RecruiterTask, ResumeAnalysis, db
from sqlalchemy import and_, or_, func
import logging

class TaskManagementService:
    """Manage recruiter tasks and follow-ups"""
    
    def create_task(
        self,
        candidate_id: int,
        task_type: str,
        title: str,
        description: str = None,
        due_date: datetime = None,
        assigned_to: str = None,
        priority: str = 'medium'
    ) -> RecruiterTask:
        """Create a new task for a candidate"""
        if not due_date:
            # Default to 3 days from now
            due_date = datetime.utcnow() + timedelta(days=3)
        
        task = RecruiterTask(
            candidate_id=candidate_id,
            task_type=task_type,
            task_title=title,
            task_description=description,
            due_date=due_date,
            assigned_to=assigned_to,
            priority=priority,
            status='pending'
        )
        
        db.session.add(task)
        db.session.commit()
        
        return task
    
    def get_upcoming_tasks(
        self,
        assigned_to: str = None,
        days_ahead: int = 7
    ) -> List[RecruiterTask]:
        """Get upcoming tasks within specified days"""
        cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        query = RecruiterTask.query.filter(
            and_(
                RecruiterTask.status != 'completed',
                RecruiterTask.due_date <= cutoff_date
            )
        )
        
        if assigned_to:
            query = query.filter(RecruiterTask.assigned_to == assigned_to)
        
        return query.order_by(RecruiterTask.due_date).all()
    
    def get_overdue_tasks(
        self,
        assigned_to: str = None
    ) -> List[RecruiterTask]:
        """Get overdue tasks"""
        query = RecruiterTask.query.filter(
            and_(
                RecruiterTask.status != 'completed',
                RecruiterTask.due_date < datetime.utcnow()
            )
        )
        
        if assigned_to:
            query = query.filter(RecruiterTask.assigned_to == assigned_to)
        
        return query.order_by(RecruiterTask.priority.desc(), RecruiterTask.due_date).all()
    
    def update_task_status(
        self,
        task_id: int,
        status: str,
        notes: str = None
    ) -> bool:
        """Update task status"""
        task = RecruiterTask.query.get(task_id)
        if not task:
            return False
        
        task.status = status
        if status == 'completed':
            task.completed_date = datetime.utcnow()
        
        if notes:
            task.task_description = (task.task_description or '') + f'\n\nUpdate: {notes}'
        
        db.session.commit()
        return True
    
    def bulk_create_tasks(
        self,
        candidate_ids: List[int],
        task_template: Dict[str, Any]
    ) -> List[RecruiterTask]:
        """Create the same task for multiple candidates"""
        tasks = []
        
        for candidate_id in candidate_ids:
            task = RecruiterTask(
                candidate_id=candidate_id,
                task_type=task_template.get('type', 'follow_up'),
                task_title=task_template.get('title', 'Follow up'),
                task_description=task_template.get('description'),
                due_date=task_template.get('due_date', datetime.utcnow() + timedelta(days=3)),
                assigned_to=task_template.get('assigned_to'),
                priority=task_template.get('priority', 'medium'),
                status='pending'
            )
            db.session.add(task)
            tasks.append(task)
        
        db.session.commit()
        return tasks
    
    def get_task_statistics(
        self,
        assigned_to: str = None
    ) -> Dict[str, Any]:
        """Get task statistics for dashboard"""
        base_query = RecruiterTask.query
        
        if assigned_to:
            base_query = base_query.filter(RecruiterTask.assigned_to == assigned_to)
        
        total_tasks = base_query.count()
        completed_tasks = base_query.filter(RecruiterTask.status == 'completed').count()
        pending_tasks = base_query.filter(RecruiterTask.status == 'pending').count()
        overdue_tasks = base_query.filter(
            and_(
                RecruiterTask.status != 'completed',
                RecruiterTask.due_date < datetime.utcnow()
            )
        ).count()
        
        # Get task distribution by type
        task_types = db.session.query(
            RecruiterTask.task_type,
            func.count(RecruiterTask.id).label('count')
        ).filter(
            RecruiterTask.assigned_to == assigned_to if assigned_to else True
        ).group_by(
            RecruiterTask.task_type
        ).all()
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'pending': pending_tasks,
            'overdue': overdue_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'task_types': {tt: count for tt, count in task_types}
        }
    
    def create_interview_schedule(
        self,
        candidate_id: int,
        interview_rounds: List[Dict[str, Any]],
        coordinator: str = None
    ) -> List[RecruiterTask]:
        """Create a series of interview tasks"""
        tasks = []
        
        for round_info in interview_rounds:
            task = RecruiterTask(
                candidate_id=candidate_id,
                task_type='interview',
                task_title=f"Interview: {round_info.get('title', 'Round')}",
                task_description=f"Interviewer: {round_info.get('interviewer', 'TBD')}\n"
                               f"Focus: {round_info.get('focus', 'General')}\n"
                               f"Duration: {round_info.get('duration', '60')} minutes",
                due_date=round_info.get('date', datetime.utcnow() + timedelta(days=7)),
                assigned_to=coordinator or round_info.get('interviewer'),
                priority=round_info.get('priority', 'high'),
                status='pending'
            )
            db.session.add(task)
            tasks.append(task)
        
        db.session.commit()
        return tasks