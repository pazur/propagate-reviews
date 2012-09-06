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
            if not commit.has_current_parent:
                commit.get_parent().patchsets[-1].get_commander(git_commander).checkout()
                last_patchset.cherry_pick()
                commit.get_branch().get_commander(git_commander).push_for()

if __name__ == '__main__':
    main()