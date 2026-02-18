"""
Batch management for large channel lists.
Tracks which batch to scan next and rotates through all channels.
"""

import json
from pathlib import Path
from datetime import datetime

from config import BATCH_SIZE, CHANNELS_FILE


STATE_FILE = Path(__file__).parent / "batch_state.json"


def load_batch_state() -> dict:
    """Load batch state from file"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"current_batch": 0, "last_run": None, "total_batches": 0}


def save_batch_state(state: dict):
    """Save batch state to file"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_batch_channels(channels: list, batch_num: int = None) -> tuple[list, int, int]:
    """
    Get channels for current batch.

    Args:
        channels: Full list of channels
        batch_num: Specific batch to run (None = use state file)

    Returns:
        (batch_channels, current_batch_num, total_batches)
    """
    total = len(channels)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE  # Ceiling division

    if batch_num is not None:
        # Use specified batch
        current_batch = batch_num % total_batches
    else:
        # Load from state
        state = load_batch_state()
        current_batch = state.get("current_batch", 0) % total_batches

    start_idx = current_batch * BATCH_SIZE
    end_idx = min(start_idx + BATCH_SIZE, total)

    return channels[start_idx:end_idx], current_batch, total_batches


def advance_batch():
    """Move to next batch for next run"""
    state = load_batch_state()

    # Load channels to get total count
    channels_file = Path(__file__).parent / CHANNELS_FILE
    if channels_file.exists():
        with open(channels_file, 'r') as f:
            data = json.load(f)
            total = len(data.get("channels", []))
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    else:
        total_batches = 1

    current = state.get("current_batch", 0)
    next_batch = (current + 1) % total_batches

    state["current_batch"] = next_batch
    state["last_run"] = datetime.now().isoformat()
    state["total_batches"] = total_batches

    save_batch_state(state)

    return next_batch, total_batches


def reset_batch():
    """Reset to batch 0"""
    state = {
        "current_batch": 0,
        "last_run": None,
        "total_batches": 0
    }
    save_batch_state(state)


def print_batch_status():
    """Print current batch status"""
    state = load_batch_state()
    current = state.get("current_batch", 0)
    total = state.get("total_batches", "?")
    last_run = state.get("last_run", "never")

    print(f"Batch Status: {current + 1}/{total}")
    print(f"Last Run: {last_run}")
    print(f"Channels per batch: {BATCH_SIZE}")
