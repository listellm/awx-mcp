#!/usr/bin/env python3
"""AWX MCP Server - Model Context Protocol server for AWX API using official Python SDK."""

import json
import sys
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from awx_client import AWXClient, AWXClientError

# Status emoji mapping
STATUS_EMOJI = {
    "successful": "✅",
    "failed": "❌",
    "running": "🔄",
    "pending": "⏳",
    "canceled": "🚫",
    "error": "💥",
}

# Initialise AWX client from environment variables
try:
    awx_client = AWXClient()
except AWXClientError as e:
    sys.stderr.write(f"Failed to initialise AWX client: {e}\n")
    sys.stderr.flush()
    raise

# Create FastMCP server
mcp = FastMCP("awx-mcp-server")


@mcp.tool()
def awx_get_job_status(job_id: int) -> str:
    """
    Get the status and details of an AWX job.

    Args:
        job_id: The AWX job ID to query

    Returns:
        Formatted job status with emoji and details
    """
    try:
        job = awx_client.get_job(job_id)

        # Format key details
        status = job.get("status", "unknown")
        name = job.get("name", "N/A")
        started = job.get("started", "N/A")
        finished = job.get("finished", "N/A")
        elapsed = job.get("elapsed", 0)
        job_type = job.get("type", "N/A")

        # Status emoji
        emoji = STATUS_EMOJI.get(status, "❓")

        output = f"""{emoji} Job {job_id}: {name}

**Status**: {status}
**Type**: {job_type}
**Started**: {started}
**Finished**: {finished}
**Elapsed**: {elapsed:.1f}s

**Related Resources**:
- Job Template ID: {job.get('job_template', 'N/A')}
- Inventory ID: {job.get('inventory', 'N/A')}
- Project: {job.get('project', 'N/A')}
"""

        return output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def awx_stream_job_logs(job_id: int, follow: bool = False) -> str:
    """
    Stream or retrieve job execution logs.

    Args:
        job_id: The AWX job ID to retrieve logs for
        follow: If true, poll for new output until job completes (default: false)

    Returns:
        Job stdout logs
    """
    try:
        if not follow:
            # Simple case: return complete logs immediately
            logs = awx_client.get_job_stdout(job_id, format="txt")
            return logs

        # Polling case: stream logs as they arrive
        output_lines = []
        start_line = 0
        poll_interval = 2  # seconds

        while True:
            # Get job status
            job = awx_client.get_job(job_id)
            status = job.get("status")

            # Get new log lines
            logs = awx_client.get_job_stdout(job_id, format="txt", start_line=start_line)
            new_lines = logs.splitlines()

            # Track progress
            if new_lines:
                output_lines.extend(new_lines)
                start_line += len(new_lines)

            # Check if job finished
            if status in ["successful", "failed", "canceled", "error"]:
                break

            # Continue polling
            time.sleep(poll_interval)

        # Return complete output
        full_output = "\n".join(output_lines)
        return full_output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def awx_list_inventories(page: int = 1, page_size: int = 50) -> str:
    """
    List available AWX inventories.

    Args:
        page: Page number (default: 1)
        page_size: Results per page (default: 50)

    Returns:
        Formatted list of inventories with host counts
    """
    try:
        data = awx_client.list_inventories(page, page_size)
        inventories = data["results"]

        # Format output
        lines = [f"📦 Found {data['count']} inventories (showing page {page}):\n"]

        for inv in inventories:
            inv_id = inv["id"]
            name = inv["name"]
            hosts_count = inv.get("total_hosts", 0)
            desc = inv.get("description", "")
            lines.append(f"- **{name}** (ID: {inv_id}) - {hosts_count} hosts")
            if desc:
                lines.append(f"  {desc}")

        output = "\n".join(lines)
        return output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def awx_get_inventory_hosts(inventory_id: Optional[int] = None, inventory_name: Optional[str] = None) -> str:
    """
    Get all hosts in an AWX inventory.

    Args:
        inventory_id: Inventory ID (use this OR inventory_name)
        inventory_name: Inventory name (use this OR inventory_id)

    Returns:
        Formatted list of hosts in the inventory
    """
    try:
        # Resolve inventory ID
        if inventory_id is not None:
            inventory = awx_client.get_inventory(inventory_id)
        elif inventory_name is not None:
            inventory = awx_client.find_inventory_by_name(inventory_name)
            if not inventory:
                return f"❌ Inventory not found: {inventory_name}"
            inventory_id = inventory["id"]
        else:
            return "❌ Must provide inventory_id or inventory_name"

        # Get hosts
        hosts = awx_client.get_inventory_hosts(inventory_id)

        # Format output
        lines = [f"🖥️ Hosts in inventory '{inventory['name']}' (ID: {inventory_id}):\n"]
        lines.append(f"Total hosts: {len(hosts)}\n")

        for host in hosts:
            host_id = host["id"]
            name = host["name"]
            enabled = "✅" if host.get("enabled", True) else "❌"
            desc = host.get("description", "")
            lines.append(f"{enabled} **{name}** (ID: {host_id})")
            if desc:
                lines.append(f"  {desc}")

        output = "\n".join(lines)
        return output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def awx_get_host_variables(host_id: Optional[int] = None, host_name: Optional[str] = None) -> str:
    """
    Get variables for a specific host.

    Args:
        host_id: Host ID (use this OR host_name)
        host_name: Host FQDN (use this OR host_id)

    Returns:
        Host variables formatted as JSON
    """
    try:
        # Resolve host ID
        if host_id is not None:
            host = awx_client.get_host(host_id)
        elif host_name is not None:
            host = awx_client.find_host_by_name(host_name)
            if not host:
                return f"❌ Host not found: {host_name}"
            host_id = host["id"]
        else:
            return "❌ Must provide host_id or host_name"

        # Get variables
        variables = awx_client.get_host_variables(host_id)

        # Format output
        lines = [f"🔧 Variables for host '{host['name']}' (ID: {host_id}):\n"]
        lines.append("```json")
        lines.append(json.dumps(variables, indent=2))
        lines.append("```")

        output = "\n".join(lines)
        return output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def awx_search_job_templates(name_filter: Optional[str] = None, limit: int = 50) -> str:
    """
    Search for AWX job templates.

    Args:
        name_filter: Filter by template name (substring match)
        limit: Maximum results to return (default: 50)

    Returns:
        Formatted list of job templates with playbook information
    """
    try:
        templates = awx_client.search_job_templates(name_filter, limit)

        # Format output
        if name_filter:
            lines = [f"🔍 Job templates matching '{name_filter}':\n"]
        else:
            lines = ["📋 Available job templates:\n"]

        lines.append(f"Found {len(templates)} templates\n")

        for tmpl in templates:
            tmpl_id = tmpl["id"]
            name = tmpl["name"]
            playbook = tmpl.get("playbook", "N/A")
            desc = tmpl.get("description", "")
            lines.append(f"- **{name}** (ID: {tmpl_id})")
            lines.append(f"  Playbook: `{playbook}`")
            if desc:
                lines.append(f"  {desc}")

        output = "\n".join(lines)
        return output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def awx_list_recent_jobs(status: Optional[str] = None, limit: int = 20) -> str:
    """
    List recent AWX job executions.

    Args:
        status: Filter by status (successful, failed, running, pending, canceled, error)
        limit: Maximum results to return (default: 20)

    Returns:
        Formatted list of recent jobs with status emoji
    """
    try:
        jobs = awx_client.list_jobs(status, limit)

        # Format output
        if status:
            lines = [f"📜 Recent jobs with status '{status}':\n"]
        else:
            lines = ["📜 Recent jobs:\n"]

        lines.append(f"Showing {len(jobs)} jobs\n")

        for job in jobs:
            job_id = job["id"]
            name = job["name"]
            job_status = job.get("status", "unknown")
            started = job.get("started", "N/A")
            finished = job.get("finished", "N/A")

            emoji = STATUS_EMOJI.get(job_status, "❓")

            lines.append(f"{emoji} **Job {job_id}**: {name}")
            lines.append(f"  Status: {job_status}")
            lines.append(f"  Started: {started}")
            if finished != "N/A":
                lines.append(f"  Finished: {finished}")

        output = "\n".join(lines)
        return output

    except AWXClientError as e:
        return f"AWX Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def main():
    """Main entry point."""
    sys.stderr.write("AWX MCP Server starting...\n")
    sys.stderr.write(f"Connected to AWX at {awx_client.base_url}\n")
    sys.stderr.flush()

    # Run server with stdio transport (default)
    mcp.run()


if __name__ == "__main__":
    main()
