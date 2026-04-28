"""PXE provisioning service - manages dnsmasq config and kickstart generation."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default paths - configurable via environment
PXE_TEMPLATE_DIR = os.environ.get("PXE_TEMPLATE_DIR", str(Path(__file__).parent.parent.parent.parent / "deploy" / "pxe"))
DNSMASQ_HOSTS_DIR = os.environ.get("DNSMASQ_HOSTS_DIR", "/etc/dnsmasq.d/hosts")
KICKSTART_OUTPUT_DIR = os.environ.get("KICKSTART_OUTPUT_DIR", "/var/www/html/kickstart")

# Available OS profiles
OS_PROFILES = {
    "rhel9": {
        "name": "RHEL 9 / CentOS Stream 9",
        "os_type": "rhel",
        "version": "9",
        "kickstart_template": "kickstart/rhel9.ks.j2",
    },
    "ubuntu2204": {
        "name": "Ubuntu 22.04 LTS",
        "os_type": "ubuntu",
        "version": "22.04",
        "kickstart_template": "preseed/ubuntu.cfg.j2",
    },
}


class PXEService:
    """Manages dnsmasq configuration and kickstart/preseed generation."""

    def __init__(self):
        self._jinja_env = Environment(
            loader=FileSystemLoader(PXE_TEMPLATE_DIR),
            autoescape=False,
        )

    def get_profiles(self) -> list[dict[str, Any]]:
        """Return available OS profiles."""
        return [{"id": k, **v} for k, v in OS_PROFILES.items()]

    def add_host(self, mac: str, ip: str, hostname: str, profile: str) -> bool:
        """Add a host entry to dnsmasq DHCP configuration."""
        os.makedirs(DNSMASQ_HOSTS_DIR, exist_ok=True)
        config_path = os.path.join(DNSMASQ_HOSTS_DIR, f"host-{hostname}.conf")
        config_content = f"dhcp-host={mac},{ip},{hostname}\n"
        try:
            with open(config_path, "w") as f:
                f.write(config_content)
            logger.info("Added dnsmasq host: %s -> %s (%s)", mac, ip, hostname)
            return True
        except OSError as e:
            logger.error("Failed to write dnsmasq host config: %s", e)
            return False

    def remove_host(self, hostname: str) -> bool:
        """Remove a host entry from dnsmasq configuration."""
        config_path = os.path.join(DNSMASQ_HOSTS_DIR, f"host-{hostname}.conf")
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
                logger.info("Removed dnsmasq host: %s", hostname)
            return True
        except OSError as e:
            logger.error("Failed to remove dnsmasq host config: %s", e)
            return False

    def reload_dnsmasq(self) -> bool:
        """Reload dnsmasq to pick up configuration changes."""
        try:
            result = subprocess.run(
                ["systemctl", "reload", "dnsmasq"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                logger.info("dnsmasq reloaded successfully")
                return True
            logger.error("dnsmasq reload failed: %s", result.stderr)
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error("Failed to reload dnsmasq: %s", e)
            return False

    def generate_kickstart(
        self,
        profile: str,
        hostname: str,
        ip: str,
        callback_url: str,
        custom_packages: list[str] | None = None,
        post_install_script: str | None = None,
    ) -> str:
        """Generate a kickstart/preseed config from template."""
        profile_info = OS_PROFILES.get(profile)
        if not profile_info:
            raise ValueError(f"Unknown OS profile: {profile}")

        template_path = profile_info["kickstart_template"]
        try:
            template = self._jinja_env.get_template(template_path)
        except Exception:
            # Fallback: return a minimal config if template not found
            logger.warning("Template %s not found, generating minimal config", template_path)
            return self._generate_minimal_config(profile_info, hostname, ip, callback_url, custom_packages, post_install_script)

        rendered = template.render(
            hostname=hostname,
            ip=ip,
            callback_url=callback_url,
            custom_packages=custom_packages or [],
            post_install_script=post_install_script or "",
            profile=profile_info,
        )
        return rendered

    def save_kickstart(self, hostname: str, content: str) -> str:
        """Save rendered kickstart to the HTTP-served directory."""
        os.makedirs(KICKSTART_OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(KICKSTART_OUTPUT_DIR, f"{hostname}.cfg")
        with open(filepath, "w") as f:
            f.write(content)
        logger.info("Saved kickstart config: %s", filepath)
        return filepath

    def _generate_minimal_config(
        self, profile_info: dict, hostname: str, ip: str,
        callback_url: str, custom_packages: list[str] | None, post_install_script: str | None,
    ) -> str:
        """Generate a minimal kickstart/preseed when template is unavailable."""
        os_type = profile_info["os_type"]
        packages = "\n".join(custom_packages or [])

        if os_type == "rhel":
            return f"""# Minimal Kickstart for {hostname}
lang en_US.UTF-8
keyboard us
timezone UTC
rootpw --plaintext changeme
network --bootproto=static --ip={ip} --hostname={hostname}
bootloader --location=mbr
clearpart --all --initlabel
autopart
%packages
@core
{packages}
%end
%post
curl -X POST {callback_url} -H "Content-Type: application/json" -d '{{"status":"completed","message":"Installation complete"}}'
{post_install_script or ""}
%end
"""
        else:  # ubuntu preseed
            return f"""# Minimal Preseed for {hostname}
d-i debian-installer/locale string en_US.UTF-8
d-i netcfg/hostname string {hostname}
d-i netcfg/get_ipaddress string {ip}
d-i partman-auto/method string regular
d-i pkgsel/include string {" ".join(custom_packages or [])}
d-i preseed/late_command string \\
    curl -X POST {callback_url} -H "Content-Type: application/json" -d '{{"status":"completed","message":"Installation complete"}}'; \\
    {post_install_script or "true"}
"""
