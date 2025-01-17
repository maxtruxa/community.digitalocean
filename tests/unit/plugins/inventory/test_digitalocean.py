# Copyright (c) 2021 Ansible Project
# GNGeneral Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
from subprocess import CompletedProcess

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.inventory.data import InventoryData
from ansible.template import Templar
from ansible.parsing.dataloader import DataLoader
import ansible_collections.community.digitalocean.plugins.inventory.digitalocean as module_under_test
from ansible_collections.community.digitalocean.plugins.inventory.digitalocean import InventoryModule


@pytest.fixture()
def inventory():
    r = InventoryModule()
    r.inventory = InventoryData()
    r.templar = Templar(loader=DataLoader())
    return r


def test_verify_file_bad_config(inventory):
    assert inventory.verify_file('digitalocean_foobar.yml') is False


def get_payload():
    return [
        {
            "id": 3164444,
            "name": "foo",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "locked": False,
            "status": "active",
            "kernel": {
                "id": 2233,
                "name": "Ubuntu 14.04 x64 vmlinuz-3.13.0-37-generic",
                "version": "3.13.0-37-generic"
            },
            "image": {
                "id": 6918990,
                "name": "14.04 x64",
                "distribution": "Ubuntu",
                "slug": "ubuntu-16-04-x64",
            },
            "size_slug": "s-1vcpu-1gb",
            "networks": {
                "v4": [
                    {
                        "ip_address": "104.236.32.182",
                        "netmask": "255.255.192.0",
                        "gateway": "104.236.0.1",
                        "type": "public"
                    }
                ],
                "v6": [
                    {
                        "ip_address": "2604:A880:0800:0010:0000:0000:02DD:4001",
                        "netmask": 64,
                        "gateway": "2604:A880:0800:0010:0000:0000:0000:0001",
                        "type": "public"
                    }
                ]
            },
            "region": {
                "name": "New York 3",
                "slug": "nyc3",
            },
            "tags": [

            ],
            "vpc_uuid": "f9b0769c-e118-42fb-a0c4-fed15ef69662"
        },
        {
            "id": 3164445,
            "name": "bar",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "locked": False,
            "status": "active",
            "kernel": {
                "id": 2233,
                "name": "Ubuntu 14.04 x64 vmlinuz-3.13.0-37-generic",
                "version": "3.13.0-37-generic"
            },
            "image": {
                "id": 6918990,
                "name": "14.04 x64",
                "distribution": "Ubuntu",
                "slug": "ubuntu-16-04-x64",
            },
            "size_slug": "s-1vcpu-1gb",
            "networks": {
                "v4": [
                    {
                        "ip_address": "104.236.32.185",
                        "netmask": "255.255.192.0",
                        "gateway": "104.236.0.1",
                        "type": "public"
                    }
                ],
                "v6": [
                    {
                        "ip_address": "2604:A880:0800:0010:0000:0000:02DD:4004",
                        "netmask": 64,
                        "gateway": "2604:A880:0800:0010:0000:0000:0000:0001",
                        "type": "public"
                    }
                ]
            },
            "region": {
                "name": "Frankfurt 1",
                "slug": "fra1",
            },
            "tags": [

            ],
            "vpc_uuid": "f9b0769c-e118-42fb-a0c4-fed15ef69662"
        }
    ]


def get_option(option):
    options = {
        'attributes': ['id', 'size_slug'],
        'var_prefix': 'do_',
        'strict': False,
    }
    return options.get(option)


def test_populate_hostvars(inventory, mocker):
    inventory._get_payload = mocker.MagicMock(side_effect=get_payload)
    inventory.get_option = mocker.MagicMock(side_effect=get_option)
    inventory._populate()

    host_foo = inventory.inventory.get_host('foo')
    host_bar = inventory.inventory.get_host('bar')

    assert host_foo.vars['do_id'] == 3164444
    assert host_bar.vars['do_size_slug'] == "s-1vcpu-1gb"


def get_option_with_templated_api_token(option):
    options = {
        # "random_choice" with just a single input always returns the same result.
        'api_token': '{{ lookup("random_choice", "my-do-token") }}',
        'pagination': 100,
    }
    return options.get(option)


def test_get_payload_with_templated_api_token(inventory, mocker):
    inventory.get_option = mocker.MagicMock(side_effect=get_option_with_templated_api_token)

    mocker.patch(module_under_test.__name__ + '.Request')
    RequestMock = module_under_test.Request

    req_instance = RequestMock.return_value
    req_instance.get.return_value.read.return_value = '{"droplets": []}'

    inventory._get_payload()

    init_headers = RequestMock.call_args.kwargs['headers']
    assert init_headers['Authorization'] == 'Bearer my-do-token'


def get_option_with_filters(option):
    options = {
        'attributes': ['id', 'size_slug'],
        'var_prefix': 'do_',
        'strict': False,
        'filters': [
            'region.slug == "fra1"',
        ],
    }
    return options.get(option)


def test_populate_hostvars_with_filters(inventory, mocker):
    inventory._get_payload = mocker.MagicMock(side_effect=get_payload)
    inventory.get_option = mocker.MagicMock(side_effect=get_option_with_filters)
    inventory._populate()

    host_foo = inventory.inventory.get_host('foo')
    host_bar = inventory.inventory.get_host('bar')

    assert host_foo is None
    assert host_bar.vars['do_size_slug'] == "s-1vcpu-1gb"


def get_variables():
    return {
        'region': {
            'slug': 'fra1',
        },
        'tags': ['something'],
    }


def test_passes_filters_accept_empty(inventory, mocker):
    filters = []
    variables = get_variables()
    assert inventory._passes_filters(filters, variables, 'foo')


def test_passes_filters_accept(inventory, mocker):
    filters = ['region.slug == "fra1"']
    variables = get_variables()
    assert inventory._passes_filters(filters, variables, 'foo')


def test_passes_filters_reject(inventory, mocker):
    filters = ['region.slug == "nyc3"']
    variables = get_variables()
    assert not inventory._passes_filters(filters, variables, 'foo')


def test_passes_filters_reject_any(inventory, mocker):
    filters = [
        'region.slug == "fra1"',  # accept
        '"nope" in tags',         # reject
    ]
    variables = get_variables()
    assert not inventory._passes_filters(filters, variables, 'foo')


def test_passes_filters_invalid_filters(inventory, mocker):
    filters = ['not a valid filter']
    variables = get_variables()
    assert not inventory._passes_filters(filters, variables, 'foo')


def test_passes_filters_invalid_filters_strict(inventory, mocker):
    filters = ['not a valid filter']
    variables = get_variables()
    try:
        inventory._passes_filters(filters, variables, 'foo', True)
        assert False, 'expected _passes_filters() to raise AnsibleError'
    except AnsibleError as e:
        pass
