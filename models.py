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
