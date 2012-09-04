import json
import subprocess
from subprocess import Popen, PIPE
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']


class CommandError(Exception):
    def __init__(self, code, output=''):
        self.code = code
        self.output = output


class GitCommander(object):
    def __init__(self, server_name):
        self.server_name = server_name

    def push_for(self, project, branch):
        arguments = [
                     self._get_project_url(project),
                     self._get_push_for_destination_and_target(branch)]
        self._execute('push', arguments)

    def _get_push_for_destination_and_target(branch):
        return 'HEAD:refs/for/%s' % branch

    def fetch_ref(self, project, ref):
        arguments = [
                     self._get_project_url(project),
                     ref]
        self._execute('fetch', arguments)

    def _get_project_url(self, project_name):
        return "ssh://%s:29418/%s" % (self.server_name, project_name)

    def checkout_commit(self, commit_id):
        self._execute('checkout', [str(commit_id)])

    def _execute(self, command, args):
        bash_command_splitted = ['git', command] + args
        self._log_execution(bash_command_splitted)
        self._execute_bash_command(bash_command_splitted)

    def _execute_bash_command(self, bash_command_splitted):
        status_code = subprocess.call(bash_command_splitted)
        if status_code != 0:
            raise CommandError(status_code)

    def _log_execution(self, bash_command_splitted):
        print 'Executing %s' % (' '.join(bash_command_splitted))


class Branch(object):
    def __init__(self, name, project):
        self.name = name
        self.project = project

    def get_commander(self, git_commander):
        return BranchCommander(self, git_commander)


class BranchCommander(object):
    def __init__(self, branch, git_commander):
        self.branch
        self.git_commander = git_commander

    def push_for(self):
        self.git_commander.push_for(self.branch.project, self.branch.name)


class Commit(object):
    def __init__(self, json_data):
        self.has_current_parent = (not 'dependsOn' in json_data or
                                   json_data['dependsOn'][0]['isCurrentPatchSet'])
        if 'dependsOn' in json_data:
            self.parent_id = json_data['dependsOn'][0]['id']
        else:
            self.parent_id = None
        self.id = json_data['id']
        self.project = json_data['project']
        self.branch = json_data['branch']
        self.number = json_data['number']
        self.patchsets = []
        self.project_url = "ssh://%s:29418/%s" % (SERVER_URL, self.project)
        for patchset_data in json_data['patchSets']:
            self.patchsets.append(Patchset(patchset_data, self))

    def get_branch(self):
        return Branch(self.branch, self.project)

    def is_reviewed(self):
        return self.patchsets[-1].is_reviewed()

    def review(self, value, message):
        args = ['ssh', '-p', '29418', SERVER_URL,
               'gerrit', 'review',
               '--code-review', str(value),
               '--message', '"%s"' % message,
               str(self.patchsets[-1].commitid)]
        assert(0 == subprocess.call(args))

    def get_parent(self):
        return query_commits(self.parent_id).next()

    def get(self):
        return query_commits(self.id).next()

class Patchset(object):
    def __init__(self, json_data, parent_commit):
        self.commit = parent_commit
        self.data = json_data
        self.ref = json_data['ref']
        self.commitid = json_data['revision']
        self.review = self.interpret_review_values(self.get_review_values())

    def get_review_values(self):
        for approval in self.data.get('approvals', []):
            if approval['type'] == 'CRVW':
                yield int(approval['value'])

    def is_reviewed(self):
        return bool(list(self.get_review_values()))


    def interpret_review_values(self, values):
        values = list(values)
        if not values:
            return None
        for value in [-2, 2, -1, 1]:
            if value in values:
                return value
        raise ValueError()

    def cherry_pick(self):
        assert(0 == subprocess.call((['git', 'fetch', self.commit.project_url, self.ref])))
        assert(0 == subprocess.call(["git", "cherry-pick", self.commitid]))

    def get_commander(self, git_commander):
        return PatchsetCommander(self, git_commander)


class PatchsetCommander(object):
    def __init__(self, patchset, git_commander):
        self.patchset = patchset
        self.git_commander = git_commander

    def checkout(self):
        self.git_commander.fetch_ref(self.patchset.commit.project, self.patchset.ref)
        self.git_commander.checkout_commit(self.patchset.commitid)


def query_open_commits():
    return query_commits("is:open")

def query_commits(query):
    process = Popen(['ssh', '-p', '29418', SERVER_URL, 'gerrit', 'query',
                     query, '--all-approvals', '--dependencies', '--format', 'json'],
                    stdout=PIPE)
    os.waitpid(process.pid, 0)
    output = process.communicate()[0]
    for json_data in output.split("\n"):
        if json_data:
            data = json.loads(json_data)
            if not 'type' in data:
                yield Commit(data)
