from __future__ import annotations

from tools.job_channels.base import JobChannel
from tools.job_channels.crypto_jobs import CryptoJobsListChannel
from tools.job_channels.hh_ru import HHRuChannel
from tools.job_channels.linkedin import LinkedInChannel
from tools.job_channels.telegram import TelegramChannel
from tools.job_channels.web3_career import Web3CareerChannel
from tools.web_search import WebSearch


def build_channels(cfg: dict, web_search: WebSearch) -> list[JobChannel]:
    """Включить только те каналы, что разрешены конфигом."""
    channels: list[JobChannel] = []

    if (cfg.get("linkedin") or {}).get("enabled"):
        channels.append(LinkedInChannel(web_search=web_search))
    if (cfg.get("hh_ru") or {}).get("enabled"):
        channels.append(HHRuChannel())
    if (cfg.get("web3_career") or {}).get("enabled"):
        channels.append(Web3CareerChannel())
    if (cfg.get("crypto_jobs") or {}).get("enabled"):
        channels.append(CryptoJobsListChannel())
    if (cfg.get("telegram") or {}).get("enabled"):
        channels.append(TelegramChannel(channels=(cfg.get("telegram") or {}).get("channels") or []))

    return channels
