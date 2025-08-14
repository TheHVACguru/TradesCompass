import os
import json
import logging
import requests
from typing import List, Dict, Any
from urllib.parse import urlencode
import time

class JobBoardAPI:
    """Base class for job board integrations"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for jobs - to be implemented by subclasses"""
        raise NotImplementedError

class JSearchAPI(JobBoardAPI):
    """JSearch API - Comprehensive job aggregator from Google for Jobs and 150,000+ sources"""
    
    def __init__(self):
        super().__init__(os.environ.get("RAPID_API_KEY"))
        self.base_url = "https://jsearch.p.rapidapi.com/search"
        self.headers = {
            "X-RapidAPI-Key": self.api_key if self.api_key else "",
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.info("RapidAPI key not found, skipping JSearch")
            return []
        
        try:
            params = {
                "query": f"{query} in {location}",
                "page": "1",
                "num_pages": "1",
                "date_posted": "month",  # Jobs posted in last month
                "remote_jobs_only": "false",
                "employment_types": "FULLTIME,PARTTIME,CONTRACTOR",
                "job_requirements": "no_degree,no_experience"  # Include all experience levels
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            if data.get('status') == 'OK' and 'data' in data:
                for job in data['data'][:max_results]:
                    # Determine the source platform
                    source = 'Multiple Sources'
                    if job.get('job_publisher'):
                        publisher = job['job_publisher'].lower()
                        if 'linkedin' in publisher:
                            source = 'LinkedIn'
                        elif 'indeed' in publisher:
                            source = 'Indeed'
                        elif 'glassdoor' in publisher:
                            source = 'Glassdoor'
                        elif 'ziprecruiter' in publisher:
                            source = 'ZipRecruiter'
                        elif 'monster' in publisher:
                            source = 'Monster'
                        else:
                            source = job['job_publisher']
                    
                    # Extract salary information
                    salary_info = 'Not specified'
                    if job.get('job_min_salary') and job.get('job_max_salary'):
                        salary_info = f"${job['job_min_salary']:,.0f} - ${job['job_max_salary']:,.0f}"
                        if job.get('job_salary_period'):
                            salary_info += f" {job['job_salary_period']}"
                    elif job.get('job_salary_currency'):
                        salary_info = f"{job.get('job_salary_currency', '')} - Competitive"
                    
                    job_info = {
                        'title': job.get('job_title', 'N/A'),
                        'company': job.get('employer_name', 'N/A'),
                        'location': f"{job.get('job_city', '')}, {job.get('job_state', '')} {job.get('job_country', '')}".strip(', '),
                        'url': job.get('job_apply_link', job.get('job_google_link', '#')),
                        'summary': job.get('job_description', 'No description available')[:200] + '...' if job.get('job_description') else 'No description available',
                        'posted_date': job.get('job_posted_at_datetime_utc', 'Recently')[:10] if job.get('job_posted_at_datetime_utc') else 'Recently',
                        'salary': salary_info,
                        'source': source,
                        'remote': job.get('job_is_remote', False),
                        'employment_type': job.get('job_employment_type', 'Full-time')
                    }
                    jobs.append(job_info)
            
            logging.info(f"JSearch returned {len(jobs)} jobs")
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from JSearch: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in JSearch: {str(e)}")
            return []

class ZipRecruiterAPI(JobBoardAPI):
    """ZipRecruiter job search integration"""
    
    def __init__(self):
        super().__init__(os.environ.get("ZIPRECRUITER_API_KEY"))
        self.base_url = "https://api.ziprecruiter.com/jobs/v1"
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.warning("ZipRecruiter API key not found")
            return []
        
        try:
            params = {
                'search': query,
                'location': location,
                'radius_miles': 50,
                'days_ago': 30,
                'jobs_per_page': max_results,
                'page': 1,
                'api_key': self.api_key
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            if 'jobs' in data:
                for job in data['jobs']:
                    job_info = {
                        'title': job.get('name', 'N/A'),
                        'company': job.get('hiring_company', {}).get('name', 'N/A'),
                        'location': job.get('location', 'N/A'),
                        'url': job.get('url', '#'),
                        'summary': job.get('snippet', 'No description available'),
                        'posted_date': job.get('posted_time_friendly', 'N/A'),
                        'salary': job.get('salary_interval', {}).get('formatted_salary', 'Not specified'),
                        'source': 'ZipRecruiter'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from ZipRecruiter: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in ZipRecruiter search: {str(e)}")
            return []

class IndeedAPI(JobBoardAPI):
    """Indeed job search integration using their publisher API"""
    
    def __init__(self):
        super().__init__(os.environ.get("INDEED_PUBLISHER_ID"))
        self.base_url = "http://api.indeed.com/ads/apisearch"
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.info("Indeed Publisher ID not found, skipping Indeed search")
            return []
        
        try:
            params = {
                'publisher': self.api_key,
                'q': query,
                'l': location,
                'sort': 'date',
                'radius': 50,
                'st': 'jobsite',
                'jt': 'fulltime',
                'start': 0,
                'limit': max_results,
                'fromage': 30,
                'format': 'json',
                'v': '2'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            if 'results' in data:
                for job in data['results']:
                    job_info = {
                        'title': job.get('jobtitle', 'N/A'),
                        'company': job.get('company', 'N/A'),
                        'location': f"{job.get('city', '')}, {job.get('state', '')}".strip(', '),
                        'url': job.get('url', '#'),
                        'summary': job.get('snippet', 'No description available'),
                        'posted_date': job.get('formattedRelativeTime', 'N/A'),
                        'salary': job.get('salary', 'Not specified'),
                        'source': 'Indeed'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from Indeed: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in Indeed search: {str(e)}")
            return []

class LinkedInAPI(JobBoardAPI):
    """LinkedIn job search integration using RapidAPI"""
    
    def __init__(self):
        super().__init__(os.environ.get("RAPID_API_KEY"))
        self.base_url = "https://linkedin-jobs-search.p.rapidapi.com/"
        self.headers = {
            "X-RapidAPI-Key": self.api_key if self.api_key else "",
            "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com"
        }
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.info("RapidAPI key not found, skipping LinkedIn search")
            return []
        
        try:
            payload = {
                "search_terms": query,
                "location": location,
                "page": "1"
            }
            
            response = requests.post(
                self.base_url, 
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            # Parse LinkedIn job results
            if isinstance(data, list):
                for idx, job in enumerate(data[:max_results]):
                    job_info = {
                        'title': job.get('job_title', 'N/A'),
                        'company': job.get('company_name', 'N/A'),
                        'location': job.get('job_location', location),
                        'url': job.get('job_url', '#'),
                        'summary': job.get('job_description', 'No description available')[:200] + '...' if job.get('job_description') else 'No description available',
                        'posted_date': job.get('posted_date', 'Recently'),
                        'salary': job.get('salary', 'Not specified'),
                        'source': 'LinkedIn'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from LinkedIn: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in LinkedIn search: {str(e)}")
            return []

class USAJobsAPI(JobBoardAPI):
    """USAJobs.gov federal job search integration"""
    
    def __init__(self):
        super().__init__(os.environ.get("USAJOBS_API_KEY"))
        self.base_url = "https://data.usajobs.gov/api/search"
        self.user_agent = os.environ.get("USAJOBS_USER_AGENT", "resume-scanner@example.com")
    
    def search_jobs(self, query: str, location: str = "United States", max_results: int = 5) -> List[Dict[str, Any]]:
        try:
            headers = {
                'Host': 'data.usajobs.gov',
                'User-Agent': self.user_agent,
            }
            
            if self.api_key:
                headers['Authorization-Key'] = self.api_key
            
            params = {
                'Keyword': query,
                'LocationName': location,
                'ResultsPerPage': max_results,
                'Page': 1
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            jobs = []
            
            if 'SearchResult' in data and 'SearchResultItems' in data['SearchResult']:
                for item in data['SearchResult']['SearchResultItems']:
                    job = item.get('MatchedObjectDescriptor', {})
                    job_info = {
                        'title': job.get('PositionTitle', 'N/A'),
                        'company': job.get('OrganizationName', 'U.S. Government'),
                        'location': ', '.join(job.get('PositionLocationDisplay', [])),
                        'url': job.get('PositionURI', '#'),
                        'summary': job.get('QualificationSummary', 'Federal position'),
                        'posted_date': job.get('PublicationStartDate', 'N/A'),
                        'salary': f"{job.get('PositionRemuneration', [{}])[0].get('MinimumRange', 'Not specified')} - {job.get('PositionRemuneration', [{}])[0].get('MaximumRange', '')}",
                        'source': 'USAJobs'
                    }
                    jobs.append(job_info)
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching jobs from USAJobs: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in USAJobs search: {str(e)}")
            return []

class MultiJobBoardSearch:
    """Aggregates job searches across multiple job boards"""
    
    def __init__(self):
        # JSearch is primary as it aggregates from 150,000+ sources including LinkedIn, Indeed, Glassdoor, etc.
        self.primary_search = JSearchAPI()
        # Fallback individual APIs if JSearch is not available
        self.fallback_boards = [
            ZipRecruiterAPI(),
            IndeedAPI(),
            USAJobsAPI()
        ]
    
    def search_all_jobs(self, query: str, location: str = "United States", max_per_board: int = 3) -> List[Dict[str, Any]]:
        """Search jobs across all available job boards"""
        all_jobs = []
        
        # Try JSearch first - it aggregates from 150,000+ sources
        try:
            jsearch_jobs = self.primary_search.search_jobs(query, location, 15)
            if jsearch_jobs:
                logging.info(f"JSearch returned {len(jsearch_jobs)} jobs")
                all_jobs.extend(jsearch_jobs)
        except Exception as e:
            logging.error(f"Error with JSearch: {str(e)}")
        
        # If JSearch didn't return enough results or failed, use fallback APIs
        if len(all_jobs) < 10:
            for board in self.fallback_boards:
                try:
                    jobs = board.search_jobs(query, location, max_per_board)
                    all_jobs.extend(jobs)
                    # Small delay to be respectful to APIs
                    time.sleep(0.5)
                except Exception as e:
                    logging.error(f"Error searching {board.__class__.__name__}: {str(e)}")
                    continue
        
        # Remove duplicates based on title and company
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = (job['title'].lower(), job['company'].lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs[:20]  # Increased limit since we have better aggregation

# Convenience function for backward compatibility
def search_relevant_jobs(search_query, location="United States", max_results=5):
    """Search for relevant jobs using multiple job boards"""
    searcher = MultiJobBoardSearch()
    return searcher.search_all_jobs(search_query, location, max_results // 3)