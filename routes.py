import os
import json
import logging
from urllib.parse import urlparse
from flask import render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app import app, db
from models import ResumeAnalysis, CandidateSkill, CandidateTag
from services.text_extraction import extract_text_from_file
from services.ai_analysis import analyze_resume, extract_candidate_info
from services.job_boards import search_relevant_jobs
from services.candidate_database import search_candidates, get_candidate_statistics, get_similar_candidates
from services.email_integration import EmailResumeProcessor
from services.salesforce_integration import SalesforceIntegration

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_redirect(referrer_url, fallback_endpoint):
    """Safely redirect to referrer only if it's from the same origin"""
    if not referrer_url:
        return redirect(url_for(fallback_endpoint))
    
    try:
        parsed_referrer = urlparse(referrer_url)
        # Only allow redirects with no netloc (relative URLs) or empty scheme
        # This prevents redirects to external sites
        if not parsed_referrer.netloc or not parsed_referrer.scheme:
            return redirect(referrer_url)
    except Exception:
        pass
    
    # Fallback to safe internal route
    return redirect(url_for(fallback_endpoint))

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
        return redirect(url_for('index'))
    
    file = request.files['file']
    job_description = request.form.get('job_description', '').strip()
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not job_description:
        flash('Please provide a job description for analysis', 'error')
        return redirect(url_for('index'))
    
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
                phone=candidate_info.get('phone'),
                location=candidate_info.get('location'),
                resume_text=resume_text,
                candidate_strengths=json.dumps(analysis_result.get('candidate_strengths', [])),
                candidate_weaknesses=json.dumps(analysis_result.get('candidate_weaknesses', [])),
                risk_factor_score=analysis_result.get('risk_factor', {}).get('score'),
                risk_factor_explanation=analysis_result.get('risk_factor', {}).get('explanation'),
                reward_factor_score=analysis_result.get('reward_factor', {}).get('score'),
                reward_factor_explanation=analysis_result.get('reward_factor', {}).get('explanation'),
                overall_fit_rating=analysis_result.get('overall_fit_rating'),
                justification=analysis_result.get('justification_for_rating'),
                relevant_jobs=json.dumps(relevant_jobs),
                source='manual_upload'
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

