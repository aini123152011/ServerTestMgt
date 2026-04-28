"""Agent configuration."""

import os


class AgentConfig:
    # Backend API URL
    SERVER_URL: str = os.getenv("STL_SERVER_URL", "http://localhost:8000/api/v1")
    # Agent authentication token (issued by backend)
    AGENT_TOKEN: str = os.getenv("STL_AGENT_TOKEN", "")
    # Heartbeat interval in seconds
    HEARTBEAT_INTERVAL: int = int(os.getenv("STL_HEARTBEAT_INTERVAL", "30"))
    # Working directory for test artifacts
    WORK_DIR: str = os.getenv("STL_WORK_DIR", "/tmp/stl-agent")
    # Log level
    LOG_LEVEL: str = os.getenv("STL_LOG_LEVEL", "INFO")


config = AgentConfig()
