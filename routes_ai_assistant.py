"""
AI Assistant Routes for TradesCompass Pro
Handles the playful AI assistant interactions
"""

from flask import render_template, request, jsonify, session
from app import app, db
from models import ResumeAnalysis
from services.ai_assistant import RecruitmentAssistant
import logging

# Initialize the assistant
assistant = RecruitmentAssistant()

@app.route('/ai-assistant')
def ai_assistant_page():
    """Main AI Assistant interface"""
    # Get user context for personalized greeting
    user_context = {
        'returning_user': session.get('has_visited', False),
        'last_search': session.get('last_search'),
        'candidates_viewed': session.get('candidates_viewed', 0)
    }
    
    # Mark user as visited
    session['has_visited'] = True
    
    # Get greeting
    greeting = assistant.get_greeting(user_context)
    
    # Get current state for suggestions
    current_state = {
        'resumes_uploaded': ResumeAnalysis.query.count(),
        'searches_performed': session.get('searches_performed', 0),
        'filters_applied': session.get('filters_applied', False),
        'candidates_reviewed': session.get('candidates_viewed', 0)
    }
    
    # Get suggestions
    suggestions = assistant.suggest_next_action(current_state)
    
    # Get quick stats
    stats = {
        'total_candidates': ResumeAnalysis.query.count(),
        'active_searches': session.get('active_searches', 0),
        'recent_uploads': ResumeAnalysis.query.filter(
            ResumeAnalysis.upload_date >= db.func.current_date()
        ).count()
    }
    
    return render_template('ai_assistant.html',
                         greeting=greeting,
                         suggestions=suggestions,
                         stats=stats,
                         assistant_name=assistant.personality['name'])

@app.route('/api/ai-assistant/chat', methods=['POST'])
def ai_assistant_chat():
    """Handle chat messages with the AI assistant"""
    data = request.json
    user_message = data.get('message', '')
    context = data.get('context', {})
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Generate response
    response = assistant.get_conversation_response(user_message, context)
    
    # If the message contains a search query, analyze intent
    intent_analysis = None
    if any(word in user_message.lower() for word in ['find', 'search', 'looking for', 'need']):
        intent_analysis = assistant.analyze_search_intent(user_message)
    
    return jsonify({
        'response': response,
        'intent': intent_analysis,
        'suggestions': assistant.suggest_next_action(context) if context else None
    })

@app.route('/api/ai-assistant/analyze-search', methods=['POST'])
def analyze_search():
    """Analyze a search query and provide guidance"""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    analysis = assistant.analyze_search_intent(query)
    
    # Update session
    session['last_search'] = query
    session['searches_performed'] = session.get('searches_performed', 0) + 1
    
    return jsonify(analysis)

@app.route('/api/ai-assistant/candidate-summary/<int:candidate_id>')
def get_candidate_summary(candidate_id):
    """Get an AI-generated summary of a candidate"""
    candidate = ResumeAnalysis.query.get_or_404(candidate_id)
    
    # Convert to dict for assistant
    candidate_dict = {
        'first_name': candidate.first_name,
        'last_name': candidate.last_name,
        'job_title': candidate.job_title,
        'experience_years': candidate.years_of_experience,
        'skills': candidate.skills.split(',') if candidate.skills else [],
        'certifications': [candidate.licenses, candidate.certifications] if candidate.licenses or candidate.certifications else [],
        'location': candidate.location
    }
    
    summary = assistant.generate_candidate_summary(candidate_dict)
    
    # Update session
    session['candidates_viewed'] = session.get('candidates_viewed', 0) + 1
    
    return jsonify({'summary': summary})

@app.route('/api/ai-assistant/matching-tips', methods=['POST'])
def get_matching_tips():
    """Get tips for better candidate matching"""
    data = request.json
    job_requirements = data.get('requirements', '')
    candidate_count = data.get('candidate_count', 0)
    
    tips = assistant.provide_matching_tips(job_requirements, candidate_count)
    
    return jsonify({'tips': tips})

@app.route('/api/ai-assistant/interview-questions', methods=['POST'])
def get_interview_questions():
    """Get suggested interview questions for a trade"""
    data = request.json
    trade = data.get('trade', 'general')
    experience_level = data.get('experience_level', 'mid')
    
    questions = assistant.create_interview_questions(trade, experience_level)
    
    return jsonify({'questions': questions})

@app.route('/api/ai-assistant/quick-action', methods=['POST'])
def handle_quick_action():
    """Handle quick action buttons from the assistant"""
    data = request.json
    action = data.get('action')
    
    responses = {
        'upload_help': "To upload resumes: 1) Click 'Add Candidate' 2) Drag & drop files or click to browse 3) Wait for AI analysis. You can upload multiple files at once!",
        'search_help': "Search tips: Use specific terms like 'HVAC OSHA 30' or 'licensed electrician Florida'. The more specific, the better the matches!",
        'filter_help': "Filter options: Use the sliders for fit/risk scores, add location preferences, and specify required certifications for best results.",
        'contact_help': "Before contacting: Review their experience, check certifications are current, and prepare relevant questions about their specific skills."
    }
    
    response = responses.get(action, "I'm here to help! What would you like to know?")
    
    return jsonify({'response': response})

# Register the routes
logging.info("AI Assistant routes registered")