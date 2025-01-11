# PR Conflict Resolver

An automated tool for handling GitHub Pull Request conflicts, merging with the target branch, and recreating PRs while preserving original attribution and information.

## Features

- Automatically downloads repository and PR branch
- Merges with target branch (configurable, defaults to 'develop')
- Handles merge conflicts through:
  - Automatic resolution for simple conflicts
  - Interactive resolution for complex conflicts
  - Manual editing option for full control
- Creates new branch with fixes
- Creates new PR with:
  - Original PR title and description
  - Attribution to original author
  - Original labels
  - Clear indication of repost
- Maintains clean git history
- Detailed progress logging

## Prerequisites

- Python 3.7+
- Git installed and configured
- GitHub personal access token with appropriate permissions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/xR0am/pr-conflict-resolver.git
cd pr-conflict-resolver
```

2. Install required packages:
```bash
pip install PyGithub gitpython requests
```

3. Set up environment variables:
```bash
export GITHUB_TOKEN='your_github_token'
export REPO_OWNER='owner_name'
export REPO_NAME='repo_name'
export BASE_BRANCH='target_branch'  # Optional, defaults to 'develop'
```

## Usage

### Basic Usage

```bash
python pr_manager.py <pr_number>
```

### Command Line Options

```bash
# For interactive mode (default)
python pr_manager.py <pr_number> --interactive

# For automatic mode only
python pr_manager.py <pr_number> --no-interactive
```

### Process Output

The script provides detailed progress information during execution:
- Shows which operations are being performed
- Reports conflict detection and resolution progress
- Indicates which target branch is being used
- Displays clear error messages if something goes wrong

### Conflict Resolution Modes

1. **Automatic Resolution**:
   - Empty vs Non-empty: Uses the non-empty changes
   - Both sides have changes: Combines both changes sequentially

2. **Interactive Resolution**:
   When automatic resolution fails, you can:
   - Keep current changes
   - Keep incoming changes
   - Keep both changes
   - Edit the file manually

3. **Manual Fallback**:
   - For complex conflicts that can't be resolved automatically
   - Provides full control over the final content

## Examples

```bash
# Using default target branch (develop)
export GITHUB_TOKEN='ghp_your_token_here'
export REPO_OWNER='myorg'
export REPO_NAME='myproject'
python pr_manager.py 123

# Using custom target branch (main)
export GITHUB_TOKEN='ghp_your_token_here'
export REPO_OWNER='myorg'
export REPO_NAME='myproject'
export BASE_BRANCH='main'
python pr_manager.py 123
```

## Error Handling

The script includes comprehensive error handling for:
- Repository access issues
- Merge conflicts
- Network problems
- Invalid PR numbers
- Authentication failures
- Multiple branch detection

The script will attempt to:
1. Use origin/{branch} first
2. Fall back to source/{branch} if origin/{branch} is not available
3. Provide clear error messages if neither is accessible

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

Created by xR0am for handling PR conflicts and maintaining clean repository history.
