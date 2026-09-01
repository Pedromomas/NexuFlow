from __future__ import annotations

import os
from dataclasses import dataclass

from ..winexec import powershell_json


@dataclass(frozen=True, slots=True)
class PrimaryInterface:
    index: int
    alias: str
    description: str
    guid: str
    next_hop: str
    route_metric: int
    interface_metric: int
    status: str
    link_speed: str
    network_category: str
    mtu: int

    @property
    def probably_virtual(self) -> bool:
        text = f"{self.alias} {self.description}".lower()
        markers = ("wireguard", "wintun", "openvpn", " tap", "vpn", "tailscale", "zerotier", "hamachi", "warp", "mullvad", "proton", "hyper-v", "vmware", "virtualbox")
        return any(x in text for x in markers)


class InterfaceManager:
    @staticmethod
    def primary_ipv4() -> PrimaryInterface:
        if os.name != "nt":
            return PrimaryInterface(0, "unknown", "non-Windows", "", "", 0, 0, "Unknown", "Unknown", "Unknown", 1500)
        data = powershell_json(r"""
$route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
  Sort-Object @{Expression={ [int]$_.RouteMetric + [int]$_.InterfaceMetric }} | Select-Object -First 1
if (-not $route) { throw 'No IPv4 default route found.' }
$adapter = Get-NetAdapter -InterfaceIndex $route.InterfaceIndex -ErrorAction Stop
$profile = Get-NetConnectionProfile -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue
$ipif = Get-NetIPInterface -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop
[PSCustomObject]@{
 InterfaceIndex=[int]$route.InterfaceIndex; InterfaceAlias=[string]$adapter.Name;
 Description=[string]$adapter.InterfaceDescription; InterfaceGuid=[string]$adapter.InterfaceGuid;
 NextHop=[string]$route.NextHop; RouteMetric=[int]$route.RouteMetric; InterfaceMetric=[int]$route.InterfaceMetric;
 Status=[string]$adapter.Status; LinkSpeed=[string]$adapter.LinkSpeed;
 NetworkCategory=if($profile){[string]$profile.NetworkCategory}else{'Unknown'}; Mtu=[int]$ipif.NlMtu
} | ConvertTo-Json -Compress
""")
        return PrimaryInterface(
            int(data["InterfaceIndex"]), data["InterfaceAlias"], data["Description"], data["InterfaceGuid"],
            data["NextHop"], int(data["RouteMetric"]), int(data["InterfaceMetric"]), data["Status"],
            data["LinkSpeed"], data["NetworkCategory"], int(data["Mtu"]),
        )
