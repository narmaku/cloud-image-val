import pytest


class TestsGeneric:
    def test_bash_history_is_empty(self, host):
        users = [host.user().name, 'root']

        for u in users:
            file_path = f'/home/{u}/.bash_history'
            bash_history_file = host.file(file_path)
            if bash_history_file.exists:
                file_content_length = len(bash_history_file.content_string)
                assert file_content_length == 0, f'{file_path} must be empty or nonexistent'

    def test_console_is_redirected_to_ttys0(self, host):
        assert host.file('/proc/cmdline').contains('console=ttyS0'), \
            'Serial console should be redirected to ttyS0'

    def test_crashkernel_is_enabled_rhel_6(self, host):
        if float(host.system_info.release) < 7.0:
            with host.sudo():
                host.run_test('service kdump status')
                assert not host.file('/proc/cmdline').contains('crashkernel'), \
                    'crashkernel is not required as xen kdump is  not supported on RHEL 6.x'
        else:
            pytest.skip('RHEL is 7.x or later')

    def test_crashkernel_is_enabled_rhel_7_and_above(self, host):
        product_release_version = float(host.system_info.release)

        if float(host.system_info.release) < 7.0:
            pytest.skip('RHEL is 6.x')

        if product_release_version < 9.0:
            expected_content = 'crashkernel=auto'
        elif host.system_info.arch == 'x86_64':
            expected_content = 'crashkernel=1G-4G:192M,4G-64G:256M,64G-:512M'
        else:
            expected_content = 'crashkernel=2G-:448M'

        with host.sudo(host.user().name):
            assert host.file('/proc/cmdline').contains(expected_content), \
                'crashkernel must be enabled in RHEL 8.x and above'

    def test_cpu_flags_are_correct(self, host):
        """
        BugZilla 1061348
        """
        arch = 'x86_64'
        if host.system_info.arch == arch:
            pytest.skip(f'Not applicable to {arch}')

        expected_flags = 'avx,xsave'
        with host.sudo():
            assert host.file('/proc/cpuinfo').contains(expected_flags), \
                f'Expected CPU flags "{expected_flags}" not set'

    def test_rhgb_quiet_not_present_in_cmdline(self, host):
        """
        BugZilla 1122300
        """
        rhgb_quiet = 'rhgb,quiet'
        with host.sudo():
            assert not host.file('/proc/cmdline').contains(rhgb_quiet), \
                f'{rhgb_quiet} must not be present in cmdline'

    def test_numa_settings(self, host):
        with host.sudo():
            assert host.run_test('dmesg | grep -i numa'), \
                'There is no NUMA information available'

            lscpu_numa_nodes = host.check_output("lscpu | grep -i 'NUMA node(s)' | awk -F' ' '{print $NF}'")
            dmesg_numa_nodes = host.check_output("dmesg | grep -i 'No NUMA'|wc -l")

            if int(lscpu_numa_nodes) > 1:
                assert dmesg_numa_nodes > 1, \
                    f'NUMA seems to be disabled, when it should be enabled (NUMA nodes: {lscpu_numa_nodes})'


class TestsCloudInit:
    def test_growpart_is_present_in_config(self, host):
        """
        BugZilla 966888
        """
        assert host.file('/etc/cloud/cloud.cfg').contains('- growpart'), \
            'growpart must be present in cloud_init_modules'

    def test_wheel_group_not_set_to_default_user(self, host):
        """
        BugZilla 1549638
        """
        assert host.file('/etc/cloud/cloud.cfg').contains('wheel'), \
            'wheel should not be configured as default_user group'


class TestsNetworking:
    def test_dns_resolving_works(self, host):
        host.run_test('ping -c 5 google-public-dns-a.google.com')


class TestsSecurity:
    def test_firewalld_is_disabled(self, host):
        product_version = 7.0
        if float(host.system_info.release) < product_version:
            for s in ['iptables', 'ip6tables']:
                assert not host.service(s).is_enabled, \
                    f'{s} service should be disabled in RHEL below {product_version}'
        else:
            assert not host.package('firewalld').is_installed, \
                f'firewalld should not be installed in cloud images for RHEL {product_version} and above'
