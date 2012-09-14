from gerrit import Commit, Patchset, query_open_commits, GitCommander
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']

def main():
    git_commander = GitCommander(SERVER_URL)
    os.chdir("tmp")
    for commit in get_open_commits_with_review_2():
        last_patchset = commit.patchsets[-1]
        parent = get_commit_parent(commit)
        if should_cherry_pick(commit, parent):
            last_patchset.get_commander(git_commander).checkout()
            last_patchset_parent_id = git_commander.get_id_of_commit_from_history(1)
            branch_commander = commit.get_branch().get_commander(git_commander)
            checkout_parent_or_branch(branch_commander, parent, git_commander)
            current_commit_id = git_commander.get_current_commit_id()
            if last_patchset_parent_id != current_commit_id:
                last_patchset.cherry_pick()
                branch_commander.push_for()

def get_open_commits_with_review_2():
    commits = get_open_commits()
    for commit in commits:
        commit = commit.get()
        last_patchset = commit.patchsets[-1]
        if last_patchset.review == 2:
            yield commit

def get_open_commits():
    commits = list(query_open_commits())
    commits.sort(key=lambda commit: commit.number)
    return commits

def get_commit_parent(commit):
    return commit.parent_id and commit.get_parent()

def should_cherry_pick(commit, parent):
    return not commit.has_current_parent or not parent or parent.is_merged()

def checkout_parent_or_branch(branch_commander, parent, git_commander):
    if not parent or parent.is_merged():
        branch_commander.checkout()
    else:
        parent.patchsets[-1].get_commander(git_commander).checkout()

if __name__ == '__main__':
    main()
