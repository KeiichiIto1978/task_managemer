#!/usr/bin/env python3
"""
Configuration validation script for the Task Collection System.
Validates MCP configuration, environment variables, and file structure.
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

@dataclass
class ValidationResult:
    """Validation result with status and details."""
    is_valid: bool
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class ConfigValidator:
    """Main configuration validator class."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.config_dir = self.project_root / "config"
        self.scripts_dir = self.project_root / "scripts"
        self.docs_dir = self.project_root / "docs"
        self.logs_dir = self.project_root / "logs"
        self.servers_dir = self.project_root / "servers"
        self.tests_dir = self.project_root / "tests"
        self.cache_dir = self.project_root / "cache"
        self.results: List[ValidationResult] = []
        self.env_loaded = self.load_dotenv_file()
    
    def load_dotenv_file(self) -> bool:
        """Load environment variables from project root .env if available."""
        env_path = self.project_root / ".env"
        if not env_path.exists():
            return False
        try:
            load_dotenv(env_path)
        except Exception as exc:
            print(f"Error loading .env file: {exc}", file=sys.stderr)
            return False
        return True

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("$D83D$DD0D Starting configuration validation...")
        print(f"$D83D$DCC1 Project root: {self.project_root}")
        print("-" * 50)
        
        # Run all validation checks
        checks = [
            ("Directory Structure", self.validate_directory_structure),
            ("Required Files", self.validate_required_files),
            ("MCP Configuration", self.validate_mcp_config),
            ("Environment Variables", self.validate_environment_variables),
            ("API Authentication", self.validate_api_authentication),
            ("Configuration Consistency", self.validate_config_consistency)
        ]
        
        all_valid = True
        for check_name, check_func in checks:
            print(f"\n$D83D$DCCB {check_name}:")
            try:
                result = check_func()
                self.results.append(result)
                if result.is_valid:
                    print(f"  $2705 {result.message}")
                else:
                    print(f"  $274C {result.message}")
                    if result.details:
                        for key, value in result.details.items():
                            print(f"     $2022 {key}: {value}")
                    all_valid = False
            except Exception as e:
                error_result = ValidationResult(False, f"Validation error: {str(e)}")
                self.results.append(error_result)
                print(f"  $274C {error_result.message}")
                all_valid = False
        
        # Print summary
        print("\n" + "=" * 50)
        if all_valid:
            print("$D83C$DF89 All validations passed! Configuration is ready.")
        else:
            print("$26A0$FE0F  Some validations failed. Please fix the issues above.")
        print("=" * 50)
        
        return all_valid
    
    def validate_directory_structure(self) -> ValidationResult:
        """Validate required directory structure exists."""
        required_dirs = [
            self.config_dir,
            self.scripts_dir,
            self.docs_dir,
            self.logs_dir,
            self.servers_dir,
            self.tests_dir,
            self.cache_dir,
            self.cache_dir / "slack",
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not dir_path.exists():
                missing_dirs.append(str(dir_path.relative_to(self.project_root)))
        
        if missing_dirs:
            return ValidationResult(
                False,
                "Missing required directories",
                {"missing_directories": missing_dirs}
            )
        
        return ValidationResult(True, "All required directories exist")
    
    def validate_required_files(self) -> ValidationResult:
        """Validate required files exist."""
        required_files = [
        self.config_dir / ".env.template",
        self.config_dir / "settings.json",
        self.config_dir / "mcp.json",
        self.project_root / "requirements.txt",
        self.project_root / ".gitignore",
        self.project_root / "README.md",
        self.docs_dir / "API_SETUP.md",
        self.docs_dir / "TROUBLESHOOTING.md",
        self.docs_dir / "workflow_prompts.md",
        self.docs_dir / "notion_prompts.md",
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path.relative_to(self.project_root)))
        
        if missing_files:
            return ValidationResult(
                False,
                "Missing required files",
                {"missing_files": missing_files}
            )
        
        return ValidationResult(True, "All required files exist")  
  
    def validate_mcp_config(self) -> ValidationResult:
        """Validate MCP configuration file."""
        mcp_config_path = self.config_dir / "mcp.json"
        
        if not mcp_config_path.exists():
            return ValidationResult(
                False,
                "MCP configuration file not found",
                {"expected_path": str(mcp_config_path.relative_to(self.project_root))}
            )
        
        try:
            with open(mcp_config_path, 'r', encoding='utf-8') as f:
                mcp_config = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationResult(
                False,
                "Invalid JSON in MCP configuration",
                {"error": str(e)}
            )
        except Exception as e:
            return ValidationResult(
                False,
                "Error reading MCP configuration",
                {"error": str(e)}
            )
        
        # Validate MCP configuration structure
        if "mcpServers" not in mcp_config:
            return ValidationResult(
                False,
                "MCP configuration missing 'mcpServers' section"
            )
        
        required_servers = ["gmail", "slack", "github", "google-calendar", "notion"]
        configured_servers = list(mcp_config["mcpServers"].keys())
        missing_servers = [server for server in required_servers if server not in configured_servers]
        
        issues = []
        
        # Check for missing servers
        if missing_servers:
            issues.append(f"Missing MCP servers: {', '.join(missing_servers)}")
        
        # Validate each server configuration
        for server_name, server_config in mcp_config["mcpServers"].items():
            if not isinstance(server_config, dict):
                issues.append(f"Server '{server_name}' configuration is not a dictionary")
                continue
            
            # Check required fields
            required_fields = ["command", "args"]
            for field in required_fields:
                if field not in server_config:
                    issues.append(f"Server '{server_name}' missing required field: {field}")
        
        if issues:
            return ValidationResult(
                False,
                "MCP configuration validation failed",
                {"issues": issues}
            )
        
        return ValidationResult(True, "MCP configuration is valid")
    
    def validate_environment_variables(self) -> ValidationResult:
        """Validate environment variables configuration."""
        env_template_path = self.config_dir / ".env.template"
        env_path = self.project_root / ".env"

        if not env_template_path.exists():
            return ValidationResult(
                False,
                "Environment template file not found"
            )

        # Read template to get required variables
        try:
            with open(env_template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except Exception as e:
            return ValidationResult(
                False,
                "Error reading environment template",
                {"error": str(e)}
            )

        # Extract variable names from template
        env_var_pattern = r'^([A-Z_][A-Z0-9_]*)='
        required_vars = []
        for line in template_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                match = re.match(env_var_pattern, line)
                if match:
                    required_vars.append(match.group(1))

        issues = []

        # Check if .env file exists
        if not env_path.exists():
            issues.append("Environment file (.env) not found at project root - copy from config/.env.template using setup.py")
        else:
            # Check if required variables are set
            missing_vars = []
            for var_name in required_vars:
                if not os.getenv(var_name):
                    missing_vars.append(var_name)

            if missing_vars:
                issues.append(f"Missing environment variables: {', '.join(missing_vars)}")

        details = {
            'required_variables': required_vars,
            'env_file_path': str(env_path),
            'env_loaded': self.env_loaded
        }

        if issues:
            details['issues'] = issues
            return ValidationResult(
                False,
                "Environment variables validation failed",
                details
            )

        return ValidationResult(True, "Environment variables configuration is valid", details)

    def validate_api_authentication(self) -> ValidationResult:
        """Validate API authentication information format."""
        issues = []
        
        # Define expected patterns for different API credentials
        credential_patterns = {
            "GMAIL_CLIENT_ID": r'^[0-9]+-[a-zA-Z0-9_]+\.apps\.googleusercontent\.com$',
            "GMAIL_CLIENT_SECRET": r'^[a-zA-Z0-9_-]{24,}$',
            "GMAIL_REFRESH_TOKEN": r'^[0-9]/[A-Za-z0-9_-]{30,}$',
            "SLACK_BOT_TOKEN": r'^xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9]+$',
            "SLACK_USER_TOKEN": r'^xoxp-[0-9]+-[0-9]+-[a-zA-Z0-9]+$',
            "SLACK_WORKSPACE_ID": r'^[A-Z0-9]{9}$',
            "GITHUB_TOKEN": r'^gh[opsu]_[a-zA-Z0-9]{36}$',
            "NOTION_TOKEN": r'^(secret|ntn)_[a-zA-Z0-9]{32,}$',
            "NOTION_DATABASE_ID": r'^[0-9a-f]{32}$',
            "GOOGLE_CALENDAR_CLIENT_ID": r'^[0-9]+-[a-zA-Z0-9_]+\.apps\.googleusercontent\.com$',
            "GOOGLE_CALENDAR_CLIENT_SECRET": r'^[a-zA-Z0-9_-]{24,}$',
            "GOOGLE_CALENDAR_REFRESH_TOKEN": r'^[0-9]/[A-Za-z0-9_-]{30,}$',
        }
        
        for var_name, pattern in credential_patterns.items():
            value = os.getenv(var_name)
            if value:
                if not re.match(pattern, value):
                    issues.append(f"{var_name} format appears invalid")
                placeholder_markers = ("your_", "-your-", "_here")
                if any(marker in value for marker in placeholder_markers):
                    issues.append(f"{var_name} still uses the template placeholder value")
            # Note: We don't report missing variables here as that's handled in validate_environment_variables
        
        # Additional checks for OAuth credentials
        gmail_client_id = os.getenv("GMAIL_CLIENT_ID")
        gmail_client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        
        if gmail_client_id and gmail_client_secret:
            if len(gmail_client_secret) < 20:
                issues.append("GMAIL_CLIENT_SECRET appears too short")
        
        if issues:
            return ValidationResult(
                False,
                "API authentication format validation failed",
                {"issues": issues}
            )
        
        return ValidationResult(True, "API authentication formats are valid")
    
    def validate_config_consistency(self) -> ValidationResult:
        """Validate consistency between different configuration files."""
        issues = []
        
        # Check settings.json
        settings_path = self.config_dir / "settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Validate settings structure
                if not isinstance(settings, dict):
                    issues.append("settings.json should contain a JSON object")
                else:
                    # Check for expected sections based on current schema
                    expected_sections = {
                        "application": dict,
                        "data_collection": dict,
                        "notion_integration": dict,
                        "error_handling": dict,
                        "logging": dict,
                        "security": dict,
                        "desktop": dict
                    }
                    for section, expected_type in expected_sections.items():
                        if section not in settings:
                            issues.append(f"settings.json missing '{section}' section")
                        elif not isinstance(settings.get(section), expected_type):
                            issues.append(f"settings.json section '{section}' should be {expected_type.__name__}")

                    desktop_config = settings.get('desktop', {}) if isinstance(settings, dict) else {}
                    if isinstance(desktop_config, dict):
                        claude_path = desktop_config.get('claude_path')
                        if not claude_path:
                            issues.append("settings.json desktop.claude_path must be set to the Claude Desktop executable")
                        elif '<username>' in claude_path:
                            issues.append("settings.json desktop.claude_path still contains the <username> placeholder")
                        auto_refresh = desktop_config.get('auto_refresh_google_tokens')
                        if auto_refresh is not None and not isinstance(auto_refresh, bool):
                            issues.append("settings.json desktop.auto_refresh_google_tokens should be true or false")
                    else:
                        issues.append("settings.json desktop section must be an object")
                
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON in settings.json: {str(e)}")
            except Exception as e:
                issues.append(f"Error reading settings.json: {str(e)}")
        
        # Check .gitignore contains .env
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    gitignore_content = f.read()
                
                if ".env" not in gitignore_content:
                    issues.append(".gitignore should include .env to protect credentials")
                
            except Exception as e:
                issues.append(f"Error reading .gitignore: {str(e)}")
        
        if issues:
            return ValidationResult(
                False,
                "Configuration consistency validation failed",
                {"issues": issues}
            )
        
        return ValidationResult(True, "Configuration consistency is valid")
    
    def generate_report(self) -> str:
        """Generate a detailed validation report."""
        report = []
        report.append("Configuration Validation Report")
        report.append("=" * 40)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Project: {self.project_root}")
        report.append("")
        
        passed = sum(1 for r in self.results if r.is_valid)
        total = len(self.results)
        
        report.append(f"Summary: {passed}/{total} checks passed")
        report.append("")
        
        for i, result in enumerate(self.results, 1):
            status = "$2705 PASS" if result.is_valid else "$274C FAIL"
            report.append(f"{i}. {status}: {result.message}")
            
            if result.details:
                for key, value in result.details.items():
                    if isinstance(value, list):
                        report.append(f"   {key}:")
                        for item in value:
                            report.append(f"     - {item}")
                    else:
                        report.append(f"   {key}: {value}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point for the validation script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Task Collection System configuration")
    parser.add_argument("--project-root", type=Path, help="Project root directory")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--quiet", action="store_true", help="Suppress output except errors")
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = ConfigValidator(args.project_root)
    
    # Run validation
    if not args.quiet:
        is_valid = validator.validate_all()
    else:
        # Run validation silently
        try:
            is_valid = True
            checks = [
                validator.validate_directory_structure,
                validator.validate_required_files,
                validator.validate_mcp_config,
                validator.validate_environment_variables,
                validator.validate_api_authentication,
                validator.validate_config_consistency
            ]
            
            for check_func in checks:
                result = check_func()
                validator.results.append(result)
                if not result.is_valid:
                    is_valid = False
        except Exception as e:
            print(f"Validation error: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Generate report if requested
    if args.report:
        report = validator.generate_report()
        report_path = validator.project_root / "validation_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        if not args.quiet:
            print(f"\n$D83D$DCC4 Detailed report saved to: {report_path}")
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
