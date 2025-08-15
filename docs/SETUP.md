# Setup Instructions

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10/11, macOS 10.15+, or Ubuntu 18.04+
- **Memory**: Minimum 4GB RAM recommended
- **Storage**: At least 1GB free space for dependencies and cache

### AWS Account Requirements
- **AWS Account**: Active AWS account with billing enabled
- **Bedrock Access**: Access to AWS Bedrock service in your region
- **IAM Permissions**: Appropriate permissions for Bedrock runtime access

## Step 1: Environment Setup

### Install Python
If you don't have Python installed:

**Windows:**
```powershell
# Download from python.org or use chocolatey
choco install python
```

**macOS:**
```bash
# Using Homebrew
brew install python
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

### Verify Installation
```bash
python --version  # Should show 3.8 or higher
pip --version     # Should show pip version
```

## Step 2: AWS Configuration

### Install AWS CLI
```bash
# Windows
choco install awscli

# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Configure AWS Credentials
```bash
aws configure
```

When prompted, enter:
- **AWS Access Key ID**: Your AWS access key
- **AWS Secret Access Key**: Your AWS secret key
- **Default region name**: us-east-1 (recommended for Bedrock)
- **Default output format**: json

### Verify AWS Configuration
```bash
# Test AWS credentials
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

## Step 3: Project Setup

### Clone/Download Project
```bash
# If using git
git clone <repository-url>
cd "Cloud Configuration Translator"

# Or download and extract the project files
```

### Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv cloud-translator-env

# Activate virtual environment
# Windows
cloud-translator-env\Scripts\activate

# macOS/Linux
source cloud-translator-env/bin/activate
```

### Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

## Step 4: Configuration

### Environment Variables

The application uses environment variables for AWS authentication and configuration. These settings can be found in the `.env` file in the project root.

**Setup Instructions:**
1. Copy `.env.example` to `.env` in the project root directory
2. Edit the `.env` file and replace the placeholder values with your actual AWS credentials
3. Ensure the `.env` file is never committed to version control (it's already in `.gitignore`)

**Important**: For security reasons, the actual `.env` file with credentials is not included in the repository.

### Verify Configuration
Check that `config.json` contains valid model configurations:

```bash
# View current configuration
cat config.json

# The file should contain model ARNs and regions
```

## Step 5: Launch Application

### Start the Application
```bash
streamlit run src/app.py
```

### Access the Web Interface
1. Open your web browser
2. Navigate to `http://localhost:8501`
3. You should see the Cloud Configuration Translator interface

## Troubleshooting

### Common Issues

**1. AWS Credentials Not Found**
```
Error: Unable to locate credentials
```
Solution: Run `aws configure` and enter valid credentials

**2. Bedrock Access Denied**
```
Error: AccessDeniedException
```
Solution: Ensure your AWS account has Bedrock access enabled in your region

**3. Python Module Not Found**
```
ModuleNotFoundError: No module named 'streamlit'
```
Solution: Ensure virtual environment is activated and run `pip install -r requirements.txt`

**4. Port Already in Use**
```
Error: Port 8501 is in use
```
Solution: Use a different port: `streamlit run src/app.py --server.port 8502`

**5. Cache Directory Permissions**
```
PermissionError: [Errno 13] Permission denied: 'cache'
```
Solution: Create cache directory manually: `mkdir cache`

### AWS Bedrock Regions
Currently supported regions for AWS Bedrock:
- us-east-1 (N. Virginia) - **Recommended**
- us-west-2 (Oregon)
- eu-west-1 (Ireland)

### Performance Optimization

**For Large Files:**
- Increase system memory allocation
- Use SSD storage for cache directory
- Configure AWS CLI with appropriate region

**For Cost Optimization:**
- Use caching effectively (don't clear cache unnecessarily)
- Choose appropriate models (Claude 3 Sonnet for balance)
- Validate only when necessary

## Security Best Practices

### AWS Credentials
- Never commit AWS credentials to version control
- Use IAM roles when possible
- Rotate access keys regularly
- Use least-privilege permissions

### Local Security
- Keep your Python environment updated
- Don't share cache files containing sensitive configurations
- Use virtual environments to isolate dependencies

## Next Steps

After successful setup:
1. Try the sample configurations in `examples/input/`
2. Test translation between different cloud platforms
3. Experiment with different AI models
4. Set up cache management strategies

For usage instructions, see the main [README.md](../README.md) file.

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all prerequisites are met
3. Ensure AWS credentials are properly configured
4. Check the application logs in the Streamlit interface