@app.route('/candidates')
def candidate_database():
    """Advanced candidate search and database view"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get search filters from query parameters
    skills = request.args.getlist('skills')
    min_fit_rating = request.args.get('min_fit_rating', type=float)
    max_risk_score = request.args.get('max_risk_score', type=float)
    min_reward_score = request.args.get('min_reward_score', type=float)
    location = request.args.get('location')
    experience_keywords = request.args.getlist('keywords')
    
    # Search candidates
    search_results = search_candidates(
        skills=skills if skills else None,
        min_fit_rating=min_fit_rating,
        max_risk_score=max_risk_score,
        min_reward_score=min_reward_score,
        location=location,
        experience_keywords=experience_keywords if experience_keywords else None,
        page=page,
        per_page=per_page
    )
    
    # Get statistics
    stats = get_candidate_statistics()
    
    return render_template('candidates.html', 
                         search_results=search_results,
                         stats=stats,
                         current_filters={
                             'skills': skills,
                             'min_fit_rating': min_fit_rating,
                             'max_risk_score': max_risk_score,
                             'min_reward_score': min_reward_score,
                             'location': location,
                             'keywords': experience_keywords
                         })

@app.route('/candidates/<int:candidate_id>')
def candidate_detail(candidate_id):
    """Detailed view of a specific candidate"""
    analysis = ResumeAnalysis.query.get_or_404(candidate_id)
    
    # Parse JSON fields
    strengths = json.loads(analysis.candidate_strengths) if analysis.candidate_strengths else []
    weaknesses = json.loads(analysis.candidate_weaknesses) if analysis.candidate_weaknesses else []
    relevant_jobs = json.loads(analysis.relevant_jobs) if analysis.relevant_jobs else []
    
    # Get similar candidates
    similar_candidates = get_similar_candidates(candidate_id, limit=5)
    
    return render_template('candidate_detail.html',
                         analysis=analysis,
                         strengths=strengths,
                         weaknesses=weaknesses,
                         relevant_jobs=relevant_jobs,
                         similar_candidates=similar_candidates)

@app.route('/candidates/<int:candidate_id>/update', methods=['POST'])
def update_candidate(candidate_id):
    """Update candidate status and notes"""
    analysis = ResumeAnalysis.query.get_or_404(candidate_id)
    
    status = request.form.get('status')
    notes = request.form.get('notes')
    
    if status and status in ['active', 'contacted', 'archived']:
        analysis.status = status
    
    if notes is not None:
        analysis.notes = notes
    
    db.session.commit()
    flash('Candidate updated successfully!', 'success')
    return redirect(url_for('candidate_detail', candidate_id=candidate_id))

@app.route('/candidates/<int:candidate_id>/add_tag', methods=['POST'])
def add_candidate_tag(candidate_id):
    """Add a tag to a candidate"""
    analysis = ResumeAnalysis.query.get_or_404(candidate_id)
    
    tag_name = request.form.get('tag_name', '').strip()
    tag_color = request.form.get('tag_color', '#6c757d')
    
    if tag_name:
        # Check if tag already exists
        existing_tag = CandidateTag.query.filter_by(
            candidate_id=candidate_id,
            tag_name=tag_name
        ).first()
        
        if not existing_tag:
            new_tag = CandidateTag(
                candidate_id=candidate_id,
                tag_name=tag_name,
                tag_color=tag_color
            )
            db.session.add(new_tag)
            db.session.commit()
            flash(f'Tag "{tag_name}" added successfully!', 'success')
        else:
            flash(f'Tag "{tag_name}" already exists for this candidate.', 'warning')
    
    return redirect(url_for('candidate_detail', candidate_id=candidate_id))

@app.route('/email_processing')
def email_processing():
    """Email processing dashboard"""
    from models import EmailProcessingLog
    
    recent_logs = EmailProcessingLog.query.order_by(
        EmailProcessingLog.processed_date.desc()
    ).limit(20).all()
    
    # Get processing statistics
    total_processed = EmailProcessingLog.query.filter_by(status='processed').count()
    total_failed = EmailProcessingLog.query.filter_by(status='failed').count()
    total_skipped = EmailProcessingLog.query.filter_by(status='skipped').count()
    
    stats = {
        'total_processed': total_processed,
        'total_failed': total_failed,
        'total_skipped': total_skipped,
        'total_emails': total_processed + total_failed + total_skipped
    }
    
    return render_template('email_processing.html', 
                         recent_logs=recent_logs,
                         stats=stats)

@app.route('/process_emails', methods=['POST'])
def process_emails():
    """Process new emails manually"""
    job_description = request.form.get('job_description', '').strip()
    
    processor = EmailResumeProcessor()
    results = processor.process_new_emails(job_description=job_description if job_description else None)
    
    if 'error' in results:
        flash(f'Error processing emails: {results["error"]}', 'error')
    else:
        message = f'Processing complete! Processed: {results["processed"]}, Failed: {results["failed"]}, Skipped: {results["skipped"]}'
        flash(message, 'success')
        
        # Show details about new candidates
        if results["candidates"]:
            candidate_names = [f"{c.get('first_name', 'Unknown')} {c.get('last_name', '')}" for c in results["candidates"]]
            flash(f'New candidates: {", ".join(candidate_names)}', 'info')
    
    return redirect(url_for('email_processing'))

@app.route('/dashboard')
def dashboard():
    """Enhanced dashboard with statistics"""
    stats = get_candidate_statistics()
    
    # Recent activity
    recent_analyses = ResumeAnalysis.query.order_by(
        ResumeAnalysis.upload_date.desc()
    ).limit(10).all()
    
    # Top candidates by fit rating
    top_candidates = ResumeAnalysis.query.filter(
        ResumeAnalysis.overall_fit_rating.isnot(None)
    ).order_by(ResumeAnalysis.overall_fit_rating.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         stats=stats,
                         recent_analyses=recent_analyses,
                         top_candidates=top_candidates)

@app.route('/api/candidates/search')
def api_search_candidates():
    """API endpoint for candidate search"""
    skills = request.args.getlist('skills')
    min_fit_rating = request.args.get('min_fit_rating', type=float)
    max_risk_score = request.args.get('max_risk_score', type=float)
    page = request.args.get('page', 1, type=int)
    
    results = search_candidates(
        skills=skills if skills else None,
        min_fit_rating=min_fit_rating,
        max_risk_score=max_risk_score,
        page=page,
        per_page=10
    )
    
    return jsonify(results)

@app.route('/jobs/search')
def search_jobs():
    """Search jobs across multiple job boards"""
    query = request.args.get('query', '')
    location = request.args.get('location', 'United States')
    
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400
    
    jobs = search_relevant_jobs(query, location, max_results=15)
    
    return jsonify({
        'query': query,
        'location': location,
        'total_jobs': len(jobs),
        'jobs': jobs
    })

@app.route('/salesforce')
def salesforce_dashboard():
    """Salesforce integration dashboard"""
    sf_integration = SalesforceIntegration()
    
    # Check if Salesforce is configured
    is_configured = all([
        os.environ.get("SALESFORCE_USERNAME"),
        os.environ.get("SALESFORCE_PASSWORD"),
        os.environ.get("SALESFORCE_SECURITY_TOKEN")
    ])
    
    # Get pipeline stats if connected
    pipeline_stats = {}
    if is_configured and sf_integration.sf:
        pipeline_stats = sf_integration.get_recruitment_pipeline_stats()
    
    # Get recent candidates for sync
    recent_candidates = ResumeAnalysis.query.order_by(
        ResumeAnalysis.upload_date.desc()
    ).limit(20).all()
    
    return render_template('salesforce.html',
                         is_configured=is_configured,
                         pipeline_stats=pipeline_stats,
                         recent_candidates=recent_candidates)

@app.route('/salesforce/sync/<int:candidate_id>', methods=['POST'])
def sync_to_salesforce(candidate_id):
    """Sync a single candidate to Salesforce"""
    create_as = request.form.get('create_as', 'lead')
    
    sf_integration = SalesforceIntegration()
    result = sf_integration.sync_candidate_to_salesforce(candidate_id, create_as)
    
    if result['success']:
        flash(f'Successfully synced candidate to Salesforce as {create_as.title()}!', 'success')
    else:
        flash(f'Error syncing to Salesforce: {result["error"]}', 'error')
    
    return safe_redirect(request.referrer, 'salesforce_dashboard')

@app.route('/salesforce/batch_sync', methods=['POST'])
def batch_sync_to_salesforce():
    """Sync multiple candidates to Salesforce"""
    candidate_ids = request.form.getlist('candidate_ids', type=int)
    create_as = request.form.get('create_as', 'lead')
    
    if not candidate_ids:
        flash('No candidates selected for sync', 'warning')
        return redirect(url_for('salesforce_dashboard'))
    
    sf_integration = SalesforceIntegration()
    results = sf_integration.batch_sync_candidates(candidate_ids, create_as)
    
    # Show results
    if results['successful']:
        flash(f'Successfully synced {len(results["successful"])} candidates to Salesforce', 'success')
    if results['duplicates']:
        flash(f'{len(results["duplicates"])} candidates already exist in Salesforce', 'warning')
    if results['failed']:
        flash(f'Failed to sync {len(results["failed"])} candidates', 'error')
    
    return redirect(url_for('salesforce_dashboard'))

@app.route('/salesforce/check_duplicate/<int:candidate_id>')
def check_salesforce_duplicate(candidate_id):
    """Check if a candidate exists in Salesforce"""
    candidate = ResumeAnalysis.query.get_or_404(candidate_id)
    
    if not candidate.email:
        return jsonify({"exists": False, "message": "No email address for candidate"})
    
    sf_integration = SalesforceIntegration()
    duplicate = sf_integration.check_duplicate_candidate(candidate.email)
    
    if duplicate:
        return jsonify({
            "exists": True,
            "type": duplicate['type'],
            "records": duplicate['records']
        })
    else:
        return jsonify({"exists": False})

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('index'))
