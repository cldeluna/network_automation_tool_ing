#!/usr/bin/env python3
"""
Load network automation tools from Packet Pushers and Steinzi sources.
Idempotent — safe to re-run; existing slugs are skipped.
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Tool definitions
# Already loaded: ansible, containerlab, infrahub, jinja2, netmiko,
#                 network-automation-mcp, nornir, suzieq
# This file is idempotent — re-running skips existing slugs.
# ---------------------------------------------------------------------------

TOOLS = [
    # ── Network Source of Truth ──────────────────────────────────────────
    {
        "name": "NetBox", "slug": "netbox",
        "tool_type": "platform",
        "description": "Leading solution for modeling and documenting modern networks",
        "homepage_url": "https://netboxlabs.com",
        "repo_url": "https://github.com/netbox-community/netbox",
        "naf_functions": ["intent"],
        "business_model": "full-open-source",
        "categories": ["source-of-truth", "data-modeling"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Nautobot", "slug": "nautobot",
        "tool_type": "platform",
        "description": "Network Source of Truth and Network Automation Platform",
        "homepage_url": "https://nautobot.com",
        "repo_url": "https://github.com/nautobot/nautobot",
        "naf_functions": ["intent", "orchestration"],
        "business_model": "full-open-source",
        "categories": ["source-of-truth", "configuration-management"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Peering Manager", "slug": "peering-manager",
        "tool_type": "platform",
        "description": "BGP session management and documentation tool",
        "homepage_url": "https://peering-manager.net",
        "repo_url": "https://github.com/peering-manager/peering-manager",
        "naf_functions": ["intent"],
        "business_model": "full-open-source",
        "categories": ["source-of-truth", "routing"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "phpIPAM", "slug": "phpipam",
        "tool_type": "platform",
        "description": "Web-based IP address management with subnet tracking and VLAN/VRF management",
        "homepage_url": "https://phpipam.net",
        "repo_url": "https://github.com/phpipam/phpipam",
        "naf_functions": ["intent"],
        "business_model": "full-open-source",
        "categories": ["source-of-truth"],
        "sources": ["steinzi", "packet-pushers"],
    },
    # ── Discovery & Assurance ─────────────────────────────────────────────
    {
        "name": "IP Fabric", "slug": "ip-fabric",
        "tool_type": "platform",
        "description": "Network infrastructure visibility and analytics with multivendor support",
        "homepage_url": "https://ipfabric.io",
        "naf_functions": ["observability", "collector"],
        "business_model": "enterprise",
        "categories": ["observability"],
        "sources": ["steinzi"],
    },
    {
        "name": "Forward Networks", "slug": "forward-networks",
        "tool_type": "platform",
        "description": "Digital twin technology for network assurance and verification",
        "homepage_url": "https://forwardnetworks.com",
        "naf_functions": ["observability"],
        "business_model": "enterprise",
        "categories": ["observability", "testing"],
        "sources": ["steinzi"],
    },
    {
        "name": "Netdisco", "slug": "netdisco",
        "tool_type": "platform",
        "description": "Web-based network management tool for IP/MAC data collection",
        "homepage_url": "https://netdisco.org",
        "naf_functions": ["collector", "observability"],
        "business_model": "full-open-source",
        "categories": ["monitoring", "observability"],
        "sources": ["steinzi", "packet-pushers"],
    },
    # ── Testing & Compliance ──────────────────────────────────────────────
    {
        "name": "Batfish", "slug": "batfish",
        "tool_type": "platform",
        "description": "Network configuration analysis and verification without live network access",
        "homepage_url": "https://batfish.org",
        "repo_url": "https://github.com/batfish/batfish",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["testing", "observability"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "ANTA", "slug": "anta",
        "tool_type": "framework",
        "description": "Arista Network Test Automation framework",
        "homepage_url": "https://anta.arista.com",
        "repo_url": "https://github.com/aristanetworks/anta",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["testing"],
        "sources": ["steinzi"],
    },
    {
        "name": "pyATS", "slug": "pyats",
        "tool_type": "framework",
        "description": "Cisco network test and automation solution",
        "homepage_url": "https://developer.cisco.com/pyats",
        "repo_url": "https://github.com/CiscoTestAutomation/pyats",
        "naf_functions": ["observability", "executor"],
        "business_model": "closed-core",
        "categories": ["testing", "scripting"],
        "sources": ["steinzi"],
    },
    {
        "name": "NUTS", "slug": "nuts",
        "tool_type": "library",
        "description": "Pytest plugin for YAML-based network unit testing",
        "homepage_url": "https://nuts.readthedocs.io",
        "repo_url": "https://github.com/network-unit-testing-system/nuts",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["testing"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Robot Framework", "slug": "robot-framework",
        "tool_type": "framework",
        "description": "Generic automation framework for acceptance testing and RPA",
        "homepage_url": "https://robotframework.org",
        "repo_url": "https://github.com/robotframework/robotframework",
        "naf_functions": ["orchestration"],
        "business_model": "full-open-source",
        "categories": ["testing", "scripting"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "JSNAPy", "slug": "jsnapy",
        "tool_type": "library",
        "description": "Captures and audits runtime snapshots of Junos devices",
        "repo_url": "https://github.com/Juniper/jsnapy",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["testing"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Netpicker", "slug": "netpicker",
        "tool_type": "platform",
        "description": "Network design compliance testing tool for configuration validation",
        "homepage_url": "https://netpicker.io",
        "naf_functions": ["observability"],
        "business_model": "enterprise",
        "categories": ["testing"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Topolograph", "slug": "topolograph",
        "tool_type": "platform",
        "description": "Web-based visualization of OSPF and IS-IS topologies",
        "repo_url": "https://github.com/Vadims06/topolograph",
        "naf_functions": ["observability", "presentation"],
        "business_model": "full-open-source",
        "categories": ["observability", "routing"],
        "sources": ["packet-pushers"],
    },
    # ── Config Backup ─────────────────────────────────────────────────────
    {
        "name": "Oxidized", "slug": "oxidized",
        "tool_type": "platform",
        "description": "Network device configuration backup supporting 90+ NOS",
        "repo_url": "https://github.com/ytti/oxidized",
        "naf_functions": ["collector"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "netcfgbu", "slug": "netcfgbu",
        "tool_type": "cli",
        "description": "Automated NOS configuration backup to version control",
        "repo_url": "https://github.com/jeremyschulman/netcfgbu",
        "naf_functions": ["collector"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Netshot", "slug": "netshot",
        "tool_type": "platform",
        "description": "Network device configuration and compliance manager",
        "homepage_url": "https://www.netfishers.onl/netshot",
        "naf_functions": ["collector", "observability"],
        "business_model": "full-open-source",
        "categories": ["configuration-management", "testing"],
        "sources": ["packet-pushers"],
    },
    # ── Monitoring & Observability ────────────────────────────────────────
    {
        "name": "LibreNMS", "slug": "librenms",
        "tool_type": "platform",
        "description": "Full-featured network monitoring system with SNMP autodiscovery",
        "homepage_url": "https://librenms.org",
        "repo_url": "https://github.com/librenms/librenms",
        "naf_functions": ["observability", "collector"],
        "business_model": "full-open-source",
        "categories": ["monitoring"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Icinga", "slug": "icinga",
        "tool_type": "platform",
        "description": "Network monitoring with availability checks and notifications",
        "homepage_url": "https://icinga.com",
        "repo_url": "https://github.com/Icinga/icinga2",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["monitoring"],
        "sources": ["steinzi"],
    },
    {
        "name": "Prometheus", "slug": "prometheus",
        "tool_type": "platform",
        "description": "Systems monitoring and alerting toolkit",
        "homepage_url": "https://prometheus.io",
        "repo_url": "https://github.com/prometheus/prometheus",
        "naf_functions": ["observability", "collector"],
        "business_model": "full-open-source",
        "categories": ["monitoring", "telemetry"],
        "sources": ["steinzi"],
    },
    {
        "name": "Grafana", "slug": "grafana",
        "tool_type": "platform",
        "description": "Graphical analytics and monitoring visualization platform",
        "homepage_url": "https://grafana.com",
        "repo_url": "https://github.com/grafana/grafana",
        "naf_functions": ["observability", "presentation"],
        "business_model": "hybrid",
        "categories": ["monitoring", "observability"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Zabbix", "slug": "zabbix",
        "tool_type": "platform",
        "description": "Enterprise-class distributed monitoring solution",
        "homepage_url": "https://zabbix.com",
        "repo_url": "https://github.com/zabbix/zabbix",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["monitoring"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "eNMS", "slug": "enms",
        "tool_type": "platform",
        "description": "Vendor-agnostic NMS for workflow-based network automation",
        "homepage_url": "https://www.enms.io",
        "repo_url": "https://github.com/eNMS-automation/eNMS",
        "naf_functions": ["orchestration", "executor", "presentation"],
        "business_model": "full-open-source",
        "categories": ["configuration-management", "monitoring"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "ntopng", "slug": "ntopng",
        "tool_type": "platform",
        "description": "Web-based network traffic monitoring application",
        "homepage_url": "https://ntop.org",
        "repo_url": "https://github.com/ntop/ntopng",
        "naf_functions": ["observability"],
        "business_model": "hybrid",
        "categories": ["monitoring"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "ServiceRadar", "slug": "serviceradar",
        "tool_type": "platform",
        "description": "Distributed network monitoring with zero-trust architecture",
        "homepage_url": "https://serviceradar.cloud",
        "repo_url": "https://github.com/carverauto/serviceradar",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["monitoring"],
        "sources": ["steinzi"],
    },
    # ── Telemetry ─────────────────────────────────────────────────────────
    {
        "name": "Telegraf", "slug": "telegraf",
        "tool_type": "cli",
        "description": "Plugin-driven server agent for metrics and telemetry collection",
        "homepage_url": "https://influxdata.com/time-series-platform/telegraf",
        "repo_url": "https://github.com/influxdata/telegraf",
        "naf_functions": ["collector"],
        "business_model": "full-open-source",
        "categories": ["telemetry"],
        "sources": ["steinzi"],
    },
    {
        "name": "gNMIc", "slug": "gnmic",
        "tool_type": "cli",
        "description": "gNMI CLI client and streaming telemetry collector",
        "homepage_url": "https://gnmic.openconfig.net",
        "repo_url": "https://github.com/openconfig/gnmic",
        "naf_functions": ["collector", "executor"],
        "business_model": "full-open-source",
        "categories": ["telemetry"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "gNOIc", "slug": "gnoic",
        "tool_type": "cli",
        "description": "gNOI CLI client for certificate, file, and system management",
        "homepage_url": "https://gnoic.kmrd.dev",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["telemetry"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Akvorado", "slug": "akvorado",
        "tool_type": "platform",
        "description": "Flow collector with enrichment and ClickHouse export",
        "repo_url": "https://github.com/akvorado/akvorado",
        "naf_functions": ["collector", "observability"],
        "business_model": "full-open-source",
        "categories": ["telemetry", "monitoring"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "GoFlow2", "slug": "goflow2",
        "tool_type": "platform",
        "description": "NetFlow, IPFIX, and sFlow collector in Go",
        "repo_url": "https://github.com/netsampler/goflow2",
        "naf_functions": ["collector"],
        "business_model": "full-open-source",
        "categories": ["telemetry"],
        "sources": ["packet-pushers"],
    },
    # ── Lab & Simulation ──────────────────────────────────────────────────
    {
        "name": "GNS3", "slug": "gns3",
        "tool_type": "platform",
        "description": "Network design and testing in virtual environment with real and virtual devices",
        "homepage_url": "https://gns3.com",
        "repo_url": "https://github.com/GNS3/gns3-gui",
        "naf_functions": ["infrastructure"],
        "business_model": "full-open-source",
        "categories": ["network-simulation"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "EVE-NG", "slug": "eve-ng",
        "tool_type": "platform",
        "description": "Clientless multi-vendor network emulation software",
        "homepage_url": "https://eve-ng.net",
        "naf_functions": ["infrastructure"],
        "business_model": "freemium",
        "categories": ["network-simulation"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "netlab", "slug": "netlab",
        "tool_type": "platform",
        "description": "YAML-based network lab orchestration supporting multiple virtualization providers",
        "homepage_url": "https://netlab.tools",
        "repo_url": "https://github.com/ipspace/netlab",
        "naf_functions": ["infrastructure"],
        "business_model": "full-open-source",
        "categories": ["network-simulation"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Mininet", "slug": "mininet",
        "tool_type": "platform",
        "description": "Virtual network with real kernel, switch, and application code",
        "homepage_url": "https://mininet.org",
        "naf_functions": ["infrastructure"],
        "business_model": "full-open-source",
        "categories": ["network-simulation"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Clabernetes", "slug": "clabernetes",
        "tool_type": "platform",
        "description": "Deploy Containerlab topologies into Kubernetes clusters",
        "homepage_url": "https://containerlab.dev/manual/clabernetes",
        "naf_functions": ["infrastructure"],
        "business_model": "full-open-source",
        "categories": ["network-simulation"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "NRX", "slug": "nrx",
        "tool_type": "cli",
        "description": "Network topology exporter for lab automation tools",
        "repo_url": "https://github.com/netreplica/nrx",
        "naf_functions": ["infrastructure"],
        "business_model": "full-open-source",
        "categories": ["network-simulation"],
        "sources": ["steinzi", "packet-pushers"],
    },
    # ── Configuration Automation ──────────────────────────────────────────
    {
        "name": "Salt", "slug": "salt",
        "tool_type": "platform",
        "description": "Remote execution and configuration management platform",
        "homepage_url": "https://saltproject.io",
        "repo_url": "https://github.com/saltstack/salt",
        "naf_functions": ["orchestration", "executor"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["steinzi"],
    },
    {
        "name": "Terraform", "slug": "terraform",
        "tool_type": "framework",
        "description": "Infrastructure as code provisioning tool",
        "homepage_url": "https://terraform.io",
        "repo_url": "https://github.com/hashicorp/terraform",
        "naf_functions": ["orchestration", "executor"],
        "business_model": "hybrid",
        "categories": ["configuration-management"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "OpenTofu", "slug": "opentofu",
        "tool_type": "framework",
        "description": "Open-source infrastructure as code tool, fork of Terraform",
        "homepage_url": "https://opentofu.org",
        "repo_url": "https://github.com/opentofu/opentofu",
        "naf_functions": ["orchestration", "executor"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["steinzi"],
    },
    {
        "name": "AWX", "slug": "awx",
        "tool_type": "platform",
        "description": "Web-based Ansible automation interface with REST API and RBAC",
        "repo_url": "https://github.com/ansible/awx",
        "naf_functions": ["orchestration", "presentation"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["steinzi", "packet-pushers"],
    },
    {
        "name": "Semaphore UI", "slug": "semaphore-ui",
        "tool_type": "platform",
        "description": "Graphical interface for Ansible playbook management",
        "homepage_url": "https://semaphoreui.com",
        "repo_url": "https://github.com/ansible-semaphore/semaphore",
        "naf_functions": ["orchestration", "presentation"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["steinzi"],
    },
    {
        "name": "Arista AVD", "slug": "arista-avd",
        "tool_type": "framework",
        "description": "Arista Validated Designs automation framework built on Ansible",
        "homepage_url": "https://avd.arista.com",
        "naf_functions": ["intent", "executor"],
        "business_model": "full-open-source",
        "categories": ["configuration-management"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Aerleon", "slug": "aerleon",
        "tool_type": "platform",
        "description": "Multi-platform firewall ACL configuration generator",
        "repo_url": "https://github.com/aerleon/aerleon",
        "naf_functions": ["intent", "executor"],
        "business_model": "full-open-source",
        "categories": ["security", "configuration-management"],
        "sources": ["packet-pushers"],
    },
    # ── Scripting & Libraries ─────────────────────────────────────────────
    {
        "name": "Scrapli", "slug": "scrapli",
        "tool_type": "library",
        "description": "Fast, flexible Python SSH/Telnet library for network devices",
        "homepage_url": "https://carlmontanari.github.io/scrapli",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["scripting"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "NAPALM", "slug": "napalm",
        "tool_type": "library",
        "description": "Network Automation and Programmability Abstraction Layer with Multivendor support",
        "homepage_url": "https://napalm.readthedocs.io",
        "repo_url": "https://github.com/napalm-automation/napalm",
        "naf_functions": ["executor", "collector"],
        "business_model": "full-open-source",
        "categories": ["scripting"],
        "sources": ["manual"],
    },
    {
        "name": "netutils", "slug": "netutils",
        "tool_type": "library",
        "description": "Python utility library for common network automation tasks",
        "repo_url": "https://github.com/networktocode/netutils",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["scripting"],
        "sources": ["packet-pushers"],
    },
    # ── BGP & Routing ─────────────────────────────────────────────────────
    {
        "name": "ExaBGP", "slug": "exabgp",
        "tool_type": "platform",
        "description": "SDN BGP application for injecting routes and monitoring BGP sessions",
        "repo_url": "https://github.com/Exa-Networks/exabgp",
        "naf_functions": ["executor", "orchestration"],
        "business_model": "full-open-source",
        "categories": ["routing"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "GoBGP", "slug": "gobgp",
        "tool_type": "platform",
        "description": "BGP implementation for modern environments written in Go",
        "repo_url": "https://github.com/osrg/gobgp",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["routing"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Hyperglass", "slug": "hyperglass",
        "tool_type": "platform",
        "description": "Modern looking glass implementation for network operators",
        "homepage_url": "https://hyperglass.io",
        "repo_url": "https://github.com/thatmattlove/hyperglass",
        "naf_functions": ["presentation", "collector"],
        "business_model": "full-open-source",
        "categories": ["routing", "observability"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Alice Looking Glass", "slug": "alice-lg",
        "tool_type": "platform",
        "description": "BGP looking glass using external route server APIs",
        "repo_url": "https://github.com/alice-lg/alice-lg",
        "naf_functions": ["presentation", "observability"],
        "business_model": "full-open-source",
        "categories": ["routing", "observability"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "BGPAlerter", "slug": "bgpalerter",
        "tool_type": "platform",
        "description": "Self-configuring real-time BGP monitoring and alerting tool",
        "repo_url": "https://github.com/nttgin/BGPalerter",
        "naf_functions": ["observability", "collector"],
        "business_model": "full-open-source",
        "categories": ["routing", "monitoring"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Routinator", "slug": "routinator",
        "tool_type": "platform",
        "description": "Lightweight RPKI relying party software written in Rust",
        "homepage_url": "https://nlnetlabs.nl/projects/routing/routinator",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["routing", "security"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "FRRouting", "slug": "frrouting",
        "tool_type": "platform",
        "description": "Internet routing protocol suite for Linux and Unix",
        "homepage_url": "https://frrouting.org",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["routing"],
        "sources": ["packet-pushers"],
    },
    # ── Cloud Native Networking ───────────────────────────────────────────
    {
        "name": "Cilium", "slug": "cilium",
        "tool_type": "platform",
        "description": "Cloud native connectivity and security secured by eBPF",
        "homepage_url": "https://cilium.io",
        "naf_functions": ["executor", "observability"],
        "business_model": "full-open-source",
        "categories": ["cloud-native-networking", "security"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Calico", "slug": "calico",
        "tool_type": "platform",
        "description": "Container and VM networking and security solution",
        "homepage_url": "https://www.tigera.io/tigera-products/calico",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["cloud-native-networking"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "MetalLB", "slug": "metallb",
        "tool_type": "platform",
        "description": "Load balancer implementation for bare metal Kubernetes clusters",
        "repo_url": "https://github.com/metallb/metallb",
        "naf_functions": ["executor"],
        "business_model": "full-open-source",
        "categories": ["cloud-native-networking"],
        "sources": ["packet-pushers"],
    },
    # ── Packet Analysis ───────────────────────────────────────────────────
    {
        "name": "Scapy", "slug": "scapy",
        "tool_type": "library",
        "description": "Powerful interactive packet manipulation program and library",
        "homepage_url": "https://scapy.net",
        "repo_url": "https://github.com/secdev/scapy",
        "naf_functions": ["executor", "collector"],
        "business_model": "full-open-source",
        "categories": ["packet-analysis", "scripting"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "Wireshark", "slug": "wireshark",
        "tool_type": "platform",
        "description": "Network protocol analyzer and packet inspection tool",
        "homepage_url": "https://wireshark.org",
        "naf_functions": ["observability"],
        "business_model": "full-open-source",
        "categories": ["packet-analysis"],
        "sources": ["packet-pushers"],
    },
    {
        "name": "TCPdump", "slug": "tcpdump",
        "tool_type": "cli",
        "description": "Command-line packet analyzer and network traffic capture library",
        "homepage_url": "https://www.tcpdump.org",
        "naf_functions": ["collector"],
        "business_model": "full-open-source",
        "categories": ["packet-analysis"],
        "sources": ["packet-pushers"],
    },
]


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            # Cache source IDs
            cur.execute("SELECT slug, id FROM data_sources")
            source_ids = {row[0]: row[1] for row in cur.fetchall()}

            # Cache category IDs
            cur.execute("SELECT slug, id FROM tool_categories")
            cat_ids = {row[0]: row[1] for row in cur.fetchall()}

        inserted = 0
        skipped = 0

        for tool in TOOLS:
            # Validate sources and categories before insert
            missing_sources = [s for s in tool["sources"] if s not in source_ids]
            missing_cats = [c for c in tool["categories"] if c not in cat_ids]
            if missing_sources:
                print(f"  SKIP {tool['slug']}: unknown sources {missing_sources}")
                skipped += 1
                continue
            if missing_cats:
                print(f"  SKIP {tool['slug']}: unknown categories {missing_cats}")
                skipped += 1
                continue

            with conn.cursor() as cur:
                # Insert tool (skip if slug exists)
                cur.execute(
                    """
                    INSERT INTO tools
                        (name, slug, description, tool_type, homepage_url, repo_url,
                         license, status, naf_functions, business_model)
                    VALUES (%s, %s, %s, %s::tool_type, %s, %s, %s, 'active'::tool_status,
                            %s::naf_function[], %s::business_model)
                    ON CONFLICT (slug) DO NOTHING
                    """,
                    (
                        tool["name"],
                        tool["slug"],
                        tool.get("description"),
                        tool["tool_type"],
                        tool.get("homepage_url"),
                        tool.get("repo_url"),
                        tool.get("license"),
                        tool.get("naf_functions", []),
                        tool.get("business_model"),
                    ),
                )
                rows_affected = cur.rowcount

                # Fetch tool id (may already exist)
                cur.execute("SELECT id FROM tools WHERE slug = %s", (tool["slug"],))
                tool_id = cur.fetchone()[0]

                if rows_affected == 0:
                    skipped += 1
                    print(f"  skip  {tool['slug']} (already exists)")
                else:
                    inserted += 1
                    print(f"  +     {tool['slug']}")

                # Source map entries
                for slug in tool["sources"]:
                    cur.execute(
                        """
                        INSERT INTO tool_source_map (tool_id, source_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (tool_id, source_ids[slug]),
                    )

                # Category map entries
                for slug in tool["categories"]:
                    cur.execute(
                        """
                        INSERT INTO tool_category_map (tool_id, category_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (tool_id, cat_ids[slug]),
                    )

            conn.commit()

        print(f"\nDone: {inserted} inserted, {skipped} skipped")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
