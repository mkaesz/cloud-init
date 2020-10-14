# Author: Marc-Steffen Kaesz <mskaesz@googlemail.com>
#
# This file is part of cloud-init. See LICENSE file for license information.
#
"""Upcloud Cloud API Documentation.
   https://developers.upcloud.com/"""

from cloudinit import log as logging
from cloudinit import net as cloudnet
from cloudinit import sources
from cloudinit import util

import cloudinit.sources.helpers.upcloud as uc_helper

LOG = logging.getLogger(__name__)

BASE_URL_V1 = 'http://169.254.169.254/metadata/v1'

BUILTIN_DS_CONFIG = {
    'metadata_url': BASE_URL_V1 + '.json',
    'userdata_url': BASE_URL_V1 + '/user_data',
}

MD_RETRIES = 60
MD_TIMEOUT = 2
MD_WAIT_RETRY = 2


class DataSourceUpCloud(sources.DataSource):

    dsname = 'UpCloud'

    def __init__(self, sys_cfg, distro, paths):
        sources.DataSource.__init__(self, sys_cfg, distro, paths)
        self.distro = distro
        self.metadata = dict()
        self.ds_cfg = util.mergemanydict([
            util.get_cfg_by_path(sys_cfg, ["datasource", "UpCloud"], {}),
            BUILTIN_DS_CONFIG])
        self.metadata_address = self.ds_cfg['metadata_url']
        self.userdata_address = self.ds_cfg['userdata_url']
        self.retries = self.ds_cfg.get('retries', MD_RETRIES)
        self.timeout = self.ds_cfg.get('timeout', MD_TIMEOUT)
        self.wait_retry = self.ds_cfg.get('wait_retry', MD_WAIT_RETRY)
        self.dsmode = sources.DSMODE_NETWORK

    def get_data(self):
        if not on_upcloud():
            return False
        md = uc_helper.read_metadata(
            self.metadata_address, timeout=self.timeout,
            sec_between=self.wait_retry, retries=self.retries)
        ud = uc_helper.read_userdata(
            self.userdata_address, timeout=self.timeout,
            sec_between=self.wait_retry, retries=self.retries)

        self.userdata_raw = ud
        self.metadata_full = md

        self.metadata['instance-id'] = md['instance_id']
        self.metadata['local-hostname'] = md['hostname']
        """self.metadata['network-config'] = md.get('network-config', None)"""
        self.metadata['public-keys'] = md.get('public_keys', None)
        self.vendordata_raw = md.get("vendor_data", None)

        return True

    @property
    def network_config(self):
        """Configure the networking. This needs to be done each boot, since
           the IP information may have changed due to snapshot and/or
           migration.
        """

        if self._network_config:
            return self._network_config

        _net_config = self.metadata['network-config']
        if not _net_config:
            raise Exception("Unable to get meta-data from server....")

        self._network_config = _net_config

        return self._network_config


def on_upcloud():
    return util.read_dmi_data('system-manufacturer') == "UpCloud"


# Used to match classes to dependencies
datasources = [
    (DataSourceUpCloud, (sources.DEP_FILESYSTEM, sources.DEP_NETWORK)),
]


# Return a list of data sources that match this set of dependencies
def get_datasource_list(depends):
    return sources.list_from_depends(depends, datasources)

# vi: ts=4 expandtab

