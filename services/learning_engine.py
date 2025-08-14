"""
Self-Learning Engine for TradesCompass Pro
Enables Scout to learn from interactions and improve over time
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from openai import OpenAI
from config import Config
from models import db

class LearningEngine:
    """Self-learning system that improves Scout's capabilities over time"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI clients
        self.xai_client = None
        if Config.XAI_API_KEY:
            self.xai_client = OpenAI(
                base_url="https://api.x.ai/v1",
                api_key=Config.XAI_API_KEY
            )
        
        self.openai_client = None
        if Config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Learning state file
        self.learning_state_file = 'instance/scout_learning_state.json'
        self.learning_state = self._load_learning_state()
    
    def _load_learning_state(self) -> Dict[str, Any]:
        """Load the persistent learning state"""
        if os.path.exists(self.learning_state_file):
            try:
                with open(self.learning_state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading learning state: {e}")
        
        # Initialize default state
        return {
            'search_patterns': {},
            'successful_hires': [],
            'skill_associations': {},
            'query_improvements': {},
            'user_preferences': {},
            'database_insights': {},
            'last_optimization': None
        }
    
    def _save_learning_state(self):
        """Save the learning state to disk"""
        try:
            os.makedirs(os.path.dirname(self.learning_state_file), exist_ok=True)
            with open(self.learning_state_file, 'w') as f:
                json.dump(self.learning_state, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error saving learning state: {e}")
    
    def track_search_interaction(self, query: str, results: List[Dict], user_action: str):
        """
        Track how users interact with search results to learn patterns
        
        Args:
            query: The search query
            results: The search results shown
            user_action: What the user did (clicked, ignored, saved, etc.)
        """
        # Update search pattern statistics
        if query not in self.learning_state['search_patterns']:
            self.learning_state['search_patterns'][query] = {
                'count': 0,
                'successful_actions': 0,
                'last_used': None
            }
        
        pattern = self.learning_state['search_patterns'][query]
        pattern['count'] += 1
        pattern['last_used'] = datetime.now().isoformat()
        
        if user_action in ['clicked', 'saved', 'contacted']:
            pattern['successful_actions'] += 1
        
        # Learn from the interaction
        self._analyze_search_effectiveness(query, results, user_action)
        
        self._save_learning_state()
    
    def track_successful_hire(self, candidate_data: Dict, job_requirements: Dict):
        """
        Learn from successful hires to improve future matching
        
        Args:
            candidate_data: Information about the hired candidate
            job_requirements: The job requirements they were hired for
        """
        hire_record = {
            'timestamp': datetime.now().isoformat(),
            'candidate_skills': candidate_data.get('skills', []),
            'candidate_experience': candidate_data.get('experience_years', 0),
            'job_trade': job_requirements.get('trade'),
            'job_skills': job_requirements.get('required_skills', []),
            'location_match': candidate_data.get('location') == job_requirements.get('location')
        }
        
        self.learning_state['successful_hires'].append(hire_record)
        
        # Update skill associations
        self._learn_skill_associations(candidate_data, job_requirements)
        
        # Limit history to last 100 hires
        if len(self.learning_state['successful_hires']) > 100:
            self.learning_state['successful_hires'] = self.learning_state['successful_hires'][-100:]
        
        self._save_learning_state()
    
    def _learn_skill_associations(self, candidate_data: Dict, job_requirements: Dict):
        """Learn which skills often go together"""
        skills = candidate_data.get('skills', [])
        
        for skill in skills:
            if skill not in self.learning_state['skill_associations']:
                self.learning_state['skill_associations'][skill] = {}
            
            for related_skill in skills:
                if skill != related_skill:
                    if related_skill not in self.learning_state['skill_associations'][skill]:
                        self.learning_state['skill_associations'][skill][related_skill] = 0
                    self.learning_state['skill_associations'][skill][related_skill] += 1
    
    def suggest_query_improvements(self, original_query: str) -> Dict[str, Any]:
        """
        Use AI and historical data to suggest query improvements
        
        Args:
            original_query: The user's original search query
        
        Returns:
            Suggestions for improving the query
        """
        # Check if we've seen similar queries before
        similar_queries = self._find_similar_queries(original_query)
        
        # Use AI to analyze and improve
        if self.xai_client or self.openai_client:
            improvements = self._ai_query_analysis(original_query, similar_queries)
        else:
            improvements = self._basic_query_analysis(original_query, similar_queries)
        
        # Cache the improvements
        self.learning_state['query_improvements'][original_query] = improvements
        self._save_learning_state()
        
        return improvements
    
    def _ai_query_analysis(self, query: str, similar_queries: List[str]) -> Dict[str, Any]:
        """Use AI to analyze and improve search queries"""
        
        # Build context from learning state
        successful_patterns = [
            q for q, data in self.learning_state['search_patterns'].items()
            if data.get('successful_actions', 0) > data.get('count', 1) * 0.5
        ]
        
        prompt = f"""Analyze this recruitment search query and suggest improvements based on historical data.

Original Query: {query}

Similar Successful Queries: {json.dumps(similar_queries[:5])}

Successful Search Patterns: {json.dumps(successful_patterns[:10])}

Common Skill Associations: {json.dumps(self.learning_state.get('skill_associations', {}))}

Provide suggestions in JSON format:
{{
    "improved_query": "enhanced version of the query",
    "additional_keywords": ["keyword1", "keyword2"],
    "recommended_filters": {{"experience_level": "mid", "certifications": []}},
    "related_trades": ["trade1", "trade2"],
    "tips": ["tip1", "tip2"]
}}"""

        try:
            client = self.xai_client or self.openai_client
            model = "grok-2-1212" if self.xai_client else "gpt-4o"
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Error in AI query analysis: {e}")
            return self._basic_query_analysis(query, similar_queries)
    
    def _basic_query_analysis(self, query: str, similar_queries: List[str]) -> Dict[str, Any]:
        """Basic query analysis without AI"""
        query_lower = query.lower()
        
        suggestions = {
            "improved_query": query,
            "additional_keywords": [],
            "recommended_filters": {},
            "related_trades": [],
            "tips": []
        }
        
        # Check for common improvements
        if 'electrician' in query_lower and 'licensed' not in query_lower:
            suggestions['additional_keywords'].append('licensed')
            suggestions['tips'].append('Consider specifying license requirements')
        
        if 'hvac' in query_lower and 'epa' not in query_lower:
            suggestions['additional_keywords'].append('EPA certified')
            suggestions['tips'].append('EPA certification is often required for HVAC techs')
        
        return suggestions
    
    def _find_similar_queries(self, query: str) -> List[str]:
        """Find similar queries from history"""
        query_words = set(query.lower().split())
        similar = []
        
        for past_query in self.learning_state['search_patterns'].keys():
            past_words = set(past_query.lower().split())
            overlap = len(query_words & past_words)
            
            if overlap >= len(query_words) * 0.5:
                similar.append(past_query)
        
        return similar
    
    def _analyze_search_effectiveness(self, query: str, results: List[Dict], user_action: str):
        """Analyze why certain searches are more effective"""
        # This would be expanded to track patterns in successful searches
        pass
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        Analyze database usage patterns and suggest optimizations
        
        Returns:
            Database optimization suggestions
        """
        optimizations = {
            'suggested_indexes': [],
            'unused_columns': [],
            'slow_queries': [],
            'data_quality_issues': []
        }
        
        try:
            # Analyze query patterns
            with db.engine.connect() as conn:
                # Check for missing indexes on frequently searched columns
                frequent_searches = self._analyze_frequent_searches()
                
                for column in frequent_searches:
                    # Check if index exists
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM pg_indexes 
                        WHERE tablename = 'resume_analysis' 
                        AND indexdef LIKE %s
                    """), (f'%{column}%',))
                    
                    if result.scalar() == 0:
                        optimizations['suggested_indexes'].append({
                            'table': 'resume_analysis',
                            'column': column,
                            'reason': f'Frequently searched column without index'
                        })
                
                # Analyze data quality
                quality_issues = self._analyze_data_quality()
                optimizations['data_quality_issues'] = quality_issues
                
                # Update learning state
                self.learning_state['database_insights'] = {
                    'last_analysis': datetime.now().isoformat(),
                    'optimizations': optimizations
                }
                self._save_learning_state()
        
        except Exception as e:
            self.logger.error(f"Error optimizing database: {e}")
        
        return optimizations
    
    def _analyze_frequent_searches(self) -> List[str]:
        """Identify frequently searched columns"""
        # Based on search patterns, identify commonly filtered columns
        frequent_columns = []
        
        for query in self.learning_state['search_patterns'].keys():
            query_lower = query.lower()
            
            if 'license' in query_lower:
                frequent_columns.append('licenses')
            if 'certification' in query_lower or 'osha' in query_lower:
                frequent_columns.append('certifications')
            if 'location' in query_lower or any(state in query_lower for state in ['miami', 'florida', 'texas']):
                frequent_columns.append('location')
            if 'experience' in query_lower or 'years' in query_lower:
                frequent_columns.append('years_of_experience')
        
        # Return unique columns
        return list(set(frequent_columns))
    
    def _analyze_data_quality(self) -> List[Dict[str, Any]]:
        """Analyze data quality issues in the database"""
        issues = []
        
        try:
            with db.engine.connect() as conn:
                # Check for missing critical data
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM resume_analysis 
                    WHERE email IS NULL OR email = ''
                """))
                missing_emails = result.scalar()
                
                if missing_emails > 0:
                    issues.append({
                        'type': 'missing_data',
                        'field': 'email',
                        'count': missing_emails,
                        'severity': 'high'
                    })
                
                # Check for outdated resumes
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM resume_analysis 
                    WHERE created_at < NOW() - INTERVAL '6 months'
                """))
                old_resumes = result.scalar()
                
                if old_resumes > 0:
                    issues.append({
                        'type': 'outdated_data',
                        'description': f'{old_resumes} resumes older than 6 months',
                        'severity': 'medium'
                    })
        
        except Exception as e:
            self.logger.error(f"Error analyzing data quality: {e}")
        
        return issues
    
    def generate_insights_report(self) -> str:
        """
        Generate a report of learned insights
        
        Returns:
            Formatted insights report
        """
        report = "📊 **Scout's Learning Insights Report**\n\n"
        
        # Search patterns
        total_searches = sum(p['count'] for p in self.learning_state['search_patterns'].values())
        successful_searches = sum(p['successful_actions'] for p in self.learning_state['search_patterns'].values())
        
        report += f"**Search Analytics:**\n"
        report += f"- Total searches tracked: {total_searches}\n"
        report += f"- Successful interactions: {successful_searches}\n"
        if total_searches > 0:
            report += f"- Success rate: {(successful_searches/total_searches)*100:.1f}%\n\n"
        
        # Top search patterns
        if self.learning_state['search_patterns']:
            top_patterns = sorted(
                self.learning_state['search_patterns'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:5]
            
            report += "**Top Search Patterns:**\n"
            for pattern, data in top_patterns:
                report += f"- \"{pattern}\": {data['count']} searches\n"
            report += "\n"
        
        # Skill associations
        if self.learning_state['skill_associations']:
            report += "**Common Skill Combinations:**\n"
            for skill, related in list(self.learning_state['skill_associations'].items())[:5]:
                top_related = sorted(related.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_related:
                    related_skills = ', '.join([s[0] for s in top_related])
                    report += f"- {skill} often paired with: {related_skills}\n"
            report += "\n"
        
        # Successful hires
        if self.learning_state['successful_hires']:
            report += f"**Hiring Patterns:**\n"
            report += f"- Successful placements tracked: {len(self.learning_state['successful_hires'])}\n"
            
            # Analyze location match importance
            location_matches = sum(
                1 for h in self.learning_state['successful_hires'] 
                if h.get('location_match')
            )
            if self.learning_state['successful_hires']:
                match_rate = (location_matches / len(self.learning_state['successful_hires'])) * 100
                report += f"- Location match rate in hires: {match_rate:.1f}%\n"
        
        # Database insights
        if self.learning_state.get('database_insights'):
            insights = self.learning_state['database_insights']
            if insights.get('optimizations'):
                opt = insights['optimizations']
                if opt.get('suggested_indexes'):
                    report += f"\n**Database Optimization Suggestions:**\n"
                    report += f"- {len(opt['suggested_indexes'])} indexes could improve search speed\n"
                if opt.get('data_quality_issues'):
                    report += f"- {len(opt['data_quality_issues'])} data quality issues detected\n"
        
        report += "\n💡 **Recommendation:** Scout is continuously learning from your interactions to provide better results!"
        
        return report
    
    def self_improve_prompt(self, task: str) -> str:
        """
        Generate an improved prompt based on learned patterns
        
        Args:
            task: The task to generate a prompt for
        
        Returns:
            An optimized prompt
        """
        if not (self.xai_client or self.openai_client):
            return task
        
        learning_context = {
            'successful_patterns': list(self.learning_state['search_patterns'].keys())[:10],
            'skill_associations': self.learning_state.get('skill_associations', {}),
            'user_preferences': self.learning_state.get('user_preferences', {})
        }
        
        prompt = f"""Based on learned patterns, improve this task prompt:

Original Task: {task}

Learning Context:
{json.dumps(learning_context, indent=2)}

Generate an improved, more specific prompt that incorporates learned patterns and preferences.
Return only the improved prompt text."""

        try:
            client = self.xai_client or self.openai_client
            model = "grok-2-1212" if self.xai_client else "gpt-4o"
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.5
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating improved prompt: {e}")
            return task
    
    def learn_from_feedback(self, feedback: str, context: Dict[str, Any]):
        """
        Learn from user feedback to improve future interactions
        
        Args:
            feedback: User's feedback text
            context: Context of what the feedback is about
        """
        # Store feedback with context
        if 'user_feedback' not in self.learning_state:
            self.learning_state['user_feedback'] = []
        
        self.learning_state['user_feedback'].append({
            'timestamp': datetime.now().isoformat(),
            'feedback': feedback,
            'context': context
        })
        
        # Keep only last 50 feedback items
        if len(self.learning_state['user_feedback']) > 50:
            self.learning_state['user_feedback'] = self.learning_state['user_feedback'][-50:]
        
        # Extract preferences from feedback
        self._extract_preferences_from_feedback(feedback)
        
        self._save_learning_state()
    
    def _extract_preferences_from_feedback(self, feedback: str):
        """Extract user preferences from feedback"""
        feedback_lower = feedback.lower()
        
        # Update preferences based on feedback patterns
        if 'too many' in feedback_lower or 'less' in feedback_lower:
            self.learning_state['user_preferences']['result_count'] = 'fewer'
        elif 'more' in feedback_lower or 'not enough' in feedback_lower:
            self.learning_state['user_preferences']['result_count'] = 'more'
        
        if 'detailed' in feedback_lower or 'more info' in feedback_lower:
            self.learning_state['user_preferences']['detail_level'] = 'high'
        elif 'summary' in feedback_lower or 'brief' in feedback_lower:
            self.learning_state['user_preferences']['detail_level'] = 'low'