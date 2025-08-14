"""
AI Assistant Service for TradesCompass Pro
Provides a friendly, conversational AI guide for recruiters
"""

import json
import logging
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import Config
from openai import OpenAI

class RecruitmentAssistant:
    """Friendly AI assistant to guide recruiters through the hiring process"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
        
        # Assistant personality traits
        self.personality = {
            'name': 'Scout',
            'role': 'Your Recruitment Assistant',
            'traits': ['friendly', 'helpful', 'encouraging', 'professional yet casual'],
            'emoji_style': 'occasional',  # Use emojis sparingly for friendliness
        }
        
        # Conversation starters and prompts
        self.greetings = [
            "Hey there! Ready to find some amazing candidates? 🎯",
            "Hi! Let's discover your next great hire together!",
            "Hello! I'm Scout, here to help you find the perfect match.",
            "Welcome back! Ready to review some talented candidates?",
            "Hi there! What kind of talent are we looking for today?"
        ]
        
        self.encouragements = [
            "Great choice! Let me help you with that.",
            "Excellent! I've got some ideas for you.",
            "Perfect! Let's dive in.",
            "Awesome! Here's what I found.",
            "Good thinking! Let me show you the options."
        ]
        
        self.tips = [
            "💡 Tip: Try searching for specific certifications like 'OSHA 30' for safety-conscious candidates.",
            "💡 Pro tip: Candidates with both residential and commercial experience are often more versatile.",
            "💡 Quick tip: Check the 'Years of Experience' filter to find seasoned professionals.",
            "💡 Reminder: Don't forget to review the safety certifications section!",
            "💡 Insight: Candidates willing to travel often have broader project experience."
        ]
    
    def get_greeting(self, user_context: Dict = None) -> str:
        """Generate a contextual greeting"""
        current_hour = datetime.now().hour
        
        if current_hour < 12:
            time_greeting = "Good morning!"
        elif current_hour < 17:
            time_greeting = "Good afternoon!"
        else:
            time_greeting = "Good evening!"
        
        if user_context and user_context.get('returning_user'):
            return f"{time_greeting} Welcome back! {random.choice(self.greetings)}"
        else:
            return f"{time_greeting} {random.choice(self.greetings)}"
    
    def suggest_next_action(self, current_state: Dict) -> Dict[str, Any]:
        """Suggest the next best action based on current recruiting state"""
        suggestions = []
        
        # Check what the recruiter has done so far
        has_uploaded = current_state.get('resumes_uploaded', 0) > 0
        has_searched = current_state.get('searches_performed', 0) > 0
        has_filtered = current_state.get('filters_applied', False)
        candidates_reviewed = current_state.get('candidates_reviewed', 0)
        
        if not has_uploaded:
            suggestions.append({
                'action': 'upload_resume',
                'message': "Let's start by uploading some resumes! You can drag and drop multiple files at once.",
                'button_text': 'Upload Resumes',
                'link': '/',
                'priority': 1
            })
        
        if not has_searched and has_uploaded:
            suggestions.append({
                'action': 'search_candidates',
                'message': "Now let's search your candidate database. What skills are you looking for?",
                'button_text': 'Search Candidates',
                'link': '/candidates',
                'priority': 1
            })
        
        if has_searched and not has_filtered:
            suggestions.append({
                'action': 'apply_filters',
                'message': "Try narrowing down your search with filters like location, certifications, or experience level.",
                'button_text': 'Refine Search',
                'link': '/candidates',
                'priority': 2
            })
        
        if candidates_reviewed < 5 and has_uploaded:
            suggestions.append({
                'action': 'review_more',
                'message': f"You've reviewed {candidates_reviewed} candidates. Let's look at a few more to find the perfect match!",
                'button_text': 'View More Candidates',
                'link': '/candidates',
                'priority': 3
            })
        
        # Add a random tip
        suggestions.append({
            'action': 'tip',
            'message': random.choice(self.tips),
            'button_text': None,
            'link': None,
            'priority': 4
        })
        
        # Sort by priority and return top suggestions
        suggestions.sort(key=lambda x: x['priority'])
        return suggestions[:2]
    
    def analyze_search_intent(self, query: str) -> Dict[str, Any]:
        """Analyze what the recruiter is looking for and provide guidance"""
        query_lower = query.lower()
        
        intent = {
            'trade': None,
            'skills': [],
            'certifications': [],
            'experience_level': None,
            'suggestions': []
        }
        
        # Detect trade type
        trades = {
            'electrician': ['electrical', 'electrician', 'journeyman electrician', 'master electrician'],
            'hvac': ['hvac', 'heating', 'cooling', 'air conditioning', 'refrigeration'],
            'plumber': ['plumber', 'plumbing', 'pipefitter', 'pipe'],
            'carpenter': ['carpenter', 'carpentry', 'framing', 'finishing'],
            'window': ['window', 'door', 'glazier', 'installation'],
            'general': ['construction', 'laborer', 'general contractor']
        }
        
        for trade, keywords in trades.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['trade'] = trade
                break
        
        # Detect certifications
        certifications = {
            'OSHA': ['osha', 'osha 10', 'osha 30', 'osha 40'],
            'EPA': ['epa', 'epa certified', '608', '609'],
            'State License': ['licensed', 'license', 'journeyman', 'master'],
            'DOT': ['dot', 'cdl', 'commercial driver']
        }
        
        for cert, keywords in certifications.items():
            if any(keyword in query_lower for keyword in keywords):
                intent['certifications'].append(cert)
        
        # Detect experience level
        if any(word in query_lower for word in ['senior', 'experienced', 'veteran', '10+ years', '15+ years']):
            intent['experience_level'] = 'senior'
        elif any(word in query_lower for word in ['junior', 'entry', 'apprentice', 'helper']):
            intent['experience_level'] = 'junior'
        elif any(word in query_lower for word in ['mid-level', 'journeyman', '5+ years']):
            intent['experience_level'] = 'mid'
        
        # Generate suggestions based on intent
        if intent['trade']:
            intent['suggestions'].append(f"I'll focus on {intent['trade']} professionals for you.")
        
        if intent['certifications']:
            intent['suggestions'].append(f"Looking for candidates with {', '.join(intent['certifications'])} - smart choice for compliance!")
        
        if intent['experience_level']:
            level_text = {
                'senior': 'seasoned professionals with 10+ years',
                'mid': 'skilled journeymen with 5-10 years',
                'junior': 'eager apprentices and helpers'
            }
            intent['suggestions'].append(f"Searching for {level_text.get(intent['experience_level'], 'experienced')} of experience.")
        
        if not intent['trade'] and not intent['certifications']:
            intent['suggestions'].append("Try being more specific - mention the trade, required certifications, or experience level you need.")
        
        return intent
    
    def generate_candidate_summary(self, candidate: Dict) -> str:
        """Generate a friendly, conversational summary of a candidate"""
        if not self.client:
            return self._generate_simple_summary(candidate)
        
        try:
            prompt = f"""You are Scout, a friendly recruitment assistant. Create a brief, conversational summary of this candidate 
            that highlights their key strengths and fit for trades work. Be encouraging and professional.
            
            Candidate Info:
            - Name: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
            - Trade: {candidate.get('job_title', 'Not specified')}
            - Experience: {candidate.get('experience_years', 'Unknown')} years
            - Skills: {', '.join(candidate.get('skills', [])[:5])}
            - Certifications: {', '.join(candidate.get('certifications', []))}
            - Location: {candidate.get('location', 'Not specified')}
            
            Keep it under 3 sentences and highlight what makes them special."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are Scout, a friendly and encouraging recruitment assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating AI summary: {e}")
            return self._generate_simple_summary(candidate)
    
    def _generate_simple_summary(self, candidate: Dict) -> str:
        """Fallback summary generation without AI"""
        name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() or "This candidate"
        trade = candidate.get('job_title', 'trades professional')
        years = candidate.get('experience_years', 0)
        
        if years > 10:
            exp_text = f"veteran {trade} with {years}+ years"
        elif years > 5:
            exp_text = f"experienced {trade} with {years} years"
        else:
            exp_text = f"{trade} with {years} years"
        
        certs = candidate.get('certifications', [])
        if certs:
            cert_text = f" and holds {', '.join(certs[:2])} certification"
        else:
            cert_text = ""
        
        return f"{name} is an {exp_text} of experience{cert_text}. Worth considering for your team!"
    
    def provide_matching_tips(self, job_requirements: str, candidate_pool_size: int) -> List[str]:
        """Provide tips for better candidate matching"""
        tips = []
        
        if candidate_pool_size == 0:
            tips.append("No matches yet? Try broadening your search criteria or checking for typos.")
            tips.append("Consider searching for related skills - for example, 'electrical' instead of 'electrician'.")
        elif candidate_pool_size < 5:
            tips.append(f"Only {candidate_pool_size} matches - you might want to relax some requirements.")
            tips.append("Consider candidates from nearby locations who might be willing to relocate.")
        elif candidate_pool_size > 50:
            tips.append(f"Wow, {candidate_pool_size} candidates! Use filters to narrow down to the best fits.")
            tips.append("Start with the highest-rated candidates or those with the most relevant certifications.")
        
        # Add job-specific tips
        if 'urgent' in job_requirements.lower() or 'asap' in job_requirements.lower():
            tips.append("For urgent hires, prioritize candidates who are immediately available.")
        
        if 'license' in job_requirements.lower():
            tips.append("Don't forget to verify that licenses are current and valid in your state.")
        
        return tips
    
    def create_interview_questions(self, trade: str, experience_level: str) -> List[str]:
        """Generate relevant interview questions for trades professionals"""
        base_questions = [
            "Tell me about your most challenging project and how you handled it.",
            "How do you ensure safety compliance on job sites?",
            "Describe a time when you had to work with a difficult team member.",
            "What's your approach to meeting tight deadlines?",
            "How do you stay updated with new techniques and regulations in your trade?"
        ]
        
        trade_specific = {
            'electrician': [
                "How do you troubleshoot electrical issues?",
                "What's your experience with both residential and commercial wiring?",
                "How familiar are you with the current NEC code?"
            ],
            'hvac': [
                "What's your diagnostic process for HVAC systems?",
                "How do you handle refrigerant regulations and EPA requirements?",
                "What's your experience with different types of heating/cooling systems?"
            ],
            'plumber': [
                "How do you approach leak detection and repair?",
                "What's your experience with different pipe materials?",
                "How do you ensure code compliance in your installations?"
            ],
            'carpenter': [
                "What's your experience with different framing techniques?",
                "How do you ensure precision in your measurements and cuts?",
                "What types of finishing work are you most experienced with?"
            ]
        }
        
        questions = base_questions.copy()
        if trade in trade_specific:
            questions.extend(trade_specific[trade])
        
        return questions[:8]  # Return top 8 questions
    
    def get_conversation_response(self, user_message: str, context: Dict = None) -> str:
        """Generate a conversational response to user queries"""
        if not self.client:
            return "I'd love to help, but I need the OpenAI API key configured first. Please add it in your settings!"
        
        try:
            system_prompt = """You are Scout, a friendly and helpful recruitment assistant for TradesCompass Pro. 
            You help recruiters find skilled trades professionals (electricians, HVAC techs, plumbers, carpenters, etc.).
            Be conversational, encouraging, and professional. Use occasional emojis for friendliness.
            Keep responses concise and actionable. Focus on practical recruiting advice."""
            
            # Add context if available
            context_info = ""
            if context:
                if context.get('current_search'):
                    context_info += f"\nCurrent search: {context['current_search']}"
                if context.get('candidates_found'):
                    context_info += f"\nCandidates found: {context['candidates_found']}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_message}\n{context_info}"}
                ],
                max_tokens=200,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating conversation response: {e}")
            return "I'm having a bit of trouble right now, but I'm still here to help! What can I assist you with?"