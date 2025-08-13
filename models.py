from app import db
from datetime import datetime
from sqlalchemy import Text

class ResumeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Extracted candidate information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(255))
    
    # Resume content
    resume_text = db.Column(Text)
    
    # AI Analysis results
    candidate_strengths = db.Column(Text)  # JSON string
    candidate_weaknesses = db.Column(Text)  # JSON string
    risk_factor_score = db.Column(db.Float)
    risk_factor_explanation = db.Column(Text)
    reward_factor_score = db.Column(db.Float)
    reward_factor_explanation = db.Column(Text)
    overall_fit_rating = db.Column(db.Float)
    justification = db.Column(Text)
    
    # Job matching data
    relevant_jobs = db.Column(Text)  # JSON string of ZipRecruiter job matches
    
    def __repr__(self):
        return f'<ResumeAnalysis {self.filename}>'
