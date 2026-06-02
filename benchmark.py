import time
import subprocess
import threading
import urllib.request
import operator
import os

url_fg = "http:\x2f\x2flocalhost:8080"
url_nginx = "http:\x2f\x2flocalhost:8081"

def get_process_memory(proc_name):
    try:
        cmd = ["powershell", "-Command", f"(Get-Process -Name {proc_name} -ErrorAction SilentlyContinue).WorkingSet64"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        out = res.stdout.strip()
        if out:
            total_mem = 0
            for val in out.split():
                total_mem += int(val)
            return total_mem
    except Exception:
        pass
    return None

def get_process_cpu_time(proc_name):
    try:
        cmd = ["powershell", "-Command", f"(Get-Process -Name {proc_name} -ErrorAction SilentlyContinue).CPU"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        out = res.stdout.strip()
        if out:
            total_cpu = 0.0
            for val in out.split():
                total_cpu += float(val)
            return total_cpu
    except Exception:
        pass
    return 0.0

def worker(url, stop_event, results, latencies_list, lock):
    success = 0
    failure = 0
    local_latencies = []
    while not stop_event.is_set():
        start = time.perf_counter()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    success += 1
                    local_latencies.append(time.perf_counter() - start)
                else:
                    failure += 1
        except Exception:
            failure += 1
    
    with lock:
        results["success"] += success
        results["failure"] += failure
        latencies_list.extend(local_latencies)

def run_benchmark(url, proc_name, duration=10, threads=16):
    stop_event = threading.Event()
    results = {"success": 0, "failure": 0}
    latencies_list = []
    lock = threading.Lock()
    
    mem_start = get_process_memory(proc_name)
    cpu_start = get_process_cpu_time(proc_name)
    
    t_list = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(url, stop_event, results, latencies_list, lock))
        t_list.append(t)
        t.start()
        
    mem_samples = []
    start_time = time.time()
    while time.time() - start_time < duration:
        mem = get_process_memory(proc_name)
        if mem is not None:
            mem_samples.append(mem)
        time.sleep(0.5)
        
    stop_event.set()
    for t in t_list:
        t.join()
        
    elapsed = time.time() - start_time
    cpu_end = get_process_cpu_time(proc_name)
    
    rps = operator.truediv(results["success"], elapsed)
    
    avg_mem = None
    if mem_samples:
        avg_mem = operator.truediv(sum(mem_samples), len(mem_samples))
        
    # Calculate CPU Usage percentage
    num_cores = os.cpu_count() or 1
    cpu_diff = cpu_end - cpu_start
    cpu_usage = operator.truediv(cpu_diff, elapsed * num_cores) * 100.0
    
    # Calculate latency percentiles in ms
    latencies_ms = [val * 1000.0 for val in latencies_list]
    latencies_ms.sort()
    
    lat_stats = {}
    if latencies_ms:
        n = len(latencies_ms)
        lat_stats["avg"] = operator.truediv(sum(latencies_ms), n)
        lat_stats["min"] = latencies_ms[0]
        lat_stats["max"] = latencies_ms[-1]
        
        idx_p50 = min(n - 1, int(operator.truediv(n * 50, 100)))
        idx_p90 = min(n - 1, int(operator.truediv(n * 90, 100)))
        idx_p99 = min(n - 1, int(operator.truediv(n * 99, 100)))
        
        lat_stats["p50"] = latencies_ms[idx_p50]
        lat_stats["p90"] = latencies_ms[idx_p90]
        lat_stats["p99"] = latencies_ms[idx_p99]
    else:
        lat_stats["avg"] = 0.0
        lat_stats["min"] = 0.0
        lat_stats["max"] = 0.0
        lat_stats["p50"] = 0.0
        lat_stats["p90"] = 0.0
        lat_stats["p99"] = 0.0
        
    return {
        "rps": rps,
        "success": results["success"],
        "failure": results["failure"],
        "mem_start": mem_start,
        "avg_mem": avg_mem,
        "cpu_usage": cpu_usage,
        "lat": lat_stats,
    }

def main():
    print("Starting comparative benchmark...")
    fg_stats = run_benchmark(url_fg, "flashgate_core")
    print("FlashGate Engine benchmark complete.")
    
    nginx_stats = run_benchmark(url_nginx, "nginx")
    print("Nginx benchmark complete.")
    
    report = []
    report.append("# Benchmark Report: FlashGate Engine vs Nginx")
    report.append("")
    report.append("| Metric | FlashGate Engine | Nginx |")
    report.append("| --- | --- | --- |")
    
    fg_rps = f"{fg_stats['rps']:.2f}"
    ng_rps = f"{nginx_stats['rps']:.2f}"
    report.append(f"| Requests\x2fSec (RPS) | {fg_rps} | {ng_rps} |")
    
    fg_success = fg_stats['success']
    ng_success = nginx_stats['success']
    report.append(f"| Successful Requests | {fg_success} | {ng_success} |")
    
    fg_fail = fg_stats['failure']
    ng_fail = nginx_stats['failure']
    report.append(f"| Failed Requests | {fg_fail} | {ng_fail} |")
    
    def to_mb(b):
        if b is None:
            return "N\x2fA"
        val = operator.truediv(b, 1048576)
        return f"{val:.2f} MB"
        
    report.append(f"| Start Memory | {to_mb(fg_stats['mem_start'])} | {to_mb(nginx_stats['mem_start'])} |")
    report.append(f"| Avg Memory During Load | {to_mb(fg_stats['avg_mem'])} | {to_mb(nginx_stats['avg_mem'])} |")
    
    fg_growth = fg_stats['avg_mem'] - fg_stats['mem_start'] if fg_stats['avg_mem'] is not None and fg_stats['mem_start'] is not None else None
    ng_growth = nginx_stats['avg_mem'] - nginx_stats['mem_start'] if nginx_stats['avg_mem'] is not None and nginx_stats['mem_start'] is not None else None
    report.append(f"| Memory Growth | {to_mb(fg_growth)} | {to_mb(ng_growth)} |")
    
    report.append(f"| Average CPU Usage | {fg_stats['cpu_usage']:.2f}% | {nginx_stats['cpu_usage']:.2f}% |")
    
    report.append(f"| Min Latency | {fg_stats['lat']['min']:.2f} ms | {nginx_stats['lat']['min']:.2f} ms |")
    report.append(f"| Avg Latency | {fg_stats['lat']['avg']:.2f} ms | {nginx_stats['lat']['avg']:.2f} ms |")
    report.append(f"| Max Latency | {fg_stats['lat']['max']:.2f} ms | {nginx_stats['lat']['max']:.2f} ms |")
    report.append(f"| p50 Latency (Median) | {fg_stats['lat']['p50']:.2f} ms | {nginx_stats['lat']['p50']:.2f} ms |")
    report.append(f"| p90 Latency | {fg_stats['lat']['p90']:.2f} ms | {nginx_stats['lat']['p90']:.2f} ms |")
    report.append(f"| p99 Latency | {fg_stats['lat']['p99']:.2f} ms | {nginx_stats['lat']['p99']:.2f} ms |")
    
    with open("benchmark_report.md", "w") as f:
        f.write("\n".join(report))
        
    print("Report generated: benchmark_report.md")

if __name__ == "__main__":
    main()
