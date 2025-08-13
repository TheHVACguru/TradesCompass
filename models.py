from app import db
from datetime import datetime
from sqlalchemy import Text, Index

class ResumeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Extracted candidate information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(255), unique=True, index=True)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    
    # Resume content
    resume_text = db.Column(Text)
    
    # AI Analysis results
    candidate_strengths = db.Column(Text)  # JSON string
    candidate_weaknesses = db.Column(Text)  # JSON string
    risk_factor_score = db.Column(db.Float)
    risk_factor_explanation = db.Column(Text)
    reward_factor_score = db.Column(db.Float)
    reward_factor_explanation = db.Column(Text)
    overall_fit_rating = db.Column(db.Float, index=True)
    justification = db.Column(Text)
    
    # Job matching data
    relevant_jobs = db.Column(Text)  # JSON string of job matches from multiple sources
    
    # Enhanced tracking
    source = db.Column(db.String(50), default='manual_upload')  # manual_upload, email, etc.
    status = db.Column(db.String(50), default='active')  # active, archived, contacted
    notes = db.Column(Text)  # Recruiter notes
    
    # Relationship to skills and tags
    skills = db.relationship('CandidateSkill', backref='candidate', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('CandidateTag', backref='candidate', lazy='dynamic', cascade='all, delete-orphan')
    
    # Add indexes for common queries
    __table_args__ = (
        Index('ix_candidate_ratings', 'overall_fit_rating', 'risk_factor_score', 'reward_factor_score'),
        Index('ix_candidate_upload_date', 'upload_date'),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'filename': self.filename,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'overall_fit_rating': self.overall_fit_rating,
            'risk_factor_score': self.risk_factor_score,
            'reward_factor_score': self.reward_factor_score,
            'source': self.source,
            'status': self.status
        }
    
    def __repr__(self):
        return f'<ResumeAnalysis {self.filename}>'

class CandidateSkill(db.Model):
    """Track specific skills extracted from candidate resumes"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False, index=True)
    skill_level = db.Column(db.String(50))  # beginner, intermediate, advanced, expert
    years_experience = db.Column(db.Integer)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('candidate_id', 'skill_name'),
        Index('ix_skill_search', 'skill_name', 'skill_level'),
    )
    
    def __repr__(self):
        return f'<CandidateSkill {self.skill_name}>'

class CandidateTag(db.Model):
    """Custom tags for organizing and categorizing candidates"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=False)
    tag_name = db.Column(db.String(50), nullable=False, index=True)
    tag_color = db.Column(db.String(7), default='#6c757d')  # Hex color code
    created_by = db.Column(db.String(100))  # Who added this tag
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('candidate_id', 'tag_name'),
    )
    
    def __repr__(self):
        return f'<CandidateTag {self.tag_name}>'

class EmailProcessingLog(db.Model):
    """Log email processing for resume extraction"""
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.String(255), unique=True, nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500))
    processed_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='processed')  # processed, failed, skipped
    resume_analysis_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'))
    error_message = db.Column(Text)
    
    def __repr__(self):
        return f'<EmailProcessingLog {self.email_id}>'

