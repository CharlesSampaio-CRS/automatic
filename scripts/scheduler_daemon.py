"""
Balance Snapshot Scheduler (APScheduler)
Roda em background e salva snapshots a cada hora fechada
Alternativa ao cron - funciona em qualquer sistema operacional
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pymongo import MongoClient
from dotenv import load_dotenv

# Import snapshot function
from hourly_balance_snapshot import run_hourly_snapshot

# Load environment
load_dotenv()


def scheduled_snapshot():
    """Wrapper para execução agendada"""
    print("\n" + "🔔 " + "=" * 76)
    print(f"   SCHEDULED SNAPSHOT TRIGGERED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    try:
        run_hourly_snapshot()
    except Exception as e:
        print(f"❌ Error in scheduled snapshot: {e}")


def main():
    """
    Inicia o scheduler para executar snapshot a cada hora fechada
    """
    print("=" * 80)
    print("🕐 BALANCE SNAPSHOT SCHEDULER - STARTING")
    print("=" * 80)
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Schedule: Every hour at minute 0 (00:00, 01:00, 02:00, ...)")
    print("=" * 80)
    
    # Create scheduler
    scheduler = BlockingScheduler(timezone='UTC')
    
    # Add job: execute every hour at minute 0
    scheduler.add_job(
        scheduled_snapshot,
        trigger=CronTrigger(minute=0, hour='*'),  # Every hour at :00
        id='hourly_balance_snapshot',
        name='Hourly Balance Snapshot',
        replace_existing=True,
        max_instances=1
    )
    
    # Show next run times
    print("\n📋 Next scheduled runs:")
    for i, job in enumerate(scheduler.get_jobs()):
        next_run = job.next_run_time
        print(f"   {i+1}. {job.name}: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    print("\n✅ Scheduler started. Press Ctrl+C to stop.\n")
    print("=" * 80 + "\n")
    
    try:
        # Start scheduler (blocks here)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n" + "=" * 80)
        print("🛑 SCHEDULER STOPPED BY USER")
        print("=" * 80)
        scheduler.shutdown()


if __name__ == '__main__':
    main()
