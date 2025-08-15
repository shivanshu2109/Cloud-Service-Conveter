#!/usr/bin/env python3
"""
Cloud Configuration Translator & Validator - Main Entry Point

This script serves as the main entry point for running the application
from the project root directory. It automatically handles path configuration
and launches the Streamlit application.

Usage:
    python run.py                    # Launch web interface
    python run.py --help            # Show help information
    python run.py --version         # Show version information

Author: Cloud Migration Intern Team
Version: 1.0.0
"""

import sys
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def show_help():
    """Display help information."""
    print("""
Cloud Configuration Translator & Validator

USAGE:
    python run.py [OPTIONS]

OPTIONS:
    --help, -h      Show this help message
    --version, -v   Show version information
    --dev          Run in development mode with debug output
    --port PORT    Specify custom port (default: 8501)

EXAMPLES:
    python run.py                    # Launch on default port 8501
    python run.py --port 8502       # Launch on custom port
    python run.py --dev             # Launch with debug mode

REQUIREMENTS:
    - Python 3.8+
    - AWS credentials configured
    - Required packages: streamlit, boto3, pyyaml, python-dotenv

For setup instructions, see docs/SETUP.md
For usage guide, see README.md
    """)

def show_version():
    """Display version information."""
    print("Cloud Configuration Translator & Validator v1.0.0")
    print("Built during Summer 2025 Internship")
    print("AI-Powered Multi-Cloud Infrastructure Translation System")

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ['streamlit', 'boto3', 'yaml', 'dotenv']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'yaml':
                import yaml
            elif package == 'dotenv':
                import dotenv
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"ERROR: Missing required packages: {', '.join(missing_packages)}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True

def check_aws_config():
    """Check if AWS credentials are configured."""
    try:
        import boto3
        # Try to create a client to test credentials
        client = boto3.client('sts')
        client.get_caller_identity()
        return True
    except Exception as e:
        print(f"WARNING: AWS credentials not configured properly: {e}")
        print("Please run: aws configure")
        return False

def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    # Handle command line arguments
    if '--help' in args or '-h' in args:
        show_help()
        return
    
    if '--version' in args or '-v' in args:
        show_version()
        return
    
    # Check dependencies
    print("Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    print("Dependencies check passed")
    
    # Check AWS configuration
    print("Checking AWS configuration...")
    if not check_aws_config():
        print("Warning: AWS configuration issues detected")
        print("The application may not work properly without valid AWS credentials")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    else:
        print("AWS configuration check passed")
    
    # Prepare streamlit command
    streamlit_cmd = ['streamlit', 'run', str(src_path / 'app.py')]
    
    # Handle port argument
    if '--port' in args:
        try:
            port_index = args.index('--port')
            port = args[port_index + 1]
            streamlit_cmd.extend(['--server.port', port])
        except (IndexError, ValueError):
            print("ERROR: Invalid port specification")
            sys.exit(1)
    
    # Handle dev mode
    if '--dev' in args:
        streamlit_cmd.extend(['--logger.level', 'debug'])
    
    # Launch the application
    print("Launching Cloud Configuration Translator...")
    print("Opening browser at http://localhost:8501")
    print("Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        subprocess.run(streamlit_cmd)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except FileNotFoundError:
        print("ERROR: Streamlit not found. Please install it with: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Error launching application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
