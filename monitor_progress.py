"""
Enhanced Blog Generator V2 - Progress Monitor
Real-time monitoring and analytics dashboard
"""

import pandas as pd
import os
import time
from datetime import datetime

def monitor_progress():
    """Monitor the progress of the enhanced blog generator"""
    
    print("🚀 Enhanced Blog Generator V2 - Progress Monitor")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Files to monitor
    progress_file = 'enhanced_output_v2.csv'
    final_file = 'enhanced_output_v2_final.csv'
    error_log = 'enhanced_error_log.txt'
    
    last_count = 0
    start_time = time.time()
    
    while True:
        try:
            # Check if progress file exists
            if os.path.exists(progress_file):
                df = pd.read_csv(progress_file)
                current_count = len(df)
                
                if current_count > last_count:
                    last_count = current_count
                    elapsed = time.time() - start_time
                    
                    # Calculate statistics
                    successful = len(df[df['Published'] == 'Yes'])
                    avg_quality = df[df['Quality Score'] != 'ERROR']['Quality Score'].astype(float).mean()
                    avg_seo = df[df['SEO Score'] != 'ERROR']['SEO Score'].astype(float).mean()
                    avg_time = df[df['Processing Time (s)'] != '0.0']['Processing Time (s)'].astype(float).mean()
                    
                    # Estimate completion
                    if current_count > 1:
                        rate = current_count / elapsed * 60  # articles per hour
                        remaining = 33 - current_count
                        eta_minutes = remaining / rate * 60 if rate > 0 else 0
                        eta_time = datetime.now().timestamp() + eta_minutes * 60
                        eta_str = datetime.fromtimestamp(eta_time).strftime('%H:%M:%S')
                    else:
                        eta_str = "Calculating..."
                    
                    print(f"📊 Progress Update - {datetime.now().strftime('%H:%M:%S')}")
                    print(f"   Articles Processed: {current_count}/33")
                    print(f"   Success Rate: {(successful/current_count)*100:.1f}%")
                    print(f"   Avg Quality Score: {avg_quality:.2f}")
                    print(f"   Avg SEO Score: {avg_seo:.2f}")
                    print(f"   Avg Processing Time: {avg_time:.1f}s")
                    print(f"   ETA: {eta_str}")
                    print(f"   Elapsed: {elapsed/60:.1f} minutes")
                    
                    if current_count >= 33:
                        print("\n🎉 PROCESSING COMPLETE!")
                        break
                    
                    print("-" * 40)
            
            # Check for completion
            if os.path.exists(final_file):
                print("\n🎉 FINAL RESULTS AVAILABLE!")
                final_df = pd.read_csv(final_file)
                
                total = len(final_df)
                successful = len(final_df[final_df['Published'] == 'Yes'])
                
                print(f"📈 Final Statistics:")
                print(f"   Total Articles: {total}")
                print(f"   Successfully Published: {successful}")
                print(f"   Success Rate: {(successful/total)*100:.1f}%")
                print(f"   Results saved to: {final_file}")
                break
            
            # Check for errors
            if os.path.exists(error_log):
                with open(error_log, 'r') as f:
                    error_count = len(f.readlines())
                if error_count > 0:
                    print(f"⚠️  {error_count} errors logged in {error_log}")
            
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Monitor error: {str(e)}")
            time.sleep(60)  # Wait longer on error

if __name__ == "__main__":
    monitor_progress()
