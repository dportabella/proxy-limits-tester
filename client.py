import urllib.request
import urllib.error
import time
import sys
import argparse

# Helper functions for human-readable formatting
def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"

def format_speed(bytes_per_sec):
    return f"{format_size(bytes_per_sec)}/s"

# Track the maximum duration of any successful request with data flowing
global_max_duration = 0.0
upload_speeds = []
download_speeds = []

def get_median(lst):
    if not lst: return 0
    s = sorted(lst)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]

def test_upload(base_url, size_mb):
    global global_max_duration, upload_speeds
    bytes_size = int(size_mb * 1024 * 1024)
    print(f"  Testing upload {format_size(bytes_size)}...", end=" ", flush=True)
    data = b"0" * bytes_size
    req = urllib.request.Request(f"{base_url}/upload", data=data, method="POST")
    start = time.time()
    try:
        urllib.request.urlopen(req, timeout=120) 
        elapsed = time.time() - start
        speed = bytes_size / elapsed if elapsed > 0 else 0
        global_max_duration = max(global_max_duration, elapsed)
        upload_speeds.append(speed)
        return True, "", elapsed, speed
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}", time.time() - start, 0
    except Exception as e:
        return False, str(e), time.time() - start, 0

def test_idle_timeout(base_url, delay_sec):
    print(f"  Testing idle timeout {format_time(delay_sec)}...", end=" ", flush=True)
    start = time.time()
    try:
        urllib.request.urlopen(f"{base_url}/timeout?delay={int(delay_sec)}", timeout=delay_sec + 30)
        elapsed = time.time() - start
        return True, "", elapsed, 0
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}", time.time() - start, 0
    except Exception as e:
        return False, str(e), time.time() - start, 0

def test_download(base_url, size_mb):
    global global_max_duration, download_speeds
    bytes_size = int(size_mb * 1024 * 1024)
    print(f"  Testing download {format_size(bytes_size)}...", end=" ", flush=True)
    start = time.time()
    try:
        response = urllib.request.urlopen(f"{base_url}/download?size_mb={int(size_mb)}", timeout=120)
        data = response.read()
        elapsed = time.time() - start
        actual_size = len(data)
        if actual_size >= bytes_size * 0.99:
            speed = actual_size / elapsed if elapsed > 0 else 0
            global_max_duration = max(global_max_duration, elapsed)
            download_speeds.append(speed)
            return True, "", elapsed, speed
        else:
            return False, f"Partial download: {format_size(actual_size)}", elapsed, 0
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}", time.time() - start, 0
    except Exception as e:
        return False, str(e), time.time() - start, 0

def find_limit(test_func, base_url, name, is_size=False, initial_val=1.0, margin=0.20, max_limit=2000.0):
    print(f"\n--- Finding Limit for: {name} ---")
    val = initial_val
    max_success = 0
    min_failure = float('inf')
    
    # Phase 1: Exponential growth
    while True:
        success, err_msg, elapsed, speed = test_func(base_url, val)
        time_str = format_time(elapsed)
        speed_str = f" @ {format_speed(speed)}" if speed > 0 else ""
        if success:
            max_success = val
            print(f"✅ OK ({time_str}{speed_str})")
            if val >= max_limit: 
                print(f"  ⚠️ Reached safety test limit ({max_limit}).")
                return val
            val *= 2
        else:
            min_failure = val
            print(f"❌ Failed ({err_msg}) after {time_str}")
            break
            
    if max_success == 0:
        print(f"⚠️ Failed on the first attempt ({initial_val}). The limit is lower.")
        return 0

    # Phase 2: Binary search
    while (min_failure - max_success) / max_success > margin:
        val = (max_success + min_failure) / 2.0
        success, err_msg, elapsed, speed = test_func(base_url, val)
        time_str = format_time(elapsed)
        speed_str = f" @ {format_speed(speed)}" if speed > 0 else ""
        if success:
            max_success = val
            print(f"✅ OK ({time_str}{speed_str})")
        else:
            min_failure = val
            print(f"❌ Failed ({err_msg}) after {time_str}")
            
    if is_size:
        success_str = format_size(max_success * 1024 * 1024)
        failure_str = format_size(min_failure * 1024 * 1024)
    else:
        success_str = format_time(max_success)
        failure_str = format_time(min_failure)

    print(f"🎯 Final result for {name}: Confirmed limit around ~{success_str} (Proxy drops at {failure_str})")
    return max_success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proxy Limits Tester Client")
    parser.add_argument("url", nargs="?", default="https://clawbox.totmicro.com", help="Base URL of the proxy to test")
    parser.add_argument("--max-timeout", type=float, default=600.0, help="Maximum idle timeout to test in seconds (default 600)")
    parser.add_argument("--max-upload", type=float, default=2000.0, help="Maximum upload size to test in MB (default 2000)")
    parser.add_argument("--max-download", type=float, default=2000.0, help="Maximum download size to test in MB (default 2000)")
    
    parser.add_argument("--min-timeout", type=float, default=2.0, help="Initial idle timeout to test in seconds (default 2.0)")
    parser.add_argument("--min-upload", type=float, default=1.0, help="Initial upload size to test in MB (default 1.0)")
    parser.add_argument("--min-download", type=float, default=5.0, help="Initial download size to test in MB (default 5.0)")
    
    args = parser.parse_args()
    base_url = args.url.rstrip('/')
        
    print(f"Testing against {base_url}\n")
    try:
        urllib.request.urlopen(base_url, timeout=10)
        print("Proxy server is reachable. Starting limit discovery...\n")
    except Exception as e:
        print(f"⚠️ Warning: Cannot ping {base_url}. Make sure proxy_tester_server is running on the target.")
        print(f"Detailed error: {e}\n")
        sys.exit(1)
        
    timeout_limit = find_limit(test_idle_timeout, base_url, "Idle Timeout / proxy_read_timeout", is_size=False, initial_val=args.min_timeout, max_limit=args.max_timeout)
    upload_limit = find_limit(test_upload, base_url, "Upload Size", is_size=True, initial_val=args.min_upload, max_limit=args.max_upload)
    download_limit = find_limit(test_download, base_url, "Download Size", is_size=True, initial_val=args.min_download, max_limit=args.max_download)

    median_upload_speed = get_median(upload_speeds)
    median_download_speed = get_median(download_speeds)

    print("\n" + "="*55)
    print(" SUMMARY OF DISCOVERED PROXY LIMITS")
    print("="*55)
    print(f" • Idle Timeout (proxy_read_timeout) : ~{format_time(timeout_limit)}")
    print(f" • Max Upload Size (client_max_body) : ~{format_size(upload_limit * 1024 * 1024)}")
    print(f" • Median Upload Speed               : {format_speed(median_upload_speed)}")
    print(f" • Max Download Size                 : ~{format_size(download_limit * 1024 * 1024)}")
    print(f" • Median Download Speed             : {format_speed(median_download_speed)}")
    print(f" • Max Request Duration (Active)     : >={format_time(global_max_duration)}")
    print("="*55 + "\n")
