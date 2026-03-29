"""
Update Datamart V2

This script loads all V2 loaders with bug fixes:
1. Risk Score - Multi-factor calculation
2. Milestone - Safe bounds checking
3. Time Affinity - Contextual interpretation
4. Activity Transitions - Proper resource key matching
5. Engagement Distribution - V2 thresholds
6. Behavior Correlation - Cramming detection
7. Deadline Proximity - Current time calculation

Usage:
    python datamart/updateDatamart_v2.py
"""

import sys
import time
from datetime import datetime

# Import V2 loaders
from datamart.loader.loadFactStudentRiskWeekly_v2 import LoadFactStudentRiskWeekly_v2
from datamart.loader.loadFactStudentCourseLifeCycle_v2 import LoadFactStudentCourseLifeCycle_v2
from datamart.loader.loadFactStudentTimeAffinity_v2 import LoadFactStudentTimeAffinity_v2
from datamart.loader.loadFactActivityTransitions_v2 import LoadFactActivityTransitions_v2
from datamart.loader.loadFactClassEngagementDistribution_v2 import LoadFactClassEngagementDistribution_v2
from datamart.loader.loadFactBehaviorOutcomeCorrelation_v2 import LoadFactBehaviorOutcomeCorrelation_v2
from datamart.loader.loadFactStudentDeadlineProximity_v2 import LoadFactStudentDeadlineProximity_v2


def print_header(message):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)


def print_step(step_num, total_steps, message):
    """Print formatted step"""
    print(f"\n[{step_num}/{total_steps}] {message}")
    print("-" * 80)


def run_loader(loader_class, loader_name):
    """Run a loader and track execution time"""
    start_time = time.time()
    try:
        loader = loader_class()
        loader.load()
        elapsed = time.time() - start_time
        print(f"✓ {loader_name} completed in {elapsed:.2f}s")
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ {loader_name} failed after {elapsed:.2f}s")
        print(f"  Error: {str(e)}")
        return False, elapsed


def main():
    """Main execution function"""
    print_header("DATAMART V2 UPDATE - BUG FIXES")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_start = time.time()
    results = []
    
    # Define loaders in execution order
    loaders = [
        (LoadFactStudentRiskWeekly_v2, "Risk Score V2 (Multi-factor)"),
        (LoadFactStudentCourseLifeCycle_v2, "Course Lifecycle V2 (Safe milestones)"),
        (LoadFactStudentTimeAffinity_v2, "Time Affinity V2 (Contextual)"),
        (LoadFactActivityTransitions_v2, "Activity Transitions V2 (Fixed keys)"),
        (LoadFactClassEngagementDistribution_v2, "Engagement Distribution V2 (New thresholds)"),
        (LoadFactStudentDeadlineProximity_v2, "Deadline Proximity V2 (Current time)"),
        (LoadFactBehaviorOutcomeCorrelation_v2, "Behavior Correlation V2 (Cramming detection)"),
    ]
    
    total_steps = len(loaders)
    
    # Execute loaders
    for idx, (loader_class, loader_name) in enumerate(loaders, 1):
        print_step(idx, total_steps, loader_name)
        success, elapsed = run_loader(loader_class, loader_name)
        results.append((loader_name, success, elapsed))
    
    # Summary
    total_elapsed = time.time() - total_start
    print_header("EXECUTION SUMMARY")
    
    print("\nResults:")
    print("-" * 80)
    success_count = 0
    for name, success, elapsed in results:
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{status:12} | {elapsed:6.2f}s | {name}")
        if success:
            success_count += 1
    
    print("-" * 80)
    print(f"\nTotal: {success_count}/{len(results)} loaders succeeded")
    print(f"Total execution time: {total_elapsed:.2f}s")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit code
    if success_count == len(results):
        print("\n✓ All V2 loaders completed successfully!")
        return 0
    else:
        print(f"\n✗ {len(results) - success_count} loader(s) failed. Check logs above.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
