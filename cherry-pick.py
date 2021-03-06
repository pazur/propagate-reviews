from gerrit import Commit, CherryPickError, Patchset, query_open_commits, GitCommander
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']
GERRIT_USER_NAME = os.environ['GERRIT_USER_NAME']

def main():
    git_commander = GitCommander(SERVER_URL)
    os.chdir("tmp")
    for commit in get_open_commits_with_appropriate_approval():
        last_patchset = commit.patchsets[-1]
        parent = get_commit_parent(commit)
        if should_cherry_pick(commit, parent):
            last_patchset.get_commander(git_commander).checkout()
            last_patchset_parent_id = git_commander.get_id_of_commit_from_history(1)
            branch_commander = commit.get_branch().get_commander(git_commander)
            checkout_parent_or_branch(branch_commander, parent, git_commander)
            current_commit_id = git_commander.get_current_commit_id()
            if last_patchset_parent_id != current_commit_id:
                do_cherry_pick(commit, branch_commander)
        elif parent and parent.is_abandoned():
            ancestor = get_first_not_abandoned_ancestor(commit)
            branch_commander = commit.get_branch().get_commander(git_commander)
            checkout_parent_or_branch(branch_commander, ancestor, git_commander)
            do_cherry_pick(commit, branch_commander)

def get_open_commits_with_appropriate_approval():
    commits = get_open_commits()
    for commit in commits:
        commit = commit.get()
        last_patchset = commit.patchsets[-1]
        if (last_patchset.review == 2 or
            last_patchset.get_review_value_for_user(GERRIT_USER_NAME) == -1 or
            last_patchset.get_verify_value_for_user(GERRIT_USER_NAME) == -1):
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

def get_first_not_abandoned_ancestor(commit):
    while commit.parent_id:
        parent = commit.get_parent()
        if not parent.is_abandoned():
            return parent
        commit = parent
    return None

def do_cherry_pick(commit, branch_commander):
    last_patchset = commit.patchsets[-1]
    try:
        last_patchset.cherry_pick()
    except CherryPickError:
        if last_patchset.get_verify_value_for_user(GERRIT_USER_NAME) != -1:
            commit.verify(-1, "Can't cherry-pick on parent")
    else:
        branch_commander.push_for()

if __name__ == '__main__':
    main()
