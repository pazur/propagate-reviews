from gerrit import Commit, Patchset, query_open_commits
import os

def main():
    os.chdir("tmp")
    commits = list(query_open_commits())
    commits.sort(key=lambda commit: commit.number)
    for commit in commits:
        commit = commit.get()
        last_patchset = commit.patchsets[-1]
        if last_patchset.review == 2:
            if not commit.has_current_parent:
                commit.get_parent().patchsets[-1].checkout()
                last_patchset.cherry_pick()
                commit.get_branch().push_for()

if __name__ == '__main__':
    main()