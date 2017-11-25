import git
import os
import shutil
import json
import logging


class Gitapi(object):

    def __init__(self, git_config_url=None):

        self.git_config_url=git_config_url
        self.ssh_executable = os.path.join(os.getcwd(), 'ssh_exe.sh')
        os.environ['GIT_SSH_COMMAND'] = self.ssh_executable
        self._git_clone_repo()
        
        
    def _git_clone_repo(self):
        # Remove any current git repo with dashboards in the pwd
        if os.path.isdir("{0}/../dashboards".format(os.getcwd())):
            shutil.rmtree("{0}/../dashboards".format(os.getcwd()), ignore_errors=True)
        # Clone the repo
        git.Repo.clone_from(self.git_config_url,"{0}/../dashboards".format(os.getcwd()))
        self._set_repo(git.Repo("{0}/../dashboards".format(os.getcwd())))
    
    def _set_repo(self, repo=None):
        self.repo = repo

    def _git_pull(self):
        # Update the repo
        self.repo.remotes.origin.pull()

    def get_dashboards(self, profile=None):
        if not profile:
            raise TypeError

        # Update the repo
        self._git_pull()

        try:
            # Get the dashboards
            with open("{0}/../dashboards/dashboards.json".format(os.getcwd()), 'r') as config_file:
                dashboards = json.load(config_file)
                return dashboards[profile]
        except:
            logging.error("Failed to open dashboards file pulled from git.")

