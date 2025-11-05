#!/usr/bin/env python3
"""
API connection test script for the Task Collection System.

This script tests individual API connections for Gmail, Slack, GitHub,
Google Calendar, and Notion to verify authentication and basic functionality.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install: pip install requests python-dotenv")
    sys.exit(1)


@dataclass
class TestResult:
    """Test result data structure"""
    service: str
    test_name: str
    success: bool
    message: str
    details: Optional[Dict] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class APITester:
    """Main API testing class"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.results: List[TestResult] = []
        self.setup_logging()
        self.load_environment()
        self.load_settings()
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/api_test.log', mode='a')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_environment(self):
        """Load environment variables from .env file"""
        root_env = project_root / '.env'
        fallback_env = self.config_dir / '.env'
        env_file = root_env if root_env.exists() else fallback_env
        if env_file.exists():
            load_dotenv(env_file)
            location = 'project root' if env_file == root_env else 'config directory'
            self.logger.info(f"Environment variables loaded from {location} .env file: {env_file}")
        else:
            self.logger.warning(f".env file not found at {root_env} or {fallback_env}")
            self.logger.info("Using system environment variables")
    
    def load_settings(self):
        """Load application settings"""
        settings_file = self.config_dir / 'settings.json'
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
            self.logger.info("Settings loaded successfully")
        except FileNotFoundError:
            self.logger.error(f"Settings file not found: {settings_file}")
            self.settings = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in settings file: {e}")
            self.settings = {}
    
    def add_result(self, service: str, test_name: str, success: bool, 
                   message: str, details: Optional[Dict] = None):
        """Add a test result"""
        result = TestResult(service, test_name, success, message, details)
        self.results.append(result)
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"{service} - {test_name}: {message}")
    
    def test_gmail_api(self) -> List[TestResult]:
        """Test Gmail API connection and authentication"""
        service = "Gmail"
        results = []
        
        # Check environment variables
        required_vars = [
            'GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 
            'GMAIL_REFRESH_TOKEN', 'GMAIL_ACCESS_TOKEN'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.add_result(
                service, "Environment Check", False,
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            return self.results
        
        self.add_result(
            service, "Environment Check", True,
            "All required environment variables found"
        )
        
        # Test authentication
        try:
            headers = {
                'Authorization': f'Bearer {os.getenv("GMAIL_ACCESS_TOKEN")}',
                'Content-Type': 'application/json'
            }
            
            # Test basic profile access
            response = requests.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/profile',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                profile_data = response.json()
                self.add_result(
                    service, "Authentication Test", True,
                    f"Successfully authenticated. Email: {profile_data.get('emailAddress', 'N/A')}",
                    {"profile": profile_data}
                )
            else:
                self.add_result(
                    service, "Authentication Test", False,
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return self.results
                
        except requests.RequestException as e:
            self.add_result(
                service, "Authentication Test", False,
                f"Network error during authentication: {str(e)}"
            )
            return self.results
        
        # Test basic data retrieval
        try:
            # Get message list (limited to 5 for testing)
            response = requests.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages',
                headers=headers,
                params={'maxResults': 5},
                timeout=30
            )
            
            if response.status_code == 200:
                messages_data = response.json()
                message_count = len(messages_data.get('messages', []))
                self.add_result(
                    service, "Data Retrieval Test", True,
                    f"Successfully retrieved {message_count} messages",
                    {"message_count": message_count}
                )
            else:
                self.add_result(
                    service, "Data Retrieval Test", False,
                    f"Failed to retrieve messages: {response.status_code}"
                )
                
        except requests.RequestException as e:
            self.add_result(
                service, "Data Retrieval Test", False,
                f"Network error during data retrieval: {str(e)}"
            )
        
        return self.results
    
    def test_slack_api(self) -> List[TestResult]:
        """Test Slack API connection and authentication"""
        service = "Slack"
        
        # Check environment variables (user token is required, bot token optional)
        required_vars = ['SLACK_USER_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.add_result(
                service, "Environment Check", False,
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            return self.results
        
        self.add_result(
            service, "Environment Check", True,
            "All required environment variables found"
        )
        
        user_token = os.getenv("SLACK_USER_TOKEN")
        user_headers = {
            'Authorization': f'Bearer {user_token}',
            'Content-Type': 'application/json',
        }
        
        # Test user token authentication
        try:
            response = requests.get(
                'https://slack.com/api/auth.test',
                headers=user_headers,
                timeout=30,
            )
            if response.status_code == 200:
                auth_data = response.json()
                if auth_data.get('ok'):
                    self.add_result(
                        service,
                        "User Token Authentication",
                        True,
                        f"User authenticated successfully. Team: {auth_data.get('team', 'N/A')}",
                        {"auth_info": auth_data},
                    )
                else:
                    self.add_result(
                        service,
                        "User Token Authentication",
                        False,
                        f"User authentication failed: {auth_data.get('error', 'Unknown error')}",
                    )
                    return self.results
            else:
                self.add_result(
                    service,
                    "User Token Authentication",
                    False,
                    f"HTTP error: {response.status_code}",
                )
                return self.results
        except requests.RequestException as exc:
            self.add_result(
                service,
                "User Token Authentication",
                False,
                f"Network error: {exc}",
            )
            return self.results
        
        # Test basic data retrieval aligned with MCP server behaviour (list joined conversations)
        try:
            response = requests.get(
                'https://slack.com/api/users.conversations',
                headers=user_headers,
                params={
                    'limit': 5,
                    'types': 'public_channel,private_channel,im,mpim',
                },
                timeout=30,
            )
            if response.status_code == 200:
                conversations_data = response.json()
                if conversations_data.get('ok'):
                    # Only channels the user is a member of are returned by this API
                    channel_count = len(conversations_data.get('channels', []))
                    self.add_result(
                        service,
                        "Data Retrieval Test",
                        True,
                        f"Successfully retrieved {channel_count} joined conversations",
                        {"channel_count": channel_count},
                    )
                else:
                    self.add_result(
                        service,
                        "Data Retrieval Test",
                        False,
                        f"Failed to retrieve conversations: {conversations_data.get('error', 'Unknown error')}",
                    )
            else:
                self.add_result(
                    service,
                    "Data Retrieval Test",
                    False,
                    f"HTTP error: {response.status_code}",
                )
        except requests.RequestException as exc:
            self.add_result(
                service,
                "Data Retrieval Test",
                False,
                f"Network error: {exc}",
            )
        
        # Optional: validate bot token if provided (useful when MCP server will still use it)
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        if bot_token:
            bot_headers = {
                'Authorization': f'Bearer {bot_token}',
                'Content-Type': 'application/json',
            }
            try:
                response = requests.get(
                    'https://slack.com/api/auth.test',
                    headers=bot_headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    bot_auth = response.json()
                    if bot_auth.get('ok'):
                        self.add_result(
                            service,
                            "Bot Token Authentication (Optional)",
                            True,
                            f"Bot authenticated successfully. Team: {bot_auth.get('team', 'N/A')}",
                            {"auth_info": bot_auth},
                        )
                    else:
                        self.add_result(
                            service,
                            "Bot Token Authentication (Optional)",
                            False,
                            f"Bot authentication failed: {bot_auth.get('error', 'Unknown error')}",
                        )
                else:
                    self.add_result(
                        service,
                        "Bot Token Authentication (Optional)",
                        False,
                        f"HTTP error: {response.status_code}",
                    )
            except requests.RequestException as exc:
                self.add_result(
                    service,
                    "Bot Token Authentication (Optional)",
                    False,
                    f"Network error: {exc}",
                )
        
        return self.results 
   
    def test_github_api(self) -> List[TestResult]:
        """Test GitHub API connection and authentication"""
        service = "GitHub"
        
        # Check environment variables
        required_vars = ['GITHUB_TOKEN', 'GITHUB_USERNAME']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.add_result(
                service, "Environment Check", False,
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            return self.results
        
        self.add_result(
            service, "Environment Check", True,
            "All required environment variables found"
        )
        
        # Test authentication
        try:
            headers = {
                'Authorization': f'token {os.getenv("GITHUB_TOKEN")}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Task-Collection-Test'
            }
            
            response = requests.get(
                'https://api.github.com/user',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.add_result(
                    service, "Authentication Test", True,
                    f"Successfully authenticated. User: {user_data.get('login', 'N/A')}",
                    {"user_info": user_data}
                )
            else:
                self.add_result(
                    service, "Authentication Test", False,
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return self.results
                
        except requests.RequestException as e:
            self.add_result(
                service, "Authentication Test", False,
                f"Network error: {str(e)}"
            )
            return self.results
        
        # Test basic data retrieval (user's repositories)
        try:
            username = os.getenv("GITHUB_USERNAME")
            response = requests.get(
                f'https://api.github.com/users/{username}/repos',
                headers=headers,
                params={'per_page': 5, 'sort': 'updated'},
                timeout=30
            )
            
            if response.status_code == 200:
                repos_data = response.json()
                repo_count = len(repos_data)
                self.add_result(
                    service, "Data Retrieval Test", True,
                    f"Successfully retrieved {repo_count} repositories",
                    {"repo_count": repo_count}
                )
            else:
                self.add_result(
                    service, "Data Retrieval Test", False,
                    f"Failed to retrieve repositories: {response.status_code}"
                )
                
        except requests.RequestException as e:
            self.add_result(
                service, "Data Retrieval Test", False,
                f"Network error: {str(e)}"
            )
        
        # Test issues retrieval
        try:
            response = requests.get(
                'https://api.github.com/issues',
                headers=headers,
                params={'filter': 'assigned', 'state': 'open', 'per_page': 5},
                timeout=30
            )
            
            if response.status_code == 200:
                issues_data = response.json()
                issue_count = len(issues_data)
                self.add_result(
                    service, "Issues Retrieval Test", True,
                    f"Successfully retrieved {issue_count} assigned issues",
                    {"issue_count": issue_count}
                )
            else:
                self.add_result(
                    service, "Issues Retrieval Test", False,
                    f"Failed to retrieve issues: {response.status_code}"
                )
                
        except requests.RequestException as e:
            self.add_result(
                service, "Issues Retrieval Test", False,
                f"Network error: {str(e)}"
            )
        
        return self.results
    
    def test_google_calendar_api(self) -> List[TestResult]:
        """Test Google Calendar API connection and authentication"""
        service = "Google Calendar"
        
        # Check environment variables
        required_vars = [
            'GOOGLE_CALENDAR_CLIENT_ID', 'GOOGLE_CALENDAR_CLIENT_SECRET',
            'GOOGLE_CALENDAR_REFRESH_TOKEN', 'GOOGLE_CALENDAR_ACCESS_TOKEN'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            self.add_result(
                service, "Environment Check", False,
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            return self.results
        
        self.add_result(
            service, "Environment Check", True,
            "All required environment variables found"
        )
        
        # Test authentication
        try:
            headers = {
                'Authorization': f'Bearer {os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                'https://www.googleapis.com/calendar/v3/users/me/calendarList',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                calendar_data = response.json()
                calendar_count = len(calendar_data.get('items', []))
                self.add_result(
                    service, "Authentication Test", True,
                    f"Successfully authenticated. Found {calendar_count} calendars",
                    {"calendar_count": calendar_count}
                )
            else:
                self.add_result(
                    service, "Authentication Test", False,
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return self.results
                
        except requests.RequestException as e:
            self.add_result(
                service, "Authentication Test", False,
                f"Network error: {str(e)}"
            )
            return self.results
        
        # Test basic data retrieval (events from primary calendar)
        try:
            # Get events for the next 7 days
            time_min = datetime.now().isoformat() + 'Z'
            time_max = (datetime.now() + timedelta(days=7)).isoformat() + 'Z'
            
            response = requests.get(
                'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                headers=headers,
                params={
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'maxResults': 10,
                    'singleEvents': True,
                    'orderBy': 'startTime'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                events_data = response.json()
                event_count = len(events_data.get('items', []))
                self.add_result(
                    service, "Data Retrieval Test", True,
                    f"Successfully retrieved {event_count} events for next 7 days",
                    {"event_count": event_count}
                )
            else:
                self.add_result(
                    service, "Data Retrieval Test", False,
                    f"Failed to retrieve events: {response.status_code}"
                )
                
        except requests.RequestException as e:
            self.add_result(
                service, "Data Retrieval Test", False,
                f"Network error: {str(e)}"
            )
        
        return self.results
    
    def test_notion_api(self) -> List[TestResult]:
        """Test Notion API connection and authentication"""
        service = "Notion"
        
        # Check environment variables
        required_vars = ['NOTION_TOKEN', 'NOTION_DATABASE_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.add_result(
                service, "Environment Check", False,
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            return self.results
        
        self.add_result(
            service, "Environment Check", True,
            "All required environment variables found"
        )
        
        # Test authentication
        try:
            headers = {
                'Authorization': f'Bearer {os.getenv("NOTION_TOKEN")}',
                'Content-Type': 'application/json',
                'Notion-Version': '2022-06-28'
            }
            
            response = requests.get(
                'https://api.notion.com/v1/users/me',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.add_result(
                    service, "Authentication Test", True,
                    f"Successfully authenticated. User type: {user_data.get('type', 'N/A')}",
                    {"user_info": user_data}
                )
            else:
                self.add_result(
                    service, "Authentication Test", False,
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return self.results
                
        except requests.RequestException as e:
            self.add_result(
                service, "Authentication Test", False,
                f"Network error: {str(e)}"
            )
            return self.results
        
        # Test database access
        try:
            database_id = os.getenv("NOTION_DATABASE_ID")
            response = requests.get(
                f'https://api.notion.com/v1/databases/{database_id}',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                database_data = response.json()
                self.add_result(
                    service, "Database Access Test", True,
                    f"Successfully accessed database: {database_data.get('title', [{}])[0].get('plain_text', 'N/A')}",
                    {"database_info": database_data}
                )
            else:
                self.add_result(
                    service, "Database Access Test", False,
                    f"Failed to access database: {response.status_code} - {response.text}"
                )
                return self.results
                
        except requests.RequestException as e:
            self.add_result(
                service, "Database Access Test", False,
                f"Network error: {str(e)}"
            )
            return self.results
        
        # Test basic data retrieval (query database)
        try:
            response = requests.post(
                f'https://api.notion.com/v1/databases/{database_id}/query',
                headers=headers,
                json={'page_size': 5},
                timeout=30
            )
            
            if response.status_code == 200:
                query_data = response.json()
                page_count = len(query_data.get('results', []))
                self.add_result(
                    service, "Data Retrieval Test", True,
                    f"Successfully queried database. Found {page_count} pages",
                    {"page_count": page_count}
                )
            else:
                self.add_result(
                    service, "Data Retrieval Test", False,
                    f"Failed to query database: {response.status_code}"
                )
                
        except requests.RequestException as e:
            self.add_result(
                service, "Data Retrieval Test", False,
                f"Network error: {str(e)}"
            )
        
        return self.results
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all API tests"""
        self.logger.info("Starting API connection tests...")
        
        # Check if services are enabled in settings
        data_collection = self.settings.get('data_collection', {})
        
        if data_collection.get('gmail', {}).get('enabled', True):
            self.logger.info("Testing Gmail API...")
            self.test_gmail_api()
        else:
            self.logger.info("Gmail API testing skipped (disabled in settings)")
        
        if data_collection.get('slack', {}).get('enabled', True):
            self.logger.info("Testing Slack API...")
            self.test_slack_api()
        else:
            self.logger.info("Slack API testing skipped (disabled in settings)")
        
        if data_collection.get('github', {}).get('enabled', True):
            self.logger.info("Testing GitHub API...")
            self.test_github_api()
        else:
            self.logger.info("GitHub API testing skipped (disabled in settings)")
        
        if data_collection.get('google_calendar', {}).get('enabled', True):
            self.logger.info("Testing Google Calendar API...")
            self.test_google_calendar_api()
        else:
            self.logger.info("Google Calendar API testing skipped (disabled in settings)")
        
        # Notion is always tested as it's the output destination
        self.logger.info("Testing Notion API...")
        self.test_notion_api()
        
        self.logger.info("All API tests completed")
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report"""
        if not self.results:
            return "No test results available"
        
        # Group results by service
        services = {}
        for result in self.results:
            if result.service not in services:
                services[result.service] = []
            services[result.service].append(result)
        
        # Generate report
        report_lines = [
            "=" * 60,
            "API Connection Test Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        report_lines.extend([
            f"Overall Summary:",
            f"  Total Tests: {total_tests}",
            f"  Passed: {passed_tests}",
            f"  Failed: {failed_tests}",
            f"  Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "  Success Rate: 0%",
            ""
        ])
        
        # Service-by-service breakdown
        for service_name, service_results in services.items():
            service_passed = sum(1 for r in service_results if r.success)
            service_total = len(service_results)
            
            status_icon = "✅" if service_passed == service_total else "❌"
            report_lines.extend([
                f"{status_icon} {service_name} ({service_passed}/{service_total} tests passed)",
                "-" * 40
            ])
            
            for result in service_results:
                status = "✅ PASS" if result.success else "❌ FAIL"
                report_lines.append(f"  {status} {result.test_name}")
                report_lines.append(f"    {result.message}")
                
                if result.details and not result.success:
                    # Show error details for failed tests
                    for key, value in result.details.items():
                        report_lines.append(f"    {key}: {value}")
                
                report_lines.append("")
            
            report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "Recommendations:",
            "-" * 20
        ])
        
        if failed_tests > 0:
            report_lines.append("• Fix failed authentication issues before proceeding")
            report_lines.append("• Check environment variables and API credentials")
            report_lines.append("• Verify API permissions and scopes")
        else:
            report_lines.append("• All APIs are working correctly")
            report_lines.append("• System is ready for production use")
        
        report_lines.extend([
            "",
            "For detailed troubleshooting, check:",
            "• docs/TROUBLESHOOTING.md",
            "• docs/API_SETUP.md",
            "• logs/api_test.log",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def save_report(self, filename: str = None) -> str:
        """Save test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/api_test_report_{timestamp}.txt"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        report = self.generate_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return filename


def main():
    """Main function to run API tests"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test API connections for the Task Collection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_individual_apis.py                    # Test all APIs
  python test_individual_apis.py --service gmail    # Test only Gmail API
  python test_individual_apis.py --quiet            # Minimal output
  python test_individual_apis.py --config ../config # Use different config directory
        """
    )
    
    parser.add_argument(
        '--service', 
        choices=['gmail', 'slack', 'github', 'calendar', 'notion'],
        help='Test only a specific service'
    )
    
    parser.add_argument(
        '--config',
        default='config',
        help='Configuration directory path (default: config)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output (only show summary)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output report file path (default: auto-generated in logs/)'
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("Task Collection System - API Connection Test")
        print("=" * 50)
    
    try:
        # Initialize tester
        tester = APITester(config_dir=args.config)
        
        # Run specific service test or all tests
        if args.service:
            if args.service == 'gmail':
                tester.test_gmail_api()
            elif args.service == 'slack':
                tester.test_slack_api()
            elif args.service == 'github':
                tester.test_github_api()
            elif args.service == 'calendar':
                tester.test_google_calendar_api()
            elif args.service == 'notion':
                tester.test_notion_api()
        else:
            # Run all tests
            tester.run_all_tests()
        
        # Generate and display report
        report = tester.generate_report()
        
        if args.quiet:
            # Show only summary for quiet mode
            lines = report.split('\n')
            summary_start = next(i for i, line in enumerate(lines) if 'Overall Summary:' in line)
            summary_end = next(i for i, line in enumerate(lines[summary_start:]) if line == '') + summary_start
            print('\n'.join(lines[summary_start:summary_end]))
        else:
            print(report)
        
        # Save report to file
        report_file = tester.save_report(args.output)
        if not args.quiet:
            print(f"Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        failed_count = sum(1 for r in tester.results if not r.success)
        sys.exit(0 if failed_count == 0 else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        logging.exception("Unexpected error during API testing")
        sys.exit(1)


if __name__ == "__main__":
    main()
