# Proxy Limits Tester

A set of Python tools with **zero external dependencies** to dynamically discover the limits of an HTTP reverse proxy (Nginx, Traefik, Kubernetes Ingress, Cloudflare, etc.).

This utility performs an exponential search (1, 2, 4, 8...) and, upon hitting the point where the proxy fails, applies a binary search algorithm to pinpoint the exact limit with high precision.

## Detected Limits:
1. **Idle Timeout (`proxy_read_timeout` / `proxy_connect_timeout`)**: The maximum time in seconds the proxy waits for a backend response without any data being transferred.
2. **Max Upload Size (`client_max_body_size`)**: The maximum data size in MB the proxy allows to be uploaded to the backend.
3. **Max Download Size**: The maximum data size in MB the proxy allows to be received in a single stream.
4. **Total Connection Duration Analysis**: At the end of the test, the script reports the maximum continuous duration achieved during data transfers, which confirms whether the proxy has a hard absolute timeout limit for active transfers.

## Usage

### 1. Start the Server (Backend)
Run `server.py` behind your proxy (e.g., inside your Kubernetes cluster, Docker environment, or target server). This server simulates a backend that handles dummy in-memory uploads or delays responses by an exact number of seconds.

```bash
python3 server.py 10010
```

### 2. Start the Client (Local Tester)
Run the client script from your local machine, pointing it to the public URL that routes through your proxy to the server port.

```bash
python3 client.py https://your-proxy-domain.com
```

You can optionally configure both minimum starting values and maximum safety limits to avoid testing excessively large payloads or long delays, especially if you already know the proxy supports a certain baseline:

```bash
python3 client.py https://your-proxy-domain.com \
  --min-timeout 60 --max-timeout 600 \
  --min-upload 50 --max-upload 2000 \
  --min-download 50 --max-download 2000
```

### Fast Upload Probing
If you want to discover the max upload size instantly and without consuming any bandwidth, pass the `--fast-upload` flag:
```bash
python3 client.py https://your-proxy-domain.com --fast-upload
```
This uses HTTP/1.1 `Expect: 100-continue` headers to ask the proxy if it accepts a given `Content-Length` before transmitting the body. It skips the upload completely, returning results in milliseconds instead of minutes.

### Example Output
The algorithm will begin probing the proxy with small payloads and low timeouts, then refine the limits:
```text
--- Finding Limit for: Idle Timeout / proxy_read_timeout ---
  Testing idle timeout 2.0s... ✅ OK (2.1s)
  Testing idle timeout 4.0s... ✅ OK (4.1s)
  Testing idle timeout 8.0s... ✅ OK (8.1s)
  Testing idle timeout 16.0s... ❌ Failed (HTTP 504) after 10.1s
  Testing idle timeout 12.0s... ❌ Failed (HTTP 504) after 10.1s
  Testing idle timeout 10.0s... ✅ OK (10.1s)
  Testing idle timeout 11.0s... ❌ Failed (HTTP 504) after 10.1s
🎯 Final result for Idle Timeout / proxy_read_timeout: Confirmed limit around ~10.0s (Proxy drops at 11.0s)

--- Finding Limit for: Upload Size ---
  Testing upload 1.0 MB... ✅ OK (0.5s @ 2.0 MB/s)
  Testing upload 2.0 MB... ❌ Failed (HTTP 413) after 0.1s
  Testing upload 1.5 MB... ✅ OK (0.7s @ 2.1 MB/s)
  Testing upload 1.7 MB... ❌ Failed (HTTP 413) after 0.1s
🎯 Final result for Upload Size: Confirmed limit around ~1.5 MB (Proxy drops at 1.7 MB)

--- Finding Limit for: Download Size ---
  Testing download 5.0 MB... ✅ OK (0.2s @ 25.0 MB/s)
  Testing download 10.0 MB... ✅ OK (0.4s @ 25.0 MB/s)
  Testing download 20.0 MB... ✅ OK (0.8s @ 25.0 MB/s)
  Testing download 40.0 MB... ✅ OK (1.6s @ 25.0 MB/s)
  Testing download 80.0 MB... ❌ Failed (HTTP 502) after 3.2s
  Testing download 60.0 MB... ✅ OK (2.4s @ 25.0 MB/s)
  Testing download 70.0 MB... ❌ Failed (HTTP 502) after 2.8s
🎯 Final result for Download Size: Confirmed limit around ~60.0 MB (Proxy drops at 70.0 MB)

=======================================================
 SUMMARY OF DISCOVERED PROXY LIMITS
=======================================================
 • Idle Timeout (proxy_read_timeout) : ~10.0s
 • Max Upload Size (client_max_body) : ~1.5 MB
 • Median Upload Speed               : 2.0 MB/s
 • Max Download Size                 : ~60.0 MB
 • Median Download Speed             : 25.0 MB/s
 • Max Request Duration (Active)     : >=2.4s
=======================================================
```

## Credits
This very small project was entirely generated using AI via **Google Antigravity**.
