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
    """Combined candidate search - both internal database and external sourcing"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_type = request.args.get('search_type', 'internal')  # internal or external
    
    # Get search filters from query parameters
    skills_str = request.args.get('skills', '').strip()
    skills = [s.strip() for s in skills_str.split(',') if s.strip()] if skills_str else []
    
    min_fit_rating = request.args.get('min_fit_rating', type=float)
    max_risk_score = request.args.get('max_risk_score', type=float)
    min_reward_score = request.args.get('min_reward_score', type=float)
    location = request.args.get('location', '').strip() or None
    status = request.args.get('status', '').strip() or None
    sort_by = request.args.get('sort_by', 'date_desc')
    
    keywords_str = request.args.get('keywords', '').strip()
    experience_keywords = [k.strip() for k in keywords_str.split(',') if k.strip()] if keywords_str else []
    
    # Query string for external search
    query_str = request.args.get('query', '').strip()
    
    if search_type == 'external' and query_str:
        # Search external candidate sources
        from services.candidate_sourcing import search_external_candidates
        
        external_results = search_external_candidates(
            query=query_str,
            location=location,
            skills=skills if skills else None,
            limit=per_page
        )
        
        search_results = {
            'candidates': external_results.get('candidates', []),
            'total': external_results.get('total_found', 0),
            'current_page': 1,
            'pages': 1,
            'per_page': per_page,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None,
            'sources_searched': external_results.get('sources_searched', []),
            'search_type': 'external'
        }
        
        stats = {'total_candidates': len(external_results.get('candidates', []))}
        
    else:
        # Search internal candidate database
        search_results = search_candidates(
            skills=skills if skills else None,
            min_fit_rating=min_fit_rating,
            max_risk_score=max_risk_score,
            min_reward_score=min_reward_score,
            location=location,
            status=status,
            sort_by=sort_by,
            experience_keywords=experience_keywords if experience_keywords else None,
            page=page,
            per_page=per_page
        )
        search_results['search_type'] = 'internal'
        
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
                             'keywords': experience_keywords,
                             'status': status,
                             'sort_by': sort_by,
                             'search_type': search_type,
                             'query': query_str
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

# ============= TalentCompass AI Enhanced Features =============

@app.route('/analytics')
def analytics_dashboard():
    """Analytics dashboard with comprehensive metrics"""
    from services.analytics_dashboard import AnalyticsDashboardService
    
    analytics = AnalyticsDashboardService()
    
    metrics = {
        'overview': analytics.get_overview_metrics(),
        'pipeline': analytics.get_candidate_pipeline_metrics(),
        'sources': analytics.get_source_effectiveness(),
        'skills': analytics.get_skill_demand_analysis(),
        'diversity': analytics.get_diversity_metrics(),
        'time_to_fill': analytics.get_time_to_fill_metrics(),
        'recruiter_performance': analytics.get_recruiter_performance(),
        'referrals': analytics.get_referral_analytics()
    }
    
    return render_template('analytics.html', metrics=metrics)

@app.route('/tasks')
def tasks_dashboard():
    """Task management dashboard"""
    from services.task_management import TaskManagementService
    
    task_service = TaskManagementService()
    assigned_to = request.args.get('assigned_to')
    
    tasks = {
        'upcoming': task_service.get_upcoming_tasks(assigned_to),
        'overdue': task_service.get_overdue_tasks(assigned_to),
        'statistics': task_service.get_task_statistics(assigned_to)
    }
    
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/create', methods=['POST'])
def create_task():
    """Create a new task"""
    from services.task_management import TaskManagementService
    from datetime import datetime
    
    task_service = TaskManagementService()
    
    try:
        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d') if request.form.get('due_date') else None
        
        task = task_service.create_task(
            candidate_id=int(request.form['candidate_id']),
            task_type=request.form['task_type'],
            title=request.form['title'],
            description=request.form.get('description'),
            due_date=due_date,
            assigned_to=request.form.get('assigned_to'),
            priority=request.form.get('priority', 'medium')
        )
        
        flash('Task created successfully', 'success')
        return redirect(url_for('tasks_dashboard'))
        
    except Exception as e:
        logging.error(f"Error creating task: {e}")
        flash('Error creating task', 'error')
        return redirect(url_for('tasks_dashboard'))

@app.route('/ai-recommendations/<int:candidate_id>')
def ai_recommendations(candidate_id):
    """Get AI recommendations for a candidate"""
    from services.ai_recommendations import AIRecommendationService
    
    ai_service = AIRecommendationService()
    
    # Get similar candidates
    similar = ai_service.find_similar_candidates(candidate_id, limit=5)
    
    # Generate insights
    insights = ai_service.generate_candidate_insights(
        candidate_id,
        job_context=request.args.get('job_context')
    )
    
    candidate = ResumeAnalysis.query.get_or_404(candidate_id)
    
    return render_template(
        'ai_recommendations.html',
        candidate=candidate,
        similar_candidates=similar,
        insights=insights
    )

@app.route('/smart-search')
def smart_search():
    """Enhanced search with fuzzy matching and AI"""
    from services.fuzzy_search import FuzzySearchService
    
    # Always get total candidate count for display
    total_candidates = ResumeAnalysis.query.count()
    
    search_service = FuzzySearchService()
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'fuzzy')
    
    results = []
    if query:
        try:
            if search_type == 'fuzzy':
                results = search_service.fuzzy_search(query, threshold=0.3)  # Lower threshold for better matches
            elif search_type == 'boolean':
                results = search_service.boolean_search(query)
            elif search_type == 'semantic':
                results = search_service.semantic_search(query, limit=20)
            
            # Log search for debugging
            logging.info(f"Smart search: query='{query}', type={search_type}, found={len(results)} results")
        except Exception as e:
            logging.error(f"Smart search error: {e}")
            flash(f'Search error: {str(e)}', 'error')
    
    return render_template('smart_search.html', 
                         results=results, 
                         query=query, 
                         search_type=search_type,
                         total_candidates=total_candidates)

# ============= Referral Management Routes =============

@app.route('/referrals')
def referrals_dashboard():
    """Referral management dashboard"""
    from services.referral_management import ReferralManagementService
    
    referral_service = ReferralManagementService()
    
    data = {
        'statistics': referral_service.get_referral_statistics(),
        'top_referrers': referral_service.get_top_referrers(limit=10),
        'pending_referrals': referral_service.get_pending_referrals(),
        'department_performance': referral_service.get_department_performance()
    }
    
    return render_template('referrals.html', data=data)

@app.route('/referrals/create', methods=['GET', 'POST'])
def create_referral():
    """Create a new referral"""
    from services.referral_management import ReferralManagementService
    
    if request.method == 'POST':
        referral_service = ReferralManagementService()
        
        try:
            referral = referral_service.create_referral(
                candidate_id=int(request.form['candidate_id']),
                referrer_name=request.form['referrer_name'],
                referrer_email=request.form['referrer_email'],
                referrer_department=request.form.get('referrer_department'),
                relationship=request.form.get('relationship'),
                notes=request.form.get('notes')
            )
            
            flash('Referral created successfully!', 'success')
            return redirect(url_for('referrals_dashboard'))
            
        except Exception as e:
            logging.error(f"Error creating referral: {e}")
            flash('Error creating referral', 'error')
            return redirect(url_for('referrals_dashboard'))
    
    # GET request - show form
    candidates = ResumeAnalysis.query.filter(
        ResumeAnalysis.status != 'hired'
    ).order_by(ResumeAnalysis.upload_date.desc()).all()
    
    return render_template('create_referral.html', candidates=candidates)

@app.route('/referrals/<int:referral_id>/update', methods=['POST'])
def update_referral_status(referral_id):
    """Update referral status"""
    from services.referral_management import ReferralManagementService
    
    referral_service = ReferralManagementService()
    new_status = request.form.get('status')
    reward_points = request.form.get('reward_points', type=int)
    
    if referral_service.update_referral_status(referral_id, new_status, reward_points):
        flash('Referral status updated successfully', 'success')
    else:
        flash('Error updating referral status', 'error')
    
    return redirect(url_for('referrals_dashboard'))

@app.route('/referrals/<int:referral_id>/bonus')
def calculate_referral_bonus(referral_id):
    """Calculate referral bonus"""
    from services.referral_management import ReferralManagementService
    
    referral_service = ReferralManagementService()
    bonus_info = referral_service.calculate_referral_bonus(referral_id)
    
    return jsonify(bonus_info)

# ============= Talent Pool Management Routes =============

@app.route('/talent-pools')
def talent_pools():
    """Talent pool management dashboard"""
    from services.talent_pools import TalentPoolService
    
    pool_service = TalentPoolService()
    pools = pool_service.get_active_pools()
    
    # Get statistics for each pool
    pool_data = []
    for pool in pools:
        stats = pool_service.get_pool_statistics(pool.id)
        pool_data.append({
            'pool': pool,
            'stats': stats
        })
    
    return render_template('talent_pools.html', pool_data=pool_data)

@app.route('/talent-pools/create', methods=['POST'])
def create_talent_pool():
    """Create a new talent pool"""
    from services.talent_pools import TalentPoolService
    
    pool_service = TalentPoolService()
    
    try:
        # Parse criteria if provided
        criteria = {}
        if request.form.get('min_rating'):
            criteria['min_rating'] = float(request.form['min_rating'])
        if request.form.get('skills'):
            criteria['skills'] = [s.strip() for s in request.form['skills'].split(',')]
        if request.form.get('location'):
            criteria['location'] = request.form['location']
        if request.form.get('status'):
            criteria['status'] = request.form['status']
        
        pool = pool_service.create_pool(
            pool_name=request.form['pool_name'],
            pool_type=request.form['pool_type'],
            description=request.form.get('description'),
            criteria=criteria if criteria else None,
            created_by=request.form.get('created_by', 'System')
        )
        
        # Auto-populate if requested
        if request.form.get('auto_populate') == 'true' and criteria:
            added = pool_service.auto_populate_pool(pool.id)
            flash(f'Talent pool created and populated with {added} candidates', 'success')
        else:
            flash('Talent pool created successfully', 'success')
        
        return redirect(url_for('talent_pools'))
        
    except Exception as e:
        logging.error(f"Error creating talent pool: {e}")
        flash('Error creating talent pool', 'error')
        return redirect(url_for('talent_pools'))

@app.route('/talent-pools/<int:pool_id>/add-candidate', methods=['POST'])
def add_to_talent_pool(pool_id):
    """Add a candidate to a talent pool"""
    from services.talent_pools import TalentPoolService
    
    pool_service = TalentPoolService()
    candidate_id = request.form.get('candidate_id', type=int)
    
    if pool_service.add_candidate_to_pool(pool_id, candidate_id):
        flash('Candidate added to talent pool', 'success')
    else:
        flash('Candidate already in pool or error occurred', 'warning')
    
    return redirect(request.referrer or url_for('talent_pools'))

@app.route('/talent-pools/<int:pool_id>/remove-candidate/<int:candidate_id>', methods=['POST'])
def remove_from_talent_pool(pool_id, candidate_id):
    """Remove a candidate from a talent pool"""
    from services.talent_pools import TalentPoolService
    
    pool_service = TalentPoolService()
    
    if pool_service.remove_candidate_from_pool(pool_id, candidate_id):
        flash('Candidate removed from talent pool', 'success')
    else:
        flash('Error removing candidate', 'error')
    
    return redirect(request.referrer or url_for('talent_pools'))

@app.route('/talent-pools/<int:pool_id>/view')
def view_talent_pool(pool_id):
    """View detailed talent pool information"""
    from services.talent_pools import TalentPoolService
    from models import TalentPool
    
    pool_service = TalentPoolService()
    pool = TalentPool.query.get_or_404(pool_id)
    stats = pool_service.get_pool_statistics(pool_id)
    members = pool_service.get_pool_members(pool_id)
    
    return render_template('view_talent_pool.html', pool=pool, stats=stats, members=members)

# ============= Test Data Route =============

@app.route('/add-test-candidates')
def add_test_candidates():
    """Add sample candidates for testing Smart Search"""
    from datetime import datetime
    import json
    
    try:
        # Check if test candidates already exist
        test_email = "john.smith@example.com"
        existing = ResumeAnalysis.query.filter_by(email=test_email).first()
        if existing:
            flash('Test candidates already exist in database', 'info')
            return redirect(url_for('smart_search'))
        
        # Create sample candidates
        test_candidates = [
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'email': 'john.smith@example.com',
                'phone': '555-0101',
                'location': 'Tampa, FL',
                'resume_text': 'Senior Python Developer with 8 years experience in machine learning and data science.',
                'candidate_strengths': json.dumps(['Python', 'Machine Learning', 'Data Science', 'AWS']),
                'overall_fit_rating': 8.5,
                'skills': ['Python', 'Machine Learning', 'TensorFlow', 'AWS', 'Docker']
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@example.com',
                'phone': '555-0102',
                'location': 'San Francisco, CA',
                'resume_text': 'Full-stack JavaScript developer specializing in React and Node.js.',
                'candidate_strengths': json.dumps(['JavaScript', 'React', 'Node.js', 'MongoDB']),
                'overall_fit_rating': 7.8,
                'skills': ['JavaScript', 'React', 'Node.js', 'MongoDB', 'Express']
            },
            {
                'first_name': 'Michael',
                'last_name': 'Chen',
                'email': 'michael.chen@example.com',
                'phone': '555-0103',
                'location': 'Austin, TX',
                'resume_text': 'DevOps Engineer with expertise in Kubernetes and cloud infrastructure.',
                'candidate_strengths': json.dumps(['Kubernetes', 'AWS', 'Terraform', 'CI/CD']),
                'overall_fit_rating': 8.2,
                'skills': ['Kubernetes', 'AWS', 'Docker', 'Terraform', 'Jenkins']
            },
            {
                'first_name': 'Emily',
                'last_name': 'Davis',
                'email': 'emily.davis@example.com',
                'phone': '555-0104',
                'location': 'Tampa, FL',
                'resume_text': 'Data Analyst with strong Python and SQL skills, experienced in business intelligence.',
                'candidate_strengths': json.dumps(['Python', 'SQL', 'Tableau', 'Data Analysis']),
                'overall_fit_rating': 7.5,
                'skills': ['Python', 'SQL', 'Tableau', 'Excel', 'Power BI']
            },
            {
                'first_name': 'Robert',
                'last_name': 'Wilson',
                'email': 'robert.wilson@example.com',
                'phone': '555-0105',
                'location': 'New York, NY',
                'resume_text': 'Java Backend Developer with microservices and Spring Boot experience.',
                'candidate_strengths': json.dumps(['Java', 'Spring Boot', 'Microservices', 'SQL']),
                'overall_fit_rating': 7.9,
                'skills': ['Java', 'Spring Boot', 'MySQL', 'Redis', 'Kafka']
            }
        ]
        
        # Add candidates to database
        for candidate_data in test_candidates:
            # Create candidate
            skills = candidate_data.pop('skills', [])
            candidate = ResumeAnalysis(
                filename=f"test_resume_{candidate_data['email']}.pdf",
                upload_date=datetime.utcnow(),
                source='test_data',
                status='active',
                **candidate_data
            )
            db.session.add(candidate)
            db.session.flush()  # Get the ID
            
            # Add skills
            for skill_name in skills:
                skill = CandidateSkill(
                    candidate_id=candidate.id,
                    skill_name=skill_name,
                    skill_level='intermediate'
                )
                db.session.add(skill)
        
        db.session.commit()
        flash(f'Successfully added {len(test_candidates)} test candidates to the database', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding test candidates: {e}")
        flash(f'Error adding test candidates: {str(e)}', 'error')
    
    return redirect(url_for('smart_search'))
