from gerrit import Commit, Patchset, query_open_commits, GitCommander
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']


def main():
    git_commander = GitCommander(SERVER_URL)
    os.chdir("tmp")
    commits = list(query_open_commits())
    commits.sort(key=lambda commit: commit.number)
    for commit in commits:
        commit = commit.get()
        last_patchset = commit.patchsets[-1]
        if last_patchset.review == 2:
            cherrypick_target = None
            parent = commit.get_parent()
            if not commit.has_current_parent or parent.is_merged():
                last_patchset.get_commander(git_commander).checkout()
                last_patchset_parent_id = git_commander.get_id_of_commit_from_history(1)
                parent.patchsets[-1].get_commander(git_commander).checkout()
                branch_commander = commit.get_branch().get_commander(git_commander)
                if parent.is_merged():
                    branch_commander.checkout()
                current_commit_id = git_commander.get_current_commit_id()
                if last_patchset_parent_id != current_commit_id:
                    last_patchset.cherry_pick()
                    branch_commander.push_for()

if __name__ == '__main__':
    main()