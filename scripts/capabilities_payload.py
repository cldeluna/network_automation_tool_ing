"""
Capability payload for review.
Each tool gets one or more entries with:
  - capability:        kebab-case name for what the tool does
  - protocol_support:  which of our management-protocol enums apply
  - os_support:        free-text OS labels
  - notes:             optional context

Protocol enum values: NETCONF, RESTCONF, gNMI, gRPC, SSH, REST, SNMP, YANG, NATS, WebSocket, STDIO

Already loaded (skip):
  containerlab  → lab-topology-orchestration     [SSH, REST]
  infrahub      → source-of-truth-api            [gRPC, REST]
  netmiko       → device-config-push             [SSH]
  network-automation-mcp → ai-agent-bridge       [STDIO, REST]
  suzieq        → operational-state-collection   [SSH, REST, gNMI]
"""

CAPABILITIES = [

    # ── Original seed tools (not yet covered) ────────────────────────────
    {
        "tool_slug": "ansible",
        "entries": [
            {
                "capability": "network-device-configuration",
                "protocol_support": ["SSH", "NETCONF", "RESTCONF"],
                "os_support": ["linux", "macos"],
                "notes": "ios, nxos, eos, junos modules use SSH; netconf_config uses NETCONF",
            },
            {
                "capability": "rest-api-automation",
                "protocol_support": ["REST"],
                "os_support": ["linux", "macos"],
                "notes": "uri module + vendor REST modules (Arista eAPI, Cisco RESTCONF)",
            },
        ],
    },
    {
        "tool_slug": "jinja2",
        "entries": [
            {
                "capability": "config-template-rendering",
                "protocol_support": [],
                "os_support": ["linux", "macos", "windows"],
                "notes": "Pure Python templating — generates config text, no direct device connection",
            },
        ],
    },
    {
        "tool_slug": "nornir",
        "entries": [
            {
                "capability": "multi-device-task-execution",
                "protocol_support": ["SSH", "NETCONF", "REST"],
                "os_support": ["linux", "macos"],
                "notes": "Protocol depends on plugin: netmiko (SSH), scrapli-netconf (NETCONF), requests (REST)",
            },
        ],
    },

    # ── Source of Truth / DCIM / IPAM ────────────────────────────────────
    {
        "tool_slug": "netbox",
        "entries": [
            {
                "capability": "network-inventory-api",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST and GraphQL APIs for DCIM, IPAM, circuits, and virtualization",
            },
        ],
    },
    {
        "tool_slug": "nautobot",
        "entries": [
            {
                "capability": "network-source-of-truth-api",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST and GraphQL; extensible plugin ecosystem for automation workflows",
            },
        ],
    },
    {
        "tool_slug": "peering-manager",
        "entries": [
            {
                "capability": "bgp-session-management",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST API; can push BGP config via Napalm/Netmiko integrations",
            },
        ],
    },
    {
        "tool_slug": "phpipam",
        "entries": [
            {
                "capability": "ip-address-management",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST API for subnet, VLAN, and address management",
            },
        ],
    },

    # ── Discovery & Assurance ─────────────────────────────────────────────
    {
        "tool_slug": "ip-fabric",
        "entries": [
            {
                "capability": "network-discovery-and-assurance",
                "protocol_support": ["SSH", "SNMP", "REST", "gNMI"],
                "os_support": ["linux", "container"],
                "notes": "Discovers topology via SSH/SNMP; gNMI for streaming state; REST API for queries",
            },
        ],
    },
    {
        "tool_slug": "forward-networks",
        "entries": [
            {
                "capability": "network-digital-twin-verification",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Ingests device configs via collectors; REST API for verification queries",
            },
        ],
    },
    {
        "tool_slug": "netdisco",
        "entries": [
            {
                "capability": "network-device-discovery",
                "protocol_support": ["SNMP", "SSH"],
                "os_support": ["linux"],
                "notes": "SNMP walk for topology; SSH for supplemental data collection",
            },
        ],
    },
    {
        "tool_slug": "topolograph",
        "entries": [
            {
                "capability": "igp-topology-visualization",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Parses OSPF/IS-IS LSDB data fed via REST; no direct device connectivity",
            },
        ],
    },

    # ── Testing & Compliance ──────────────────────────────────────────────
    {
        "tool_slug": "batfish",
        "entries": [
            {
                "capability": "offline-network-configuration-analysis",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Pybatfish client uses REST; analyses device configs without connecting to devices",
            },
        ],
    },
    {
        "tool_slug": "netpicker",
        "entries": [
            {
                "capability": "network-design-compliance-testing",
                "protocol_support": ["SSH", "REST"],
                "os_support": ["linux", "container"],
                "notes": "Python-based; connects via SSH; REST API for test orchestration",
            },
        ],
    },
    {
        "tool_slug": "anta",
        "entries": [
            {
                "capability": "network-test-automation",
                "protocol_support": ["SSH", "REST", "gNMI"],
                "os_support": ["linux", "macos"],
                "notes": "Arista-focused: eAPI (REST) primary; SSH fallback; gNMI optional",
            },
        ],
    },
    {
        "tool_slug": "pyats",
        "entries": [
            {
                "capability": "network-test-and-verification",
                "protocol_support": ["SSH", "NETCONF", "REST"],
                "os_support": ["linux", "macos"],
                "notes": "Genie parsers over SSH; NETCONF and RESTCONF via yang module",
            },
        ],
    },
    {
        "tool_slug": "nuts",
        "entries": [
            {
                "capability": "network-unit-testing",
                "protocol_support": ["SSH", "REST", "gNMI"],
                "os_support": ["linux", "macos"],
                "notes": "YAML-defined tests dispatched via Nornir; protocol depends on driver",
            },
        ],
    },
    {
        "tool_slug": "robot-framework",
        "entries": [
            {
                "capability": "acceptance-test-automation",
                "protocol_support": ["SSH", "REST"],
                "os_support": ["linux", "macos", "windows"],
                "notes": "SSHLibrary for device access; RequestsLibrary for REST API testing",
            },
        ],
    },
    {
        "tool_slug": "jsnapy",
        "entries": [
            {
                "capability": "junos-state-snapshot-testing",
                "protocol_support": ["NETCONF"],
                "os_support": ["linux", "macos"],
                "notes": "Uses PyEZ NETCONF connection to Juniper devices exclusively",
            },
        ],
    },

    # ── Config Backup ─────────────────────────────────────────────────────
    {
        "tool_slug": "oxidized",
        "entries": [
            {
                "capability": "network-configuration-backup",
                "protocol_support": ["SSH", "NETCONF"],
                "os_support": ["linux", "container"],
                "notes": "SSH primary across 100+ NOS; NETCONF model for some vendors",
            },
        ],
    },
    {
        "tool_slug": "netcfgbu",
        "entries": [
            {
                "capability": "network-configuration-backup",
                "protocol_support": ["SSH"],
                "os_support": ["linux", "macos"],
                "notes": "Async SSH via asyncssh; stores configs to git",
            },
        ],
    },
    {
        "tool_slug": "netshot",
        "entries": [
            {
                "capability": "configuration-backup-and-compliance",
                "protocol_support": ["SSH", "NETCONF", "SNMP"],
                "os_support": ["linux", "container"],
                "notes": "Multi-protocol collection; compliance checks against policy rules",
            },
        ],
    },

    # ── Monitoring ────────────────────────────────────────────────────────
    {
        "tool_slug": "librenms",
        "entries": [
            {
                "capability": "network-monitoring",
                "protocol_support": ["SNMP", "REST"],
                "os_support": ["linux", "container"],
                "notes": "SNMP-primary polling; REST API for integration and automation",
            },
        ],
    },
    {
        "tool_slug": "icinga",
        "entries": [
            {
                "capability": "infrastructure-monitoring",
                "protocol_support": ["SNMP", "REST"],
                "os_support": ["linux", "container"],
                "notes": "Check plugins via SNMP; REST API for config and results",
            },
        ],
    },
    {
        "tool_slug": "prometheus",
        "entries": [
            {
                "capability": "metrics-collection-and-alerting",
                "protocol_support": ["REST", "SNMP"],
                "os_support": ["linux", "macos", "container"],
                "notes": "HTTP scrape for exporters; snmp_exporter bridges SNMP to Prometheus",
            },
        ],
    },
    {
        "tool_slug": "grafana",
        "entries": [
            {
                "capability": "metrics-visualization",
                "protocol_support": ["REST"],
                "os_support": ["linux", "macos", "windows", "container"],
                "notes": "Queries Prometheus, InfluxDB, and other sources via REST data source plugins",
            },
        ],
    },
    {
        "tool_slug": "zabbix",
        "entries": [
            {
                "capability": "network-monitoring",
                "protocol_support": ["SNMP", "REST"],
                "os_support": ["linux", "container"],
                "notes": "SNMP traps and polling; REST API for configuration and alerting",
            },
        ],
    },
    {
        "tool_slug": "enms",
        "entries": [
            {
                "capability": "workflow-based-network-automation",
                "protocol_support": ["SSH", "NETCONF", "REST"],
                "os_support": ["linux", "container"],
                "notes": "Runs Netmiko (SSH) and Napalm (NETCONF/REST) tasks in workflows",
            },
        ],
    },
    {
        "tool_slug": "ntopng",
        "entries": [
            {
                "capability": "network-traffic-analysis",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Passive traffic capture; REST API for reporting and alerting",
            },
        ],
    },
    {
        "tool_slug": "serviceradar",
        "entries": [
            {
                "capability": "distributed-network-monitoring",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST API; zero-trust agent-based collection model",
            },
        ],
    },

    # ── Telemetry ─────────────────────────────────────────────────────────
    {
        "tool_slug": "telegraf",
        "entries": [
            {
                "capability": "telemetry-and-metrics-collection",
                "protocol_support": ["gNMI", "SNMP", "REST"],
                "os_support": ["linux", "macos", "windows", "container"],
                "notes": "gnmi input plugin for streaming telemetry; snmp plugin for polling",
            },
        ],
    },
    {
        "tool_slug": "gnmic",
        "entries": [
            {
                "capability": "gnmi-telemetry-collection",
                "protocol_support": ["gNMI", "gRPC", "YANG"],
                "os_support": ["linux", "macos"],
                "notes": "Subscribe/Get/Set over gNMI; YANG path navigation; gRPC transport",
            },
        ],
    },
    {
        "tool_slug": "gnoic",
        "entries": [
            {
                "capability": "gnoi-device-management",
                "protocol_support": ["gRPC"],
                "os_support": ["linux", "macos"],
                "notes": "gNOI services over gRPC: certificate, file, OS upgrade, system",
            },
        ],
    },
    {
        "tool_slug": "akvorado",
        "entries": [
            {
                "capability": "flow-collection-and-enrichment",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Collects NetFlow v5/v9, IPFIX, sFlow; enriches with BGP; REST query API",
            },
        ],
    },
    {
        "tool_slug": "goflow2",
        "entries": [
            {
                "capability": "network-flow-collection",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Receives NetFlow, IPFIX, sFlow; Kafka/Prometheus output via REST",
            },
        ],
    },

    # ── Lab & Simulation ──────────────────────────────────────────────────
    {
        "tool_slug": "gns3",
        "entries": [
            {
                "capability": "network-emulation",
                "protocol_support": ["REST", "SSH"],
                "os_support": ["linux", "macos", "windows"],
                "notes": "GNS3 REST API for topology management; SSH/telnet for node consoles",
            },
        ],
    },
    {
        "tool_slug": "eve-ng",
        "entries": [
            {
                "capability": "network-emulation",
                "protocol_support": ["REST", "SSH"],
                "os_support": ["linux"],
                "notes": "REST API for topology lifecycle; SSH/telnet for node console access",
            },
        ],
    },
    {
        "tool_slug": "netlab",
        "entries": [
            {
                "capability": "network-lab-orchestration",
                "protocol_support": ["SSH"],
                "os_support": ["linux", "macos"],
                "notes": "Deploys topologies; post-deploy device config via Ansible (SSH)",
            },
        ],
    },
    {
        "tool_slug": "mininet",
        "entries": [
            {
                "capability": "virtual-network-emulation",
                "protocol_support": ["REST"],
                "os_support": ["linux"],
                "notes": "Python API and optional REST interface; OpenFlow for switch programming",
            },
        ],
    },
    {
        "tool_slug": "clabernetes",
        "entries": [
            {
                "capability": "kubernetes-lab-orchestration",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Kubernetes CRDs (REST) extend Containerlab topologies to k8s clusters",
            },
        ],
    },
    {
        "tool_slug": "nrx",
        "entries": [
            {
                "capability": "network-topology-export",
                "protocol_support": ["REST"],
                "os_support": ["linux", "macos"],
                "notes": "Reads topology from NetBox REST API; exports to Containerlab/draw.io",
            },
        ],
    },

    # ── Configuration Automation ──────────────────────────────────────────
    {
        "tool_slug": "salt",
        "entries": [
            {
                "capability": "remote-execution-and-configuration",
                "protocol_support": ["SSH", "REST"],
                "os_support": ["linux", "macos"],
                "notes": "Netmiko/NAPALM proxy minions for SSH/NETCONF; Salt API for REST access",
            },
        ],
    },
    {
        "tool_slug": "terraform",
        "entries": [
            {
                "capability": "infrastructure-as-code-provisioning",
                "protocol_support": ["REST"],
                "os_support": ["linux", "macos", "windows"],
                "notes": "Network providers (Cisco, Juniper, Arista, Palo Alto) via vendor REST APIs",
            },
        ],
    },
    {
        "tool_slug": "opentofu",
        "entries": [
            {
                "capability": "infrastructure-as-code-provisioning",
                "protocol_support": ["REST"],
                "os_support": ["linux", "macos", "windows"],
                "notes": "Drop-in Terraform replacement; all network providers fully compatible",
            },
        ],
    },
    {
        "tool_slug": "awx",
        "entries": [
            {
                "capability": "ansible-automation-orchestration",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST API for job scheduling; underlying playbooks use Ansible protocols",
            },
        ],
    },
    {
        "tool_slug": "semaphore-ui",
        "entries": [
            {
                "capability": "ansible-workflow-management",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "REST API; thin UI over Ansible — protocols determined by playbooks",
            },
        ],
    },
    {
        "tool_slug": "arista-avd",
        "entries": [
            {
                "capability": "data-model-driven-network-design",
                "protocol_support": ["REST", "SSH"],
                "os_support": ["linux", "macos"],
                "notes": "Generates structured configs; deploys via Arista eAPI (REST) or SSH",
            },
        ],
    },
    {
        "tool_slug": "aerleon",
        "entries": [
            {
                "capability": "firewall-acl-policy-generation",
                "protocol_support": [],
                "os_support": ["linux", "macos"],
                "notes": "Generates platform-specific ACL configs from YAML — no direct device connectivity",
            },
        ],
    },

    # ── Scripting & Libraries ─────────────────────────────────────────────
    {
        "tool_slug": "scrapli",
        "entries": [
            {
                "capability": "network-device-connectivity",
                "protocol_support": ["SSH", "NETCONF"],
                "os_support": ["linux", "macos"],
                "notes": "Async-first SSH; scrapli-netconf plugin adds NETCONF transport",
            },
        ],
    },
    {
        "tool_slug": "napalm",
        "entries": [
            {
                "capability": "multi-vendor-device-abstraction",
                "protocol_support": ["SSH", "NETCONF", "REST"],
                "os_support": ["linux", "macos"],
                "notes": "Unified API: IOS/NX-OS via SSH, JunOS via NETCONF, EOS via eAPI (REST)",
            },
        ],
    },
    {
        "tool_slug": "netutils",
        "entries": [
            {
                "capability": "network-data-utilities",
                "protocol_support": [],
                "os_support": ["linux", "macos", "windows"],
                "notes": "IP math, ACL parsing, config diff — no direct device connectivity",
            },
        ],
    },

    # ── BGP & Routing ─────────────────────────────────────────────────────
    {
        "tool_slug": "exabgp",
        "entries": [
            {
                "capability": "bgp-route-injection",
                "protocol_support": ["REST"],
                "os_support": ["linux"],
                "notes": "Peers with routers over BGP (not in enum); REST/JSON API for route injection commands",
            },
        ],
    },
    {
        "tool_slug": "gobgp",
        "entries": [
            {
                "capability": "bgp-session-management",
                "protocol_support": ["gRPC", "REST"],
                "os_support": ["linux"],
                "notes": "gRPC API for peer and route table management; REST via gobgpd API",
            },
        ],
    },
    {
        "tool_slug": "hyperglass",
        "entries": [
            {
                "capability": "bgp-looking-glass",
                "protocol_support": ["SSH", "REST"],
                "os_support": ["linux", "container"],
                "notes": "Proxies BGP queries to routers via SSH or HTTPS/REST depending on device",
            },
        ],
    },
    {
        "tool_slug": "alice-lg",
        "entries": [
            {
                "capability": "route-server-looking-glass",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Queries Bird2 and OpenBGPd route server APIs via REST",
            },
        ],
    },
    {
        "tool_slug": "bgpalerter",
        "entries": [
            {
                "capability": "bgp-prefix-monitoring",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Monitors BGP feeds via RIPE RIS/Route Views API; REST for alert config",
            },
        ],
    },
    {
        "tool_slug": "routinator",
        "entries": [
            {
                "capability": "rpki-route-origin-validation",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "RTR server for routers to fetch ROAs; REST API for validation queries",
            },
        ],
    },
    {
        "tool_slug": "frrouting",
        "entries": [
            {
                "capability": "routing-protocol-suite",
                "protocol_support": ["SSH", "REST"],
                "os_support": ["linux", "container"],
                "notes": "vtysh management via SSH; optional REST API (Northbound); BGP/OSPF/IS-IS dataplane",
            },
        ],
    },

    # ── Cloud Native Networking ───────────────────────────────────────────
    {
        "tool_slug": "cilium",
        "entries": [
            {
                "capability": "ebpf-based-network-policy",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "Cilium REST API and kubectl for policy management; eBPF dataplane",
            },
        ],
    },
    {
        "tool_slug": "calico",
        "entries": [
            {
                "capability": "container-network-connectivity",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "BGP pod routing (not in enum); Kubernetes REST API for NetworkPolicy",
            },
        ],
    },
    {
        "tool_slug": "metallb",
        "entries": [
            {
                "capability": "bare-metal-load-balancing",
                "protocol_support": ["REST"],
                "os_support": ["linux", "container"],
                "notes": "BGP or L2 for IP advertisement; Kubernetes REST API for configuration",
            },
        ],
    },

    # ── Packet Analysis ───────────────────────────────────────────────────
    {
        "tool_slug": "scapy",
        "entries": [
            {
                "capability": "packet-crafting-and-analysis",
                "protocol_support": [],
                "os_support": ["linux", "macos", "windows"],
                "notes": "Raw packet manipulation at L2-L7; operates below the management-protocol layer",
            },
        ],
    },
    {
        "tool_slug": "wireshark",
        "entries": [
            {
                "capability": "packet-capture-and-inspection",
                "protocol_support": [],
                "os_support": ["linux", "macos", "windows"],
                "notes": "Protocol-agnostic capture; dissects all management protocols but doesn't generate them",
            },
        ],
    },
    {
        "tool_slug": "tcpdump",
        "entries": [
            {
                "capability": "command-line-packet-capture",
                "protocol_support": [],
                "os_support": ["linux", "macos"],
                "notes": "libpcap-based; protocol-agnostic capture and filtering",
            },
        ],
    },
]
