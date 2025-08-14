"""
API Routes for Scout's Self-Learning Capabilities
"""

from flask import jsonify, request, session
from app import app, db
from services.learning_engine import LearningEngine
from models_learning import (
    SearchInteraction, SuccessfulPlacement, QueryImprovement,
    UserPreference, LearningFeedback, DatabaseOptimization
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
learning_engine = LearningEngine()

@app.route('/api/learning/track-search', methods=['POST'])
def track_search_interaction():
    """Track user interaction with search results"""
    try:
        data = request.json
        query = data.get('query')
        action = data.get('action')  # clicked, saved, contacted, ignored
        result_id = data.get('result_id')
        result_rank = data.get('result_rank')
        results = data.get('results', [])
        
        # Track in learning engine
        learning_engine.track_search_interaction(query, results, action)
        
        # Save to database
        interaction = SearchInteraction(
            query=query,
            action=action,
            result_id=result_id,
            result_rank=result_rank,
            session_id=session.get('session_id', 'anonymous'),
            filters_used=data.get('filters'),
            total_results=len(results)
        )
        db.session.add(interaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Interaction tracked successfully'
        })
        
    except Exception as e:
        logger.error(f"Error tracking search interaction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/track-placement', methods=['POST'])
def track_successful_placement():
    """Track a successful candidate placement"""
    try:
        data = request.json
        
        # Track in learning engine
        learning_engine.track_successful_hire(
            data.get('candidate_data'),
            data.get('job_requirements')
        )
        
        # Save to database
        placement = SuccessfulPlacement(
            candidate_id=data.get('candidate_id'),
            job_title=data.get('job_title'),
            job_trade=data.get('job_trade'),
            skills_matched=data.get('skills_matched'),
            certifications_matched=data.get('certifications_matched'),
            experience_years_required=data.get('experience_years'),
            location_matched=data.get('location_matched', False),
            starting_salary=data.get('starting_salary'),
            placement_type=data.get('placement_type', 'permanent'),
            time_to_hire=data.get('time_to_hire'),
            candidate_source=data.get('candidate_source')
        )
        db.session.add(placement)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Placement tracked successfully',
            'insights': 'Scout is learning from this successful placement!'
        })
        
    except Exception as e:
        logger.error(f"Error tracking placement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/improve-query', methods=['POST'])
def improve_search_query():
    """Get AI-powered query improvements"""
    try:
        original_query = request.json.get('query')
        
        # Get improvements from learning engine
        improvements = learning_engine.suggest_query_improvements(original_query)
        
        # Save improvement to database for tracking
        if improvements.get('improved_query') != original_query:
            query_improvement = QueryImprovement(
                original_query=original_query,
                improved_query=improvements.get('improved_query'),
                keywords_added=improvements.get('additional_keywords'),
                filters_suggested=improvements.get('recommended_filters')
            )
            db.session.add(query_improvement)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'original_query': original_query,
            'improvements': improvements
        })
        
    except Exception as e:
        logger.error(f"Error improving query: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/insights', methods=['GET'])
def get_learning_insights():
    """Get Scout's learning insights report"""
    try:
        # Generate insights report
        report = learning_engine.generate_insights_report()
        
        # Get recent learning metrics from database
        recent_interactions = SearchInteraction.query.filter(
            SearchInteraction.timestamp >= datetime.now().replace(day=1)
        ).count()
        
        successful_placements = SuccessfulPlacement.query.count()
        
        # Get top improved queries
        top_improvements = QueryImprovement.query.order_by(
            QueryImprovement.success_rate.desc()
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'report': report,
            'metrics': {
                'recent_interactions': recent_interactions,
                'total_placements': successful_placements,
                'top_improvements': [
                    {
                        'original': imp.original_query,
                        'improved': imp.improved_query,
                        'success_rate': imp.success_rate
                    }
                    for imp in top_improvements
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/optimize-database', methods=['POST'])
def optimize_database():
    """Get database optimization suggestions"""
    try:
        # Get optimization suggestions
        optimizations = learning_engine.optimize_database()
        
        # Save suggestions to database
        for suggestion in optimizations.get('suggested_indexes', []):
            db_opt = DatabaseOptimization(
                optimization_type='index',
                table_name=suggestion.get('table'),
                column_name=suggestion.get('column'),
                suggestion=f"CREATE INDEX ON {suggestion.get('table')}({suggestion.get('column')})",
                reason=suggestion.get('reason'),
                expected_improvement='Faster search queries'
            )
            db.session.add(db_opt)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'optimizations': optimizations,
            'message': 'Database analysis complete'
        })
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback for Scout to learn from"""
    try:
        data = request.json
        feedback_text = data.get('feedback')
        feedback_type = data.get('type', 'general')
        context = data.get('context', {})
        
        # Let Scout learn from the feedback
        learning_engine.learn_from_feedback(feedback_text, context)
        
        # Analyze sentiment
        sentiment = 'neutral'
        if any(word in feedback_text.lower() for word in ['great', 'excellent', 'love', 'perfect']):
            sentiment = 'positive'
        elif any(word in feedback_text.lower() for word in ['bad', 'poor', 'hate', 'terrible']):
            sentiment = 'negative'
        
        # Save to database
        feedback = LearningFeedback(
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            context_data=context,
            session_id=session.get('session_id', 'anonymous'),
            sentiment=sentiment,
            actionable=True if sentiment != 'neutral' else False
        )
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you! Scout is learning from your feedback.',
            'sentiment': sentiment
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/self-improve', methods=['POST'])
def self_improve_task():
    """Have Scout improve its own task performance"""
    try:
        task = request.json.get('task')
        
        # Get improved version from Scout
        improved_task = learning_engine.self_improve_prompt(task)
        
        return jsonify({
            'success': True,
            'original_task': task,
            'improved_task': improved_task,
            'explanation': 'Scout has optimized this task based on learned patterns'
        })
        
    except Exception as e:
        logger.error(f"Error self-improving task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/preferences', methods=['GET'])
def get_user_preferences():
    """Get learned user preferences"""
    try:
        session_id = session.get('session_id', 'anonymous')
        
        # Get preferences from database
        preferences = UserPreference.query.filter_by(
            session_id=session_id
        ).order_by(UserPreference.confidence.desc()).all()
        
        pref_dict = {}
        for pref in preferences:
            if pref.preference_type not in pref_dict:
                pref_dict[pref.preference_type] = pref.preference_value
        
        return jsonify({
            'success': True,
            'preferences': pref_dict,
            'learning_active': True
        })
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Register learning routes
logger.info("Learning routes registered")