import os
import sys
import subprocess
import requests
from git import Repo
from github import Github

class PRManager:
    def __init__(self, token, repo_owner, repo_name):
        self.github = Github(token)
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.repo = self.github.get_repo(f"{repo_owner}/{repo_name}")
        
    def setup_git_config(self):
        """Configure git with token authentication"""
        subprocess.run(["git", "config", "--global", "credential.helper", "store"])
        with open(os.path.expanduser("~/.git-credentials"), "w") as f:
            f.write(f"https://{self.token}:x-oauth-basic@github.com\n")

    def clone_and_setup_repo(self, pr_number):
        """Clone repository and set up branches"""
        try:
            # Get PR information
            pr = self.repo.get_pull(pr_number)
            source_branch = pr.head.ref
            source_repo = pr.head.repo.full_name
            
            # Clone repository
            if os.path.exists("temp_repo"):
                subprocess.run(["rm", "-rf", "temp_repo"])
            
            print(f"Cloning repository {self.repo_owner}/{self.repo_name}...")
            local_repo = Repo.clone_from(
                f"https://github.com/{self.repo_owner}/{self.repo_name}.git",
                "temp_repo"
            )
            
            # Add source repository as remote if it's a fork
            if source_repo != f"{self.repo_owner}/{self.repo_name}":
                print(f"Adding source repository {source_repo} as remote...")
                local_repo.create_remote('source', f"https://github.com/{source_repo}.git")
                local_repo.remotes.source.fetch()
            
            return local_repo, pr, source_branch
        except Exception as e:
            raise Exception(f"Error setting up repository: {str(e)}")

    def merge_develop(self, local_repo):
        """Merge develop branch and handle conflicts"""
        try:
            print("Fetching all remotes...")
            local_repo.git.fetch('--all')
            
            print("Checking out origin/develop...")
            try:
                # First try to find develop in origin
                local_repo.git.checkout('-B', 'develop', 'origin/develop', '--track')
            except Exception as e:
                print(f"Could not find develop in origin: {str(e)}")
                # If that fails, try to find it in source
                try:
                    print("Trying source/develop...")
                    local_repo.git.checkout('-B', 'develop', 'source/develop', '--track')
                except Exception as e2:
                    raise Exception(f"Could not find develop branch in any remote: {str(e2)}")

            print("Pulling latest changes from develop...")
            local_repo.git.pull('origin', 'develop')
            
            print("Creating temporary branch...")
            local_repo.git.checkout('-b', 'temp_branch')
            
            try:
                print("Attempting to merge develop...")
                local_repo.git.merge('develop')
                return True
            except Exception as e:
                print("Merge conflicts detected. Attempting to resolve...")
                
                # Get list of files with conflicts
                conflict_files = [
                    item.a_path for item in local_repo.index.unmerged_blobs()
                ]
                
                print(f"Found conflicts in: {', '.join(conflict_files)}")
                
                # Try to resolve each conflict
                for file_path in conflict_files:
                    try:
                        self.handle_conflict_file(os.path.join('temp_repo', file_path))
                        # Stage the resolved file
                        local_repo.index.add([file_path])
                    except Exception as resolve_error:
                        print(f"Could not resolve conflict in {file_path}: {str(resolve_error)}")
                        # If we can't resolve a file, abort the whole process
                        local_repo.git.merge('--abort')
                        return False
                
                # If we got here, all conflicts were resolved
                local_repo.index.commit("Resolved merge conflicts automatically")
                return True
                
        except Exception as e:
            print(f"Error during merge: {str(e)}")
            if 'merge' in dir(local_repo.git):
                local_repo.git.merge('--abort')
            return False

    def handle_conflict_file(self, file_path, interactive=True):
        """Handle conflicts in a single file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Split the content into sections
            sections = content.split('<<<<<<< HEAD')
            
            resolved_content = ''
            for section in sections:
                if '=======' in section and '>>>>>>>' in section:
                    # This is a conflict section
                    current_changes = section.split('=======')[0].strip()
                    incoming_changes = section.split('=======')[1].split('>>>>>>>')[0].strip()
                    
                    # Strategy 1: If one side is empty, use the other side
                    if not current_changes:
                        resolved_content += incoming_changes + '\n'
                    elif not incoming_changes:
                        resolved_content += current_changes + '\n'
                    # Strategy 2: If both sides made additions, try to combine them
                    elif len(current_changes) > 0 and len(incoming_changes) > 0:
                        resolved_content += current_changes + '\n' + incoming_changes + '\n'
                    else:
                        # If we can't automatically resolve, try interactive mode
                        if interactive:
                            return self.interactive_resolve_conflict(file_path)
                        raise Exception(f"Unable to automatically resolve conflict in {file_path}")
                else:
                    # This is a non-conflict section
                    resolved_content += section
            
            # Write back the resolved content
            with open(file_path, 'w') as f:
                f.write(resolved_content)
                
        except Exception as e:
            raise Exception(f"Error handling conflict in {file_path}: {str(e)}")

    def create_new_pr(self, original_pr, new_branch_name):
        """Create new PR with information from original PR"""
        try:
            # Prepare PR body with attribution
            new_body = f"""
