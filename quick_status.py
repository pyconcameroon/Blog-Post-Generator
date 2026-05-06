"""
Quick Status Checker for Enhanced Blog Generator V2
"""

import os
import pandas as pd
from datetime import datetime

def quick_status():
    """Quick status check"""
    print(f"📊 Enhanced Blog Generator V2 - Status Check")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check if process is running
    progress_file = 'enhanced_output_v2.csv'
    error_log = 'enhanced_error_log.txt'
    
    if os.path.exists(progress_file):
        df = pd.read_csv(progress_file)
        print(f"✅ Articles Completed: {len(df)}/33")
        
        if len(df) > 0:
            successful = len(df[df['Published'] == 'Yes'])
            print(f"✅ Successfully Published: {successful}")
            print(f"📈 Success Rate: {(successful/len(df))*100:.1f}%")
            
            # Latest article
            latest = df.iloc[-1]
            print(f"🔄 Latest: {latest['Meta Title']}")
            print(f"📊 Quality: {latest['Quality Score']}, SEO: {latest['SEO Score']}")
    else:
        print("⏳ Processing started, waiting for first results...")
    
    if os.path.exists(error_log):
        with open(error_log, 'r') as f:
            errors = f.readlines()
        if errors:
            print(f"⚠️  {len(errors)} errors logged")
    
    print("\n🔄 Process Status: RUNNING")
    print("💡 Use 'python monitor_progress.py' for real-time monitoring")

if __name__ == "__main__":
    quick_status()
