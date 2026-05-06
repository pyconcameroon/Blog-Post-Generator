#!/usr/bin/env python3
"""
Enhanced V2 System Monitor
Monitor the current status of the blog generation system
"""

import os
import json
import glob
from datetime import datetime, timedelta
import requests

def monitor_system_status():
    """Monitor the Enhanced V2 system status"""
    
    print("🔍 ENHANCED V2 SYSTEM STATUS MONITOR")
    print("=" * 50)
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Check if process is running
    print("1️⃣ PROCESS STATUS:")
    python_processes = []
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent']):
            try:
                if 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if 'enhanced_blog_generator_v2.py' in cmdline:
                        runtime = datetime.now() - datetime.fromtimestamp(proc.info['create_time'])
                        python_processes.append({
                            'pid': proc.info['pid'],
                            'runtime': str(runtime).split('.')[0],
                            'cpu_percent': proc.info['cpu_percent']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if python_processes:
            for proc in python_processes:
                print(f"   ✅ Enhanced V2 Running (PID: {proc['pid']})")
                print(f"      Runtime: {proc['runtime']}")
                print(f"      CPU Usage: {proc['cpu_percent']}%")
        else:
            print("   ❌ Enhanced V2 not currently running")
    except ImportError:
        print("   ⚠️  Cannot check process status (psutil not available)")
    except Exception as e:
        print(f"   ⚠️  Error checking processes: {e}")
    
    print()
    
    # 2. Check generated content files
    print("2️⃣ CONTENT GENERATION STATUS:")
    
    # Look for HTML files
    html_files = glob.glob("*.html")
    content_files = [f for f in html_files if 'content_' in f or 'generated_' in f or 'article_' in f]
    
    if content_files:
        print(f"   📄 Generated content files found: {len(content_files)}")
        for file in sorted(content_files, key=os.path.getmtime, reverse=True)[:5]:
            mod_time = datetime.fromtimestamp(os.path.getmtime(file))
            file_size = os.path.getsize(file)
            print(f"      • {file} ({file_size:,} bytes, {mod_time.strftime('%H:%M:%S')})")
    else:
        print("   📄 No content files found with standard naming")
        
        # Check for any recent HTML files
        recent_files = []
        for file in html_files:
            mod_time = datetime.fromtimestamp(os.path.getmtime(file))
            if mod_time > datetime.now() - timedelta(hours=2):
                recent_files.append((file, mod_time))
        
        if recent_files:
            print(f"   📄 Recent HTML files (last 2 hours): {len(recent_files)}")
            for file, mod_time in sorted(recent_files, key=lambda x: x[1], reverse=True):
                file_size = os.path.getsize(file)
                print(f"      • {file} ({file_size:,} bytes, {mod_time.strftime('%H:%M:%S')})")
    
    print()
    
    # 3. Check CSV input file
    print("3️⃣ INPUT DATA STATUS:")
    if os.path.exists('input.csv'):
        import pandas as pd
        try:
            df = pd.read_csv('input.csv')
            print(f"   📊 Input CSV: {len(df)} total articles")
            
            # Try to determine progress
            if 'status' in df.columns:
                completed = len(df[df['status'] == 'completed'])
                in_progress = len(df[df['status'] == 'in_progress'])
                pending = len(df[df['status'] == 'pending'])
                print(f"      ✅ Completed: {completed}")
                print(f"      🔄 In Progress: {in_progress}")
                print(f"      ⏳ Pending: {pending}")
            else:
                print("      ℹ️  No status column found in CSV")
                
        except Exception as e:
            print(f"   ❌ Error reading CSV: {e}")
    else:
        print("   ❌ input.csv not found")
    
    print()
    
    # 4. Check generated images
    print("4️⃣ IMAGE GENERATION STATUS:")
    if os.path.exists('generated_images'):
        image_files = glob.glob('generated_images/*.png')
        if image_files:
            print(f"   🖼️  Generated images: {len(image_files)}")
            
            # Show recent images
            recent_images = []
            for img in image_files:
                mod_time = datetime.fromtimestamp(os.path.getmtime(img))
                if mod_time > datetime.now() - timedelta(hours=2):
                    recent_images.append((os.path.basename(img), mod_time))
            
            if recent_images:
                print(f"      Recent (last 2 hours): {len(recent_images)}")
                for img, mod_time in sorted(recent_images, key=lambda x: x[1], reverse=True)[:5]:
                    print(f"        • {img} ({mod_time.strftime('%H:%M:%S')})")
        else:
            print("   📁 Generated images folder exists but no PNG files found")
    else:
        print("   📁 No generated_images folder found")
    
    print()
    
    # 5. System performance estimates
    print("5️⃣ PERFORMANCE ESTIMATES:")
    
    # Calculate based on file timestamps
    if content_files:
        # Get creation times of content files
        file_times = []
        for file in content_files:
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(file))
                file_times.append(mod_time)
            except:
                continue
        
        if len(file_times) >= 2:
            file_times.sort()
            time_diff = (file_times[-1] - file_times[0]).total_seconds()
            avg_time_per_article = time_diff / (len(file_times) - 1) if len(file_times) > 1 else 0
            
            print(f"   ⏱️  Average time per article: {avg_time_per_article/60:.1f} minutes")
            
            # Estimate remaining time if we know total articles
            try:
                df = pd.read_csv('input.csv')
                total_articles = len(df)
                completed_articles = len(content_files)
                remaining_articles = total_articles - completed_articles
                estimated_remaining_time = (remaining_articles * avg_time_per_article) / 60
                
                print(f"   📈 Progress: {completed_articles}/{total_articles} articles ({(completed_articles/total_articles)*100:.1f}%)")
                print(f"   ⏰ Estimated remaining time: {estimated_remaining_time:.0f} minutes ({estimated_remaining_time/60:.1f} hours)")
                
            except:
                print(f"   📈 Articles generated: {len(content_files)}")
    
    print()
    
    # 6. WordPress integration status
    print("6️⃣ WORDPRESS INTEGRATION:")
    try:
        # Check if WordPress credentials are configured
        import json
        config_found = False
        
        # Check for config files
        config_files = ['config.json', 'wp_config.json', 'wordpress_config.json']
        for config_file in config_files:
            if os.path.exists(config_file):
                print(f"   ⚙️  Configuration found: {config_file}")
                config_found = True
                break
        
        if not config_found:
            print("   ⚙️  No WordPress configuration files found")
        
        # Try to check WordPress connectivity (if we can find credentials)
        print("   🔌 WordPress connectivity: Unable to test without exposing credentials")
        
    except Exception as e:
        print(f"   ❌ Error checking WordPress integration: {e}")
    
    print()
    print("🔍 MONITORING COMPLETE")
    print("=" * 50)
    
    return {
        'content_files_count': len(content_files) if content_files else 0,
        'image_files_count': len(glob.glob('generated_images/*.png')) if os.path.exists('generated_images') else 0,
        'system_running': len(python_processes) > 0 if 'python_processes' in locals() else None
    }

if __name__ == "__main__":
    try:
        status = monitor_system_status()
        
        # Save status to file for external monitoring
        with open('system_status.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'status': status
            }, f, indent=2)
            
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        import traceback
        traceback.print_exc()
