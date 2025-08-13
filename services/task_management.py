"""
Task Management Service for TalentCompass AI
Handles task creation, tracking, reminders, and productivity analytics
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app import db
from models import RecruiterTask, ResumeAnalysis, TalentPool
import logging

class TaskManagementService:
    """Service for managing recruiter tasks and follow-ups"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # ============= Task Creation =============
    
    def create_task(self, 
                   title: str,
                   task_type: str,
                   due_date: datetime,
                   priority: str = 'medium',
                   description: str = None,
                   assigned_to: str = None,
                   candidate_id: int = None,
                   referral_id: int = None,
                   pool_id: int = None,
                   reminder_date: datetime = None) -> RecruiterTask:
        """
        Create a new task
        
        Args:
            title: Task title
            task_type: Type of task (follow_up, interview, etc.)
            due_date: When the task is due
            priority: Task priority (low, medium, high, urgent)
            description: Detailed task description
            assigned_to: Person responsible
            candidate_id: Related candidate ID
            referral_id: Related referral ID
            pool_id: Related talent pool ID
            reminder_date: When to send reminder
        
        Returns:
            Created RecruiterTask object
        """
        try:
            task = RecruiterTask(
                task_title=title,
                task_type=task_type,
                due_date=due_date,
                priority=priority,
                task_description=description,
                assigned_to=assigned_to,
                candidate_id=candidate_id,
                referral_id=referral_id,
                pool_id=pool_id,
                reminder_date=reminder_date,
                status='pending'
            )
            
            db.session.add(task)
            db.session.commit()
            
            self.logger.info(f"Created task: {title} (ID: {task.id})")
            return task
            
        except Exception as e:
            self.logger.error(f"Error creating task: {e}")
            db.session.rollback()
            raise
    
    def create_candidate_task(self, candidate_id: int, task_type: str, 
                             days_from_now: int = 1) -> RecruiterTask:
        """
        Create a task for a specific candidate with predefined templates
        
        Args:
            candidate_id: Candidate ID
            task_type: Type of task
            days_from_now: Days until due date
        
        Returns:
            Created RecruiterTask object
        """
        # Task templates
        templates = {
            'follow_up': {
                'title': 'Follow up with candidate',
                'description': 'Send follow-up email or call to check interest and availability',
                'priority': 'medium'
            },
            'screening_call': {
                'title': 'Initial screening call',
                'description': 'Conduct 15-30 minute screening call to assess basic qualifications',
                'priority': 'high'
            },
            'interview': {
                'title': 'Schedule interview',
                'description': 'Coordinate interview with hiring manager and candidate',
                'priority': 'high'
            },
            'reference_check': {
                'title': 'Check references',
                'description': 'Contact provided references to verify candidate information',
                'priority': 'medium'
            },
            'offer': {
                'title': 'Extend offer',
                'description': 'Prepare and send formal job offer to candidate',
                'priority': 'urgent'
            },
            'assessment': {
                'title': 'Send assessment',
                'description': 'Send technical or behavioral assessment to candidate',
                'priority': 'medium'
            },
            'onboarding': {
                'title': 'Begin onboarding',
                'description': 'Start onboarding process for accepted candidate',
                'priority': 'medium'
            }
        }
        
        template = templates.get(task_type, {
            'title': f'{task_type.replace("_", " ").title()}',
            'description': '',
            'priority': 'medium'
        })
        
        # Get candidate info for personalized title
        candidate = ResumeAnalysis.query.get(candidate_id)
        if candidate:
            name = f"{candidate.first_name} {candidate.last_name}".strip() or "Candidate"
            template['title'] = f"{template['title']} - {name}"
        
        due_date = datetime.utcnow() + timedelta(days=days_from_now)
        
        return self.create_task(
            title=template['title'],
            task_type=task_type,
            due_date=due_date,
            priority=template['priority'],
            description=template['description'],
            candidate_id=candidate_id
        )
    
    # ============= Task Retrieval =============
    
    def get_tasks(self, 
                  status: str = None,
                  assigned_to: str = None,
                  priority: str = None,
                  task_type: str = None,
                  overdue_only: bool = False,
                  upcoming_days: int = None) -> List[RecruiterTask]:
        """
        Get tasks with various filters
        
        Args:
            status: Filter by status
            assigned_to: Filter by assignee
            priority: Filter by priority
            task_type: Filter by type
            overdue_only: Show only overdue tasks
            upcoming_days: Show tasks due in next N days
        
        Returns:
            List of matching tasks
        """
        query = RecruiterTask.query
        
        if status:
            query = query.filter_by(status=status)
        
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        
        if priority:
            query = query.filter_by(priority=priority)
        
        if task_type:
            query = query.filter_by(task_type=task_type)
        
        if overdue_only:
            query = query.filter(
                RecruiterTask.due_date < datetime.utcnow(),
                RecruiterTask.status.in_(['pending', 'in_progress'])
            )
        
        if upcoming_days:
            future_date = datetime.utcnow() + timedelta(days=upcoming_days)
            query = query.filter(
                RecruiterTask.due_date <= future_date,
                RecruiterTask.due_date >= datetime.utcnow()
            )
        
        # Order by priority and due date
        priority_order = db.case(
            (RecruiterTask.priority == 'urgent', 1),
            (RecruiterTask.priority == 'high', 2),
            (RecruiterTask.priority == 'medium', 3),
            (RecruiterTask.priority == 'low', 4),
            else_=5
        )
        
        return query.order_by(priority_order, RecruiterTask.due_date).all()
    
    def get_candidate_tasks(self, candidate_id: int) -> List[RecruiterTask]:
        """Get all tasks for a specific candidate"""
        return RecruiterTask.query.filter_by(candidate_id=candidate_id).order_by(
            RecruiterTask.due_date
        ).all()
    
    def get_overdue_tasks(self) -> List[RecruiterTask]:
        """Get all overdue tasks"""
        return self.get_tasks(overdue_only=True)
    
    def get_today_tasks(self) -> List[RecruiterTask]:
        """Get tasks due today"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        return RecruiterTask.query.filter(
            RecruiterTask.due_date >= today_start,
            RecruiterTask.due_date < today_end,
            RecruiterTask.status.in_(['pending', 'in_progress'])
        ).order_by(RecruiterTask.priority).all()
    
    # ============= Task Updates =============
    
    def update_task_status(self, task_id: int, status: str, 
                          outcome: str = None, notes: str = None,
                          time_spent: int = None) -> bool:
        """
        Update task status
        
        Args:
            task_id: Task ID
            status: New status
            outcome: Task outcome (for completed tasks)
            notes: Additional notes
            time_spent: Time spent in minutes
        
        Returns:
            Success status
        """
        try:
            task = RecruiterTask.query.get(task_id)
            if not task:
                return False
            
            task.status = status
            
            if status == 'completed':
                task.completed_date = datetime.utcnow()
            
            if outcome:
                task.outcome = outcome
            
            if notes:
                task.notes = notes
            
            if time_spent:
                task.time_spent_minutes = time_spent
            
            db.session.commit()
            self.logger.info(f"Updated task {task_id} status to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating task status: {e}")
            db.session.rollback()
            return False
    
    def complete_task(self, task_id: int, outcome: str = None) -> bool:
        """Mark task as completed"""
        return self.update_task_status(task_id, 'completed', outcome=outcome)
    
    def cancel_task(self, task_id: int, reason: str = None) -> bool:
        """Cancel a task"""
        return self.update_task_status(task_id, 'cancelled', notes=reason)
    
    def snooze_task(self, task_id: int, days: int = 1) -> bool:
        """Postpone task by specified days"""
        try:
            task = RecruiterTask.query.get(task_id)
            if not task:
                return False
            
            task.due_date = task.due_date + timedelta(days=days)
            if task.reminder_date:
                task.reminder_date = task.reminder_date + timedelta(days=days)
            
            db.session.commit()
            self.logger.info(f"Snoozed task {task_id} by {days} days")
            return True
            
        except Exception as e:
            self.logger.error(f"Error snoozing task: {e}")
            db.session.rollback()
            return False
    
    # ============= Bulk Operations =============
    
    def create_interview_tasks(self, candidate_id: int) -> List[RecruiterTask]:
        """Create a set of tasks for interview process"""
        tasks = []
        
        # Pre-interview tasks
        tasks.append(self.create_candidate_task(candidate_id, 'screening_call', 1))
        tasks.append(self.create_candidate_task(candidate_id, 'interview', 3))
        
        # Post-interview tasks
        tasks.append(self.create_candidate_task(candidate_id, 'reference_check', 5))
        tasks.append(self.create_candidate_task(candidate_id, 'offer', 7))
        
        return tasks
    
    def mark_overdue_tasks(self) -> int:
        """Mark all overdue tasks with overdue status"""
        try:
            overdue_tasks = self.get_overdue_tasks()
            count = 0
            
            for task in overdue_tasks:
                if task.status != 'overdue':
                    task.status = 'overdue'
                    count += 1
            
            db.session.commit()
            self.logger.info(f"Marked {count} tasks as overdue")
            return count
            
        except Exception as e:
            self.logger.error(f"Error marking overdue tasks: {e}")
            db.session.rollback()
            return 0
    
    # ============= Analytics =============
    
    def get_task_statistics(self, assigned_to: str = None) -> Dict[str, Any]:
        """
        Get task statistics
        
        Args:
            assigned_to: Filter by assignee
        
        Returns:
            Dictionary of statistics
        """
        query = RecruiterTask.query
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        
        all_tasks = query.all()
        
        stats = {
            'total_tasks': len(all_tasks),
            'pending': len([t for t in all_tasks if t.status == 'pending']),
            'in_progress': len([t for t in all_tasks if t.status == 'in_progress']),
            'completed': len([t for t in all_tasks if t.status == 'completed']),
            'overdue': len([t for t in all_tasks if t.is_overdue()]),
            'due_today': len(self.get_today_tasks()),
            'by_priority': {
                'urgent': len([t for t in all_tasks if t.priority == 'urgent' and t.status in ['pending', 'in_progress']]),
                'high': len([t for t in all_tasks if t.priority == 'high' and t.status in ['pending', 'in_progress']]),
                'medium': len([t for t in all_tasks if t.priority == 'medium' and t.status in ['pending', 'in_progress']]),
                'low': len([t for t in all_tasks if t.priority == 'low' and t.status in ['pending', 'in_progress']])
            },
            'by_type': {}
        }
        
        # Count by type
        for task in all_tasks:
            if task.status in ['pending', 'in_progress']:
                stats['by_type'][task.task_type] = stats['by_type'].get(task.task_type, 0) + 1
        
        # Calculate completion rate
        if stats['total_tasks'] > 0:
            stats['completion_rate'] = round((stats['completed'] / stats['total_tasks']) * 100, 1)
        else:
            stats['completion_rate'] = 0
        
        # Calculate average time to complete (for completed tasks)
        completed_tasks = [t for t in all_tasks if t.status == 'completed' and t.completed_date]
        if completed_tasks:
            total_time = sum([
                (t.completed_date - t.created_date).days 
                for t in completed_tasks
            ])
            stats['avg_completion_days'] = round(total_time / len(completed_tasks), 1)
        else:
            stats['avg_completion_days'] = 0
        
        return stats
    
    def get_productivity_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Get productivity report for specified period
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Productivity metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get tasks created and completed in period
        tasks_created = RecruiterTask.query.filter(
            RecruiterTask.created_date >= start_date
        ).all()
        
        tasks_completed = RecruiterTask.query.filter(
            RecruiterTask.completed_date >= start_date
        ).all()
        
        # Group by assignee
        assignee_stats = {}
        for task in tasks_completed:
            if task.assigned_to:
                if task.assigned_to not in assignee_stats:
                    assignee_stats[task.assigned_to] = {
                        'completed': 0,
                        'total_time': 0,
                        'on_time': 0,
                        'late': 0
                    }
                
                assignee_stats[task.assigned_to]['completed'] += 1
                
                if task.time_spent_minutes:
                    assignee_stats[task.assigned_to]['total_time'] += task.time_spent_minutes
                
                if task.completed_date <= task.due_date:
                    assignee_stats[task.assigned_to]['on_time'] += 1
                else:
                    assignee_stats[task.assigned_to]['late'] += 1
        
        return {
            'period_days': days,
            'tasks_created': len(tasks_created),
            'tasks_completed': len(tasks_completed),
            'completion_rate': round((len(tasks_completed) / len(tasks_created) * 100), 1) if tasks_created else 0,
            'by_assignee': assignee_stats,
            'busiest_day': self._get_busiest_day(tasks_created),
            'most_common_type': self._get_most_common_type(tasks_created)
        }
    
    def _get_busiest_day(self, tasks: List[RecruiterTask]) -> str:
        """Find the busiest day of week"""
        if not tasks:
            return 'N/A'
        
        days = {}
        for task in tasks:
            day = task.created_date.strftime('%A')
            days[day] = days.get(day, 0) + 1
        
        return max(days.items(), key=lambda x: x[1])[0] if days else 'N/A'
    
    def _get_most_common_type(self, tasks: List[RecruiterTask]) -> str:
        """Find most common task type"""
        if not tasks:
            return 'N/A'
        
        types = {}
        for task in tasks:
            types[task.task_type] = types.get(task.task_type, 0) + 1
        
        return max(types.items(), key=lambda x: x[1])[0] if types else 'N/A'