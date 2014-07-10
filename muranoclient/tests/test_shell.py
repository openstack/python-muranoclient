#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import re
import six
import sys

import fixtures
import mock
from testtools import matchers

from muranoclient.openstack.common.apiclient import exceptions
import muranoclient.shell
from muranoclient.tests import base

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'fixture_data'))
RESULT_PACKAGE = os.path.join(FIXTURE_DIR, 'test-app.zip')

FAKE_ENV = {'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where'}

FAKE_ENV2 = {'OS_USERNAME': 'username',
             'OS_PASSWORD': 'password',
             'OS_TENANT_ID': 'tenant_id',
             'OS_AUTH_URL': 'http://no.where'}


class ShellTest(base.TestCaseShell):

    def make_env(self, exclude=None, fake_env=FAKE_ENV):
        env = dict((k, v) for k, v in fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    def setUp(self):
        super(ShellTest, self).setUp()
        self.useFixture(fixtures.MonkeyPatch(
            'keystoneclient.v2_0.client.Client', mock.MagicMock))

    def shell(self, argstr, exitcodes=(0,)):
        orig = sys.stdout
        orig_stderr = sys.stderr
        try:
            sys.stdout = six.StringIO()
            sys.stderr = six.StringIO()
            _shell = muranoclient.shell.MuranoShell()
            _shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertIn(exc_value.code, exitcodes)
        finally:
            stdout = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig
            stderr = sys.stderr.getvalue()
            sys.stderr.close()
            sys.stderr = orig_stderr
        return (stdout, stderr)

    def test_help_unknown_command(self):
        self.assertRaises(exceptions.CommandError, self.shell, 'help foofoo')

    def test_help(self):
        required = [
            '.*?^usage: murano',
            '.*?^\s+package-create\s+Create an application package.',
            '.*?^See "murano help COMMAND" for help on a specific command',
        ]
        stdout, stderr = self.shell('help')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_on_subcommand(self):
        required = [
            '.*?^usage: murano package-create',
            '.*?^Create an application package.',
        ]
        stdout, stderr = self.shell('help package-create')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_no_options(self):
        required = [
            '.*?^usage: murano',
            '.*?^\s+package-create\s+Create an application package',
            '.*?^See "murano help COMMAND" for help on a specific command',
        ]
        stdout, stderr = self.shell('')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_no_username(self):
        required = ('You must provide a username via either --os-username or '
                    'env[OS_USERNAME] or a token via --os-auth-token or '
                    'env[OS_AUTH_TOKEN]',)
        self.make_env(exclude='OS_USERNAME')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_tenant_name(self):
        required = ('You must provide a tenant name '
                    'or tenant id via --os-tenant-name, '
                    '--os-tenant-id, env[OS_TENANT_NAME] '
                    'or env[OS_TENANT_ID]',)
        self.make_env(exclude='OS_TENANT_NAME')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_tenant_id(self):
        required = ('You must provide a tenant name '
                    'or tenant id via --os-tenant-name, '
                    '--os-tenant-id, env[OS_TENANT_NAME] '
                    'or env[OS_TENANT_ID]',)
        self.make_env(exclude='OS_TENANT_ID', fake_env=FAKE_ENV2)
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_auth_url(self):
        required = ('You must provide an auth url'
                    ' via either --os-auth-url or via env[OS_AUTH_URL]',)
        self.make_env(exclude='OS_AUTH_URL')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_create_hot_based_package(self):
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.v1.client.Client', mock.MagicMock))
        heat_template = os.path.join(FIXTURE_DIR, 'heat-template.yaml')
        logo = os.path.join(FIXTURE_DIR, 'logo.png')
        self.make_env()
        stdout, stderr = self.shell(
            "package-create  --template={0} "
            "--output={1} -l={2}".format(heat_template, RESULT_PACKAGE, logo))

        matchers.MatchesRegex((stdout + stderr),
                              "Application package "
                              "is available at {0}".format(RESULT_PACKAGE))

    def test_create_mpl_package(self):
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.v1.client.Client', mock.MagicMock))
        classes_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Classes')
        resources_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Resources')
        ui = os.path.join(FIXTURE_DIR, 'test-app', 'ui.yaml')
        self.make_env()
        stdout, stderr = self.shell(
            "package-create  -c={0} -r={1} -u={2} -o={3}".format(
                classes_dir, resources_dir, ui, RESULT_PACKAGE))
        matchers.MatchesRegex((stdout + stderr),
                              "Application package "
                              "is available at {0}".format(RESULT_PACKAGE))
