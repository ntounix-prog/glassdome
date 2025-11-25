"""
Reaper Agents

OS-specific agents for executing vulnerability injection tasks.
"""

from glassdome.reaper.agents.base import BaseReaperAgent
from glassdome.reaper.agents.linux_agent import LinuxReaperAgent
from glassdome.reaper.agents.windows_agent import WindowsReaperAgent
from glassdome.reaper.agents.mac_agent import MacReaperAgent

__all__ = [
    'BaseReaperAgent',
    'LinuxReaperAgent',
    'WindowsReaperAgent',
    'MacReaperAgent',
]

