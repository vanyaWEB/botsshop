"""
Main entry point for the bot
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