This is a reposted PR originally created by @{original_pr.user.login}

Original PR: #{original_pr.number}

---
{original_pr.body}
"""
            
            print("Creating new PR...")
            # Create new PR
            new_pr = self.repo.create_pull(
                title=f"[Repost] {original_pr.title}",
                body=new_body,
                base=original_pr.base.ref,
                head=new_branch_name,
                maintainer_can_modify=True
            )
            
            print("Copying labels...")
            # Copy labels
            for label in original_pr.labels:
                new_pr.add_to_labels(label.name)
                
            return new_pr
        except Exception as e:
            raise Exception(f"Error creating new PR: {str(e)}")

    def process_pr(self, pr_number, interactive=True):
        """Main process to handle PR conflict resolution"""
        try:
            # Initial setup
            print(f"Processing PR #{pr_number}...")
            self.setup_git_config()
            local_repo, original_pr, source_branch = self.clone_and_setup_repo(pr_number)
            
            # Create new branch name
            new_branch_name = f"pr{pr_number}_fix"
            print(f"Will create new branch: {new_branch_name}")
            
            # Checkout source branch
            print(f"Checking out source branch: {source_branch}")
            local_repo.git.checkout(source_branch)
            
            # Merge develop
            if not self.merge_develop(local_repo):
                return "Failed to merge develop branch. Manual intervention required."
            
            # Push to new branch
            print(f"Pushing to new branch: {new_branch_name}")
            local_repo.git.push('origin', f'temp_branch:{new_branch_name}')
            
            # Create new PR
            new_pr = self.create_new_pr(original_pr, new_branch_name)
            
            return f"Successfully created new PR: {new_pr.html_url}"
            
        except Exception as e:
            return f"Error processing PR: {str(e)}"
        finally:
            # Cleanup
            if os.path.exists("temp_repo"):
                subprocess.run(["rm", "-rf", "temp_repo"])

def main():
    if len(sys.argv) < 2:
        print("Usage: python pr_manager.py <pr_number> [--no-interactive]")
        sys.exit(1)
    
    # Get environment variables
    token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    if not all([token, repo_owner, repo_name]):
        print("Please set GITHUB_TOKEN, REPO_OWNER, and REPO_NAME environment variables")
        sys.exit(1)
    
    pr_number = int(sys.argv[1])
    interactive = "--no-interactive" not in sys.argv[2:] if len(sys.argv) > 2 else True
    
    pr_manager = PRManager(token, repo_owner, repo_name)
    result = pr_manager.process_pr(pr_number, interactive)
    print(result)

if __name__ == "__main__":
    main()