class CandidateReferral(db.Model):
    """Track employee and executive referrals"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=False)
    referrer_name = db.Column(db.String(100), nullable=False)
    referrer_email = db.Column(db.String(255), nullable=False)
    referrer_department = db.Column(db.String(100))
    referral_date = db.Column(db.DateTime, default=datetime.utcnow)
    referral_notes = db.Column(Text)
    referral_status = db.Column(db.String(50), default='pending')  # pending, contacted, interviewed, hired, rejected
    reward_status = db.Column(db.String(50), default='pending')  # pending, eligible, awarded
    reward_points = db.Column(db.Integer, default=0)
    
    # Relationship
    candidate = db.relationship('ResumeAnalysis', backref='referrals')
    
    def __repr__(self):
        return f'<CandidateReferral by {self.referrer_name}>'

class TalentPool(db.Model):
    """Group candidates by role, level or industry"""
    id = db.Column(db.Integer, primary_key=True)
    pool_name = db.Column(db.String(100), nullable=False, unique=True)
    pool_type = db.Column(db.String(50))  # role, level, industry, custom
    description = db.Column(Text)
    created_by = db.Column(db.String(100))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with candidates
    candidates = db.relationship('ResumeAnalysis', secondary='talent_pool_candidates', backref='talent_pools')
    
    def __repr__(self):
        return f'<TalentPool {self.pool_name}>'

# Association table for many-to-many relationship
talent_pool_candidates = db.Table('talent_pool_candidates',
    db.Column('pool_id', db.Integer, db.ForeignKey('talent_pool.id'), primary_key=True),
    db.Column('candidate_id', db.Integer, db.ForeignKey('resume_analysis.id'), primary_key=True),
    db.Column('added_date', db.DateTime, default=datetime.utcnow)
)

class RecruiterTask(db.Model):
    """Enhanced task and follow-up management for recruiters"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=True)
    referral_id = db.Column(db.Integer, db.ForeignKey('candidate_referral.id'), nullable=True)
    pool_id = db.Column(db.Integer, db.ForeignKey('talent_pool.id'), nullable=True)
    
    task_type = db.Column(db.String(50), nullable=False)  # follow_up, interview, reference_check, offer, onboarding, screening_call, assessment
    task_title = db.Column(db.String(200), nullable=False)
    task_description = db.Column(Text)
    due_date = db.Column(db.DateTime, nullable=False)
    reminder_date = db.Column(db.DateTime)
    assigned_to = db.Column(db.String(100))
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(50), default='pending')  # pending, in_progress, completed, cancelled, overdue
    completed_date = db.Column(db.DateTime)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional tracking
    outcome = db.Column(Text)  # Result/outcome when completed
    notes = db.Column(Text)
    time_spent_minutes = db.Column(db.Integer)
    
    # Relationships
    candidate = db.relationship('ResumeAnalysis', backref='tasks')
    referral = db.relationship('CandidateReferral', backref='tasks', foreign_keys=[referral_id])
    pool = db.relationship('TalentPool', backref='tasks', foreign_keys=[pool_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_task_status_due', 'status', 'due_date'),
        Index('ix_task_assigned', 'assigned_to', 'status'),
    )
    
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status in ['completed', 'cancelled']:
            return False
        return datetime.utcnow() > self.due_date if self.due_date else False
    
    def __repr__(self):
        return f'<RecruiterTask {self.task_title}>'

class CommunicationLog(db.Model):
    """Track all communications with candidates"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=False)
    communication_type = db.Column(db.String(50), nullable=False)  # email, sms, call, meeting, linkedin
    subject = db.Column(db.String(500))
    content = db.Column(Text)
    direction = db.Column(db.String(20))  # inbound, outbound
    status = db.Column(db.String(50))  # sent, delivered, failed, replied
    sent_by = db.Column(db.String(100))
    sent_date = db.Column(db.DateTime, default=datetime.utcnow)
    template_used = db.Column(db.String(100))  # If a template was used
    
    # Relationship
    candidate = db.relationship('ResumeAnalysis', backref='communications')
    
    def __repr__(self):
        return f'<CommunicationLog {self.communication_type} to {self.candidate_id}>'

class ScoringScheme(db.Model):
    """Dynamic risk/reward scoring schemes"""
    id = db.Column(db.Integer, primary_key=True)
    scheme_name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(Text)
    
    # Weight factors (0-100 scale)
    experience_weight = db.Column(db.Integer, default=25)
    skills_weight = db.Column(db.Integer, default=25)
    education_weight = db.Column(db.Integer, default=15)
    leadership_weight = db.Column(db.Integer, default=10)
    culture_fit_weight = db.Column(db.Integer, default=10)
    location_weight = db.Column(db.Integer, default=5)
    availability_weight = db.Column(db.Integer, default=10)
    
    # Risk factors weights
    job_hopping_weight = db.Column(db.Integer, default=20)
    employment_gap_weight = db.Column(db.Integer, default=15)
    overqualification_weight = db.Column(db.Integer, default=10)
    
    is_default = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(100))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ScoringScheme {self.scheme_name}>'

class CandidateAssessment(db.Model):
    """Store results from third-party assessments"""
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'), nullable=False)
    assessment_type = db.Column(db.String(100), nullable=False)  # coding_test, psychometric, leadership, etc.
    assessment_provider = db.Column(db.String(100))  # HackerRank, Codility, etc.
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Float)
    max_score = db.Column(db.Float)
    percentile = db.Column(db.Float)  # Percentile rank if available
    result_summary = db.Column(Text)
    detailed_results = db.Column(Text)  # JSON string of detailed results
    assessment_url = db.Column(db.String(500))  # Link to full assessment
    
    # Relationship
    candidate = db.relationship('ResumeAnalysis', backref='assessments')
    
    def __repr__(self):
        return f'<CandidateAssessment {self.assessment_type} for {self.candidate_id}>'
