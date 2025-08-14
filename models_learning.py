"""
Database models for Scout's self-learning capabilities
"""

from app import db
from datetime import datetime

class SearchInteraction(db.Model):
    """Track user interactions with search results"""
    __tablename__ = 'search_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(500), nullable=False)
    action = db.Column(db.String(50))  # clicked, saved, contacted, ignored
    result_id = db.Column(db.Integer)  # ID of the candidate/result interacted with
    result_rank = db.Column(db.Integer)  # Position in search results
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(100))
    
    # Additional context
    filters_used = db.Column(db.JSON)
    total_results = db.Column(db.Integer)
    
    # Indexes for analysis
    __table_args__ = (
        db.Index('idx_search_query', 'query'),
        db.Index('idx_search_timestamp', 'timestamp'),
        db.Index('idx_search_action', 'action'),
    )

class SuccessfulPlacement(db.Model):
    """Track successful candidate placements"""
    __tablename__ = 'successful_placements'
    
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('resume_analysis.id'))
    job_title = db.Column(db.String(200))
    job_trade = db.Column(db.String(100))
    
    # Matching factors
    skills_matched = db.Column(db.JSON)
    certifications_matched = db.Column(db.JSON)
    experience_years_required = db.Column(db.Integer)
    location_matched = db.Column(db.Boolean)
    
    # Outcome data
    placement_date = db.Column(db.DateTime, default=datetime.utcnow)
    starting_salary = db.Column(db.Float)
    placement_type = db.Column(db.String(50))  # permanent, contract, temp
    
    # Learning metrics
    time_to_hire = db.Column(db.Integer)  # Days from first contact to hire
    candidate_source = db.Column(db.String(100))  # internal, github, linkedin, etc.
    
    # Relationship
    candidate = db.relationship('ResumeAnalysis', backref='placements')

class QueryImprovement(db.Model):
    """Store query improvements and their effectiveness"""
    __tablename__ = 'query_improvements'
    
    id = db.Column(db.Integer, primary_key=True)
    original_query = db.Column(db.String(500))
    improved_query = db.Column(db.String(500))
    
    # Improvement details
    keywords_added = db.Column(db.JSON)
    filters_suggested = db.Column(db.JSON)
    
    # Effectiveness metrics
    times_used = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)

class UserPreference(db.Model):
    """Track learned user preferences"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100))
    preference_type = db.Column(db.String(50))  # result_count, detail_level, etc.
    preference_value = db.Column(db.String(200))
    
    # Learning context
    learned_from = db.Column(db.String(50))  # feedback, behavior, explicit
    confidence = db.Column(db.Float, default=0.5)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SkillAssociation(db.Model):
    """Track which skills commonly appear together"""
    __tablename__ = 'skill_associations'
    
    id = db.Column(db.Integer, primary_key=True)
    primary_skill = db.Column(db.String(100), nullable=False)
    associated_skill = db.Column(db.String(100), nullable=False)
    
    # Association strength
    co_occurrence_count = db.Column(db.Integer, default=1)
    correlation_strength = db.Column(db.Float, default=0.0)
    
    # Context
    trade_context = db.Column(db.String(100))  # electrician, hvac, etc.
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint on skill pairs
    __table_args__ = (
        db.UniqueConstraint('primary_skill', 'associated_skill', 'trade_context'),
        db.Index('idx_skill_primary', 'primary_skill'),
        db.Index('idx_skill_associated', 'associated_skill'),
    )

class DatabaseOptimization(db.Model):
    """Track suggested and applied database optimizations"""
    __tablename__ = 'database_optimizations'
    
    id = db.Column(db.Integer, primary_key=True)
    optimization_type = db.Column(db.String(50))  # index, cleanup, etc.
    table_name = db.Column(db.String(100))
    column_name = db.Column(db.String(100))
    
    # Optimization details
    suggestion = db.Column(db.Text)
    reason = db.Column(db.Text)
    expected_improvement = db.Column(db.String(200))
    
    # Status tracking
    status = db.Column(db.String(50), default='suggested')  # suggested, applied, rejected
    suggested_at = db.Column(db.DateTime, default=datetime.utcnow)
    applied_at = db.Column(db.DateTime)
    
    # Performance metrics
    query_time_before = db.Column(db.Float)
    query_time_after = db.Column(db.Float)

class LearningFeedback(db.Model):
    """Store user feedback for continuous learning"""
    __tablename__ = 'learning_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    feedback_type = db.Column(db.String(50))  # search, recommendation, UI, etc.
    feedback_text = db.Column(db.Text)
    
    # Context
    context_data = db.Column(db.JSON)
    session_id = db.Column(db.String(100))
    
    # Sentiment analysis
    sentiment = db.Column(db.String(20))  # positive, negative, neutral
    actionable = db.Column(db.Boolean)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)