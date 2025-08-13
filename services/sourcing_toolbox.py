"""
Enhanced Sourcing Toolbox for TalentCompass AI
Based on awesome-recruitment repository resources
"""

import json
import re
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

class SourcingToolbox:
    """Advanced sourcing tools and utilities for recruitment professionals"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # ============= Boolean Search Builder =============
    
    def build_boolean_search(self, 
                            job_title: str,
                            must_have_skills: List[str] = None,
                            nice_to_have_skills: List[str] = None,
                            exclude_terms: List[str] = None,
                            location: str = None,
                            platforms: List[str] = None) -> Dict[str, str]:
        """
        Build advanced Boolean search strings for different platforms
        
        Args:
            job_title: Target job title
            must_have_skills: Required skills
            nice_to_have_skills: Optional skills
            exclude_terms: Terms to exclude
            location: Target location
            platforms: List of platforms to generate queries for
        
        Returns:
            Dictionary of platform-specific Boolean search strings
        """
        queries = {}
        
        # Default platforms if not specified
        if not platforms:
            platforms = ['linkedin', 'github', 'google', 'indeed']
        
        for platform in platforms:
            if platform.lower() == 'linkedin':
                queries['linkedin'] = self._build_linkedin_boolean(
                    job_title, must_have_skills, nice_to_have_skills, exclude_terms, location
                )
            elif platform.lower() == 'github':
                queries['github'] = self._build_github_search(
                    must_have_skills, location
                )
            elif platform.lower() == 'google':
                queries['google'] = self._build_google_xray(
                    job_title, must_have_skills, nice_to_have_skills, exclude_terms, location
                )
            elif platform.lower() == 'indeed':
                queries['indeed'] = self._build_indeed_boolean(
                    job_title, must_have_skills, location
                )
        
        return queries
    
    def _build_linkedin_boolean(self, job_title: str, must_have: List[str], 
                               nice_to_have: List[str], exclude: List[str], 
                               location: str) -> str:
        """Build LinkedIn-specific Boolean search"""
        query_parts = []
        
        # Title variations
        title_variations = self._get_title_variations(job_title)
        if title_variations:
            query_parts.append(f'({" OR ".join([f\'"{t}"\' for t in title_variations])})')
        
        # Must-have skills
        if must_have:
            query_parts.append(f'({" AND ".join([f\'"{s}"\' for s in must_have])})')
        
        # Nice-to-have skills
        if nice_to_have:
            query_parts.append(f'({" OR ".join([f\'"{s}"\' for s in nice_to_have])})')
        
        # Location
        if location:
            query_parts.append(f'"{location}"')
        
        # Exclusions
        if exclude:
            for term in exclude:
                query_parts.append(f'NOT "{term}"')
        
        return ' '.join(query_parts)
    
    def _build_github_search(self, skills: List[str], location: str) -> str:
        """Build GitHub-specific search query"""
        query_parts = []
        
        if skills:
            # GitHub searches by language/skill
            query_parts.append(' '.join([f'language:{s}' for s in skills[:3]]))
        
        if location:
            query_parts.append(f'location:"{location}"')
        
        return ' '.join(query_parts)
    
    def _build_google_xray(self, job_title: str, must_have: List[str],
                          nice_to_have: List[str], exclude: List[str],
                          location: str) -> str:
        """Build Google X-Ray search for LinkedIn profiles"""
        query = 'site:linkedin.com/in/'
        
        # Add title
        if job_title:
            query += f' intitle:"{job_title}"'
        
        # Add must-have skills
        if must_have:
            query += ' ' + ' '.join([f'"{s}"' for s in must_have])
        
        # Add nice-to-have with OR
        if nice_to_have:
            query += f' ({" OR ".join([f\'"{s}"\' for s in nice_to_have])})'
        
        # Add location
        if location:
            query += f' "{location}"'
        
        # Add exclusions
        if exclude:
            query += ' ' + ' '.join([f'-"{term}"' for term in exclude])
        
        return query
    
    def _build_indeed_boolean(self, job_title: str, skills: List[str], location: str) -> str:
        """Build Indeed resume search query"""
        query_parts = []
        
        if job_title:
            query_parts.append(f'title:({job_title})')
        
        if skills:
            query_parts.append(' '.join(skills))
        
        if location:
            query_parts.append(f'"{location}"')
        
        return ' '.join(query_parts)
    
    def _get_title_variations(self, job_title: str) -> List[str]:
        """Get common variations of a job title"""
        variations = [job_title]
        
        # Common variations mapping
        title_map = {
            'software engineer': ['software developer', 'programmer', 'SWE'],
            'data scientist': ['data analyst', 'ML engineer', 'machine learning engineer'],
            'product manager': ['PM', 'product owner', 'PO'],
            'devops engineer': ['site reliability engineer', 'SRE', 'infrastructure engineer'],
            'frontend developer': ['front-end developer', 'UI developer', 'frontend engineer'],
            'backend developer': ['back-end developer', 'backend engineer', 'server-side developer'],
            'full stack developer': ['fullstack developer', 'full-stack engineer'],
            'ux designer': ['user experience designer', 'UX/UI designer', 'product designer'],
            'qa engineer': ['QA analyst', 'test engineer', 'quality assurance engineer']
        }
        
        job_title_lower = job_title.lower()
        for key, values in title_map.items():
            if key in job_title_lower:
                variations.extend(values)
                break
        
        return variations[:4]  # Limit to 4 variations
    
    # ============= GitHub Developer Insights =============
    
    def get_github_developer_stats(self, username: str) -> Dict[str, Any]:
        """
        Get GitHub developer statistics and insights
        
        Args:
            username: GitHub username
        
        Returns:
            Developer statistics including repos, languages, contributions
        """
        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            
            # Get user info
            user_url = f"https://api.github.com/users/{username}"
            user_response = requests.get(user_url, headers=headers, timeout=10)
            
            if user_response.status_code != 200:
                return None
            
            user_data = user_response.json()
            
            # Get repositories
            repos_url = f"https://api.github.com/users/{username}/repos"
            repos_response = requests.get(repos_url, headers=headers, 
                                         params={'per_page': 100}, timeout=10)
            
            repos = repos_response.json() if repos_response.status_code == 200 else []
            
            # Analyze repositories
            languages = {}
            total_stars = 0
            total_forks = 0
            
            for repo in repos:
                if repo.get('language'):
                    languages[repo['language']] = languages.get(repo['language'], 0) + 1
                total_stars += repo.get('stargazers_count', 0)
                total_forks += repo.get('forks_count', 0)
            
            # Sort languages by frequency
            top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'username': username,
                'name': user_data.get('name'),
                'bio': user_data.get('bio'),
                'company': user_data.get('company'),
                'location': user_data.get('location'),
                'email': user_data.get('email'),
                'blog': user_data.get('blog'),
                'public_repos': user_data.get('public_repos', 0),
                'followers': user_data.get('followers', 0),
                'following': user_data.get('following', 0),
                'created_at': user_data.get('created_at'),
                'top_languages': [lang[0] for lang in top_languages],
                'language_breakdown': dict(top_languages),
                'total_stars': total_stars,
                'total_forks': total_forks,
                'profile_url': user_data.get('html_url'),
                'hireable': user_data.get('hireable'),
                'activity_level': self._calculate_activity_level(
                    user_data.get('public_repos', 0),
                    total_stars,
                    user_data.get('followers', 0)
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching GitHub stats for {username}: {e}")
            return None
    
    def _calculate_activity_level(self, repos: int, stars: int, followers: int) -> str:
        """Calculate developer activity level based on GitHub metrics"""
        score = (repos * 2) + (stars * 3) + (followers * 1)
        
        if score >= 500:
            return 'Very High'
        elif score >= 200:
            return 'High'
        elif score >= 50:
            return 'Medium'
        else:
            return 'Low'
    
    # ============= Contact Discovery Tools =============
    
    def get_contact_finder_links(self, name: str, company: str = None) -> Dict[str, str]:
        """
        Generate links to popular contact finding tools
        
        Args:
            name: Person's full name
            company: Company name (optional)
        
        Returns:
            Dictionary of service names and search URLs
        """
        links = {}
        
        # URL encode the parameters
        from urllib.parse import quote
        encoded_name = quote(name)
        encoded_company = quote(company) if company else ''
        
        # Generate search links for various tools
        links['Hunter.io'] = f"https://hunter.io/search/{encoded_company}" if company else "https://hunter.io"
        links['Clearbit Connect'] = f"https://connect.clearbit.com/search?query={encoded_name}"
        links['RocketReach'] = f"https://rocketreach.co/search?name={encoded_name}"
        links['Lusha'] = "https://www.lusha.com"
        links['ContactOut'] = "https://contactout.com"
        links['Anymail Finder'] = f"https://anymailfinder.com/search/{encoded_name}"
        links['Snovio'] = f"https://snov.io/email-finder#name={encoded_name}"
        links['Signal Hire'] = "https://www.signalhire.com"
        
        # Add LinkedIn search
        links['LinkedIn Search'] = f"https://www.linkedin.com/search/results/people/?keywords={encoded_name}"
        if company:
            links['LinkedIn + Company'] = f"https://www.linkedin.com/search/results/people/?keywords={encoded_name}%20{encoded_company}"
        
        return links
    
    # ============= Job Description Quality Analyzer =============
    
    def analyze_job_description_quality(self, job_description: str) -> Dict[str, Any]:
        """
        Analyze job description for quality, bias, and inclusiveness
        
        Args:
            job_description: Job description text
        
        Returns:
            Analysis results including bias detection and suggestions
        """
        analysis = {
            'word_count': len(job_description.split()),
            'readability_score': self._calculate_readability(job_description),
            'bias_issues': [],
            'missing_sections': [],
            'suggestions': [],
            'inclusive_score': 0
        }
        
        # Check for biased language
        bias_terms = {
            'masculine_coded': [
                'aggressive', 'ambitious', 'analytical', 'assertive', 'athletic',
                'autonomous', 'competitive', 'confident', 'decisive', 'determined',
                'dominant', 'driven', 'fearless', 'independent', 'individual',
                'leader', 'ninja', 'rockstar', 'strong', 'superior'
            ],
            'feminine_coded': [
                'collaborative', 'cooperative', 'dependable', 'emotional',
                'empathetic', 'gentle', 'honest', 'interpersonal', 'kind',
                'loyal', 'nurturing', 'pleasant', 'polite', 'quiet',
                'responsible', 'sensitive', 'supportive', 'warm', 'understanding'
            ],
            'age_bias': [
                'young', 'energetic', 'digital native', 'recent graduate',
                'fresh', 'mature', 'seasoned', 'overqualified'
            ],
            'culture_bias': [
                'native speaker', 'native English', 'culture fit',
                'work hard play hard', 'like a family'
            ]
        }
        
        jd_lower = job_description.lower()
        
        # Check for bias
        for bias_type, terms in bias_terms.items():
            found_terms = [term for term in terms if term in jd_lower]
            if found_terms:
                analysis['bias_issues'].append({
                    'type': bias_type,
                    'terms_found': found_terms,
                    'severity': 'high' if len(found_terms) > 3 else 'medium'
                })
        
        # Check for required sections
        required_sections = [
            'responsibilities', 'requirements', 'qualifications',
            'benefits', 'about', 'equal opportunity'
        ]
        
        for section in required_sections:
            if section not in jd_lower:
                analysis['missing_sections'].append(section)
        
        # Generate suggestions
        if analysis['word_count'] < 150:
            analysis['suggestions'].append('Job description is too short. Aim for 300-800 words.')
        elif analysis['word_count'] > 1000:
            analysis['suggestions'].append('Job description is too long. Consider being more concise.')
        
        if analysis['bias_issues']:
            analysis['suggestions'].append('Consider using more neutral language to attract diverse candidates.')
        
        if 'equal opportunity' in analysis['missing_sections']:
            analysis['suggestions'].append('Add an Equal Opportunity Employer statement.')
        
        # Calculate inclusive score
        inclusive_score = 100
        inclusive_score -= len(analysis['bias_issues']) * 20
        inclusive_score -= len(analysis['missing_sections']) * 10
        analysis['inclusive_score'] = max(0, inclusive_score)
        
        return analysis
    
    def _calculate_readability(self, text: str) -> str:
        """Calculate readability level of text"""
        sentences = text.count('.') + text.count('!') + text.count('?')
        words = len(text.split())
        
        if sentences == 0:
            return 'Unknown'
        
        avg_words_per_sentence = words / sentences
        
        if avg_words_per_sentence < 15:
            return 'Easy'
        elif avg_words_per_sentence < 20:
            return 'Medium'
        else:
            return 'Difficult'
    
    # ============= Compensation Benchmarking =============
    
    def get_salary_benchmark_links(self, job_title: str, location: str = None) -> Dict[str, str]:
        """
        Generate links to salary benchmarking resources
        
        Args:
            job_title: Job title to research
            location: Location for salary data
        
        Returns:
            Dictionary of salary research links
        """
        from urllib.parse import quote
        
        encoded_title = quote(job_title)
        encoded_location = quote(location) if location else ''
        
        links = {
            'Glassdoor': f"https://www.glassdoor.com/Salaries/index.htm?search={encoded_title}",
            'PayScale': f"https://www.payscale.com/research/US/Job={encoded_title}/Salary",
            'Salary.com': f"https://www.salary.com/research/salary/alternate/{encoded_title}",
            'Indeed Salaries': f"https://www.indeed.com/career/{encoded_title}/salaries",
            'LinkedIn Salary': f"https://www.linkedin.com/salary/search?keywords={encoded_title}",
            'Levels.fyi': "https://www.levels.fyi",
            'Comparably': f"https://www.comparably.com/salaries/salaries-for-{encoded_title}",
            'Robert Half': "https://www.roberthalf.com/salary-guide"
        }
        
        if location:
            links['Glassdoor + Location'] = f"https://www.glassdoor.com/Salaries/{encoded_location}-{encoded_title}-salary.htm"
            links['Indeed + Location'] = f"https://www.indeed.com/career/{encoded_title}/salaries/{encoded_location}"
        
        return links
    
    # ============= Search Engine Operators Guide =============
    
    def get_advanced_search_tips(self) -> Dict[str, List[str]]:
        """
        Get advanced search operators and tips for different platforms
        
        Returns:
            Dictionary of platform-specific search tips
        """
        return {
            'google': [
                'site:linkedin.com/in/ - Search only LinkedIn profiles',
                'intitle:"software engineer" - Find pages with exact title',
                'filetype:pdf resume - Find PDF resumes',
                '"exact phrase" - Search for exact phrase',
                'term1 OR term2 - Either term',
                'term1 AND term2 - Both terms required',
                '-exclude - Exclude this term',
                'related:website.com - Find similar sites',
                'cache:website.com - View cached version'
            ],
            'linkedin': [
                'Use quotes for exact phrases: "machine learning"',
                'Boolean operators: AND, OR, NOT',
                'Parentheses for grouping: (Python OR Java) AND AWS',
                'Current company: "Google" OR "Facebook"',
                'Past company: "worked at Microsoft"',
                'School: "Stanford University"',
                'Industry filters in advanced search',
                'Connection degree filters (1st, 2nd, 3rd)'
            ],
            'github': [
                'language:python - Filter by programming language',
                'location:"San Francisco" - Filter by location',
                'followers:>100 - Users with more than 100 followers',
                'repos:>10 - Users with more than 10 repositories',
                'created:>2020-01-01 - Accounts created after date',
                'stars:>50 - Repositories with more than 50 stars',
                'user:username - Search within specific user\'s repos',
                'org:organization - Search within organization'
            ],
            'indeed': [
                'title:(software engineer) - Search in job title only',
                'company:Google - Search specific company',
                'salary:$100,000 - Minimum salary filter',
                '"exact phrase" - Exact phrase matching',
                'NOT keyword - Exclude keyword',
                'experience level filters',
                'job type filters (full-time, contract, etc.)',
                'date posted filters'
            ]
        }
    
    # ============= University Alumni Search =============
    
    def get_university_alumni_links(self, university: str = None) -> Dict[str, str]:
        """
        Get LinkedIn alumni search links for top universities
        
        Args:
            university: Specific university name (optional)
        
        Returns:
            Dictionary of university alumni search links
        """
        # Top universities for tech recruiting
        universities = {
            'MIT': 'massachusetts-institute-of-technology',
            'Stanford': 'stanford-university',
            'Harvard': 'harvard-university',
            'UC Berkeley': 'uc-berkeley',
            'Carnegie Mellon': 'carnegie-mellon-university',
            'Georgia Tech': 'georgia-institute-of-technology',
            'University of Washington': 'university-of-washington',
            'UIUC': 'university-of-illinois-at-urbana-champaign',
            'UT Austin': 'the-university-of-texas-at-austin',
            'Michigan': 'university-of-michigan',
            'Waterloo': 'university-of-waterloo',
            'Toronto': 'university-of-toronto',
            'Oxford': 'university-of-oxford',
            'Cambridge': 'university-of-cambridge',
            'IIT': 'indian-institute-of-technology'
        }
        
        links = {}
        
        if university:
            # Search for specific university
            from urllib.parse import quote
            encoded_uni = quote(university)
            links[university] = f"https://www.linkedin.com/school/{encoded_uni}/people/"
        else:
            # Return all top universities
            for name, linkedin_id in universities.items():
                links[name] = f"https://www.linkedin.com/school/{linkedin_id}/people/"
        
        return links
    
    # ============= Programming Communities =============
    
    def get_developer_communities(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get list of developer communities and forums for sourcing
        
        Returns:
            Dictionary of communities by category
        """
        return {
            'general_tech': [
                {'name': 'Stack Overflow', 'url': 'https://stackoverflow.com/users'},
                {'name': 'Dev.to', 'url': 'https://dev.to'},
                {'name': 'Hashnode', 'url': 'https://hashnode.com'},
                {'name': 'Reddit r/programming', 'url': 'https://reddit.com/r/programming'},
                {'name': 'HackerNews', 'url': 'https://news.ycombinator.com'},
                {'name': 'IndieHackers', 'url': 'https://www.indiehackers.com'},
                {'name': 'Product Hunt', 'url': 'https://www.producthunt.com'}
            ],
            'language_specific': [
                {'name': 'Python Discord', 'url': 'https://pythondiscord.com'},
                {'name': 'Reactiflux (React)', 'url': 'https://www.reactiflux.com'},
                {'name': 'Vue Land', 'url': 'https://vue-land.js.org'},
                {'name': 'Gophers Slack (Go)', 'url': 'https://invite.slack.golangbridge.org'},
                {'name': 'Rust Discord', 'url': 'https://discord.gg/rust-lang'},
                {'name': 'Ruby on Rails Discord', 'url': 'https://discord.gg/ruby-on-rails'}
            ],
            'specialized': [
                {'name': 'Women Who Code', 'url': 'https://www.womenwhocode.com'},
                {'name': 'CodeNewbie', 'url': 'https://www.codenewbie.org'},
                {'name': 'freeCodeCamp', 'url': 'https://www.freecodecamp.org/forum'},
                {'name': 'GitHub Discussions', 'url': 'https://github.com/discussions'},
                {'name': 'Kaggle (Data Science)', 'url': 'https://www.kaggle.com'},
                {'name': 'Dribbble (Design)', 'url': 'https://dribbble.com'},
                {'name': 'Behance (Design)', 'url': 'https://www.behance.net'}
            ],
            'slack_communities': [
                {'name': 'TechCommunity', 'url': 'https://techcommunity.microsoft.com'},
                {'name': 'iOS Developers', 'url': 'https://ios-developers.io'},
                {'name': 'Android Developers', 'url': 'https://android-united.community'},
                {'name': 'DevOps Chat', 'url': 'https://devopschat.co'},
                {'name': 'MLOps Community', 'url': 'https://mlops.community'}
            ]
        }