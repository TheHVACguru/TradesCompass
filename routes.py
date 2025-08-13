import os
import json
import logging
from flask import render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app import app, db
from models import ResumeAnalysis
from services.text_extraction import extract_text_from_file
from services.ai_analysis import analyze_resume, extract_candidate_info
from services.ziprecruiter_api import search_relevant_jobs

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main upload page"""
    recent_analyses = ResumeAnalysis.query.order_by(ResumeAnalysis.upload_date.desc()).limit(5).all()
    return render_template('index.html', recent_analyses=recent_analyses)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    job_description = request.form.get('job_description', '').strip()
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(request.url)
    
    if not job_description:
        flash('Please provide a job description for analysis', 'error')
        return redirect(request.url)
    
    if file and file.filename and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from file
            resume_text = extract_text_from_file(filepath)
            
            if not resume_text.strip():
                flash('Could not extract text from the file. Please ensure it contains readable text.', 'error')
                os.remove(filepath)
                return redirect(url_for('index'))
            
            # Extract candidate information
            candidate_info = extract_candidate_info(resume_text)
            
            # Analyze resume against job description
            analysis_result = analyze_resume(resume_text, job_description)
            
            # Search for relevant jobs
            relevant_jobs = []
            if candidate_info.get('extracted_skills'):
                # Use extracted skills to search for relevant jobs
                skills_query = ' '.join(candidate_info.get('extracted_skills', [])[:3])  # Use top 3 skills
                relevant_jobs = search_relevant_jobs(skills_query)
            
            # Save to database
            resume_analysis = ResumeAnalysis(
                filename=filename,
                first_name=candidate_info.get('first_name'),
                last_name=candidate_info.get('last_name'),
                email=candidate_info.get('email'),
                resume_text=resume_text,
                candidate_strengths=json.dumps(analysis_result.get('candidate_strengths', [])),
                candidate_weaknesses=json.dumps(analysis_result.get('candidate_weaknesses', [])),
                risk_factor_score=analysis_result.get('risk_factor', {}).get('score'),
                risk_factor_explanation=analysis_result.get('risk_factor', {}).get('explanation'),
                reward_factor_score=analysis_result.get('reward_factor', {}).get('score'),
                reward_factor_explanation=analysis_result.get('reward_factor', {}).get('explanation'),
                overall_fit_rating=analysis_result.get('overall_fit_rating'),
                justification=analysis_result.get('justification_for_rating'),
                relevant_jobs=json.dumps(relevant_jobs)
            )
            
            db.session.add(resume_analysis)
            db.session.commit()
            
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            flash('Resume analyzed successfully!', 'success')
            return redirect(url_for('view_results', analysis_id=resume_analysis.id))
            
        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            flash(f'Error processing file: {str(e)}', 'error')
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload a PDF, DOCX, or TXT file.', 'error')
        return redirect(url_for('index'))

@app.route('/results/<int:analysis_id>')
def view_results(analysis_id):
    """View analysis results"""
    analysis = ResumeAnalysis.query.get_or_404(analysis_id)
    
    # Parse JSON fields
    strengths = json.loads(analysis.candidate_strengths) if analysis.candidate_strengths else []
    weaknesses = json.loads(analysis.candidate_weaknesses) if analysis.candidate_weaknesses else []
    relevant_jobs = json.loads(analysis.relevant_jobs) if analysis.relevant_jobs else []
    
    return render_template('results.html', 
                         analysis=analysis,
                         strengths=strengths,
                         weaknesses=weaknesses,
                         relevant_jobs=relevant_jobs)

@app.route('/history')
def view_history():
    """View all past analyses"""
    analyses = ResumeAnalysis.query.order_by(ResumeAnalysis.upload_date.desc()).all()
    return render_template('history.html', analyses=analyses)

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('index'))
