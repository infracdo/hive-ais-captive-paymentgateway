# Getting Client IP from MikroTik NAT Redirect

## Problem
When MikroTik redirects HTTP traffic using NAT, the FastAPI server sees the MikroTik router's IP instead of the actual client IP.

## Solution: MikroTik Web Proxy (RECOMMENDED)

Use MikroTik's built-in web proxy which automatically adds `X-Forwarded-For` headers.

### Architecture
```
Client (10.88.1.100) 
  ↓ HTTP request
MikroTik Web Proxy (port 8888)
  ↓ Adds X-Forwarded-For: 10.88.1.100
  ↓ Forwards to parent-proxy
FastAPI Server (10.42.4.19:8080)
  ↓ Extracts client IP from X-Forwarded-For
Payment Page Displayed
```

## Setup Instructions

### 1. Enable MikroTik Web Proxy

Configure MikroTik's built-in web proxy to forward requests with X-Forwarded-For headers:

```routeros
# Enable MikroTik web proxy
/ip proxy
set enabled=yes \
    port=8888 \
    parent-proxy=10.42.4.19 \
    parent-proxy-port=8080

# Optional: Adjust cache and access settings
/ip proxy
set max-cache-size=unlimited \
    cache-administrator=admin@example.com \
    cache-on-disk=no
```

### 2. Create Address List for Overdue Customers

```routeros
# Create address list for overdue customers
/ip firewall address-list
add list=overdue-customers address=10.88.1.100 comment="Test overdue user"
add list=overdue-customers address=10.88.1.0/24 comment="Overdue subnet"
```

### 3. Redirect HTTP Traffic to Proxy

```routeros
# Redirect HTTP to local MikroTik proxy
/ip firewall nat
add chain=dstnat \
    protocol=tcp \
    dst-port=80 \
    src-address-list=overdue-customers \
    action=redirect \
    to-ports=8888 \
    comment="Redirect to MikroTik proxy with X-Forwarded-For"

# Block HTTPS for overdue customers
/ip firewall filter
add chain=forward \
    protocol=tcp \
    dst-port=443 \
    src-address-list=overdue-customers \
    action=drop \
    comment="Block HTTPS for overdue"
```

### 4. Start FastAPI Payment Gateway

```bash
cd /home/mcandres/sandbox/APOLLO/apollo-captive-paymentgateway

# Using Docker Compose
docker-compose up -d

# Or using Docker directly
docker run -d \
  --name apollo-captive-paymentgateway \
  --restart unless-stopped \
  -p 8080:8080 \
  -e PAYMENT_URL=https://www.coronatel.com/ \
  marcandres888/apollo-captive-paymentgateway:latest
```

### 5. Verify Client IP is Forwarded

Watch the FastAPI logs:

```bash
docker logs -f apollo-captive-paymentgateway
```

You should see:

```
================================================================================
📨 INCOMING REQUEST HEADERS:
  host: 10.42.4.19:8080
  x-forwarded-for: 10.88.1.100    ← Original client IP!
  user-agent: Mozilla/5.0 ...
  via: 1.1 MikroTik-HttpProxy      ← Shows MikroTik proxy was used
================================================================================
🔍 CLIENT INFORMATION EXTRACTED:
  📍 Client IP: 10.88.1.100        ← Correctly extracted!
  🌐 User Agent: Mozilla/5.0 ...
================================================================================
```

## How It Works

### MikroTik Web Proxy

When enabled, MikroTik's web proxy automatically:

1. **Intercepts** HTTP requests from clients in the overdue-customers list
2. **Adds** `X-Forwarded-For` header with the original client IP
3. **Adds** `Via` header showing it passed through MikroTik proxy
4. **Forwards** the request to the parent proxy (FastAPI server)
5. **Returns** the response back to the client

### FastAPI Extraction

The FastAPI app already extracts client IP from these headers (in priority order):

1. `X-Forwarded-For` (first IP in comma-separated list) ← **Used with MikroTik proxy**
2. `X-Real-IP`
3. `CF-Connecting-IP` (Cloudflare)
4. `True-Client-IP`
5. `request.client.host` (fallback)

### Configuration Details

**Parent Proxy Settings:**
- `parent-proxy=10.42.4.19` - IP address of FastAPI server
- `parent-proxy-port=8080` - Port where FastAPI is listening

**Why This Works:**
- ✅ MikroTik proxy automatically adds X-Forwarded-For header
- ✅ No additional software needed (uses built-in MikroTik feature)
- ✅ Simple configuration
- ✅ Works immediately after enabling

## Alternative: NGINX Reverse Proxy

If you prefer using NGINX instead of MikroTik proxy, see the alternative configuration below.

```routeros
## Alternative: NGINX Reverse Proxy

If you prefer using NGINX instead of MikroTik proxy, you can use the NGINX setup:

### NGINX Configuration Files

- `nginx.conf` - NGINX configuration with X-Forwarded-For support
- `docker-compose-nginx.yml` - Docker Compose with NGINX + FastAPI

### Setup with NGINX

```bash
cd /home/mcandres/sandbox/APOLLO/apollo-captive-paymentgateway

# Start with NGINX proxy
docker-compose -f docker-compose-nginx.yml up -d
```

### MikroTik Configuration for NGINX

```routeros
# Redirect HTTP to NGINX (port 8082)
/ip firewall nat
add chain=dstnat \
    protocol=tcp \
    dst-port=80 \
    src-address-list=overdue-customers \
    action=dst-nat \
    to-addresses=10.42.4.19 \
    to-ports=8082 \
    comment="Captive Portal - NGINX Proxy"
```

**Architecture with NGINX:**
```
Client → MikroTik NAT → NGINX (8082) → FastAPI (8000)
```
```

MikroTik proxy will automatically add `X-Forwarded-For` headers.

## Troubleshooting

### Issue: Still seeing MikroTik IP

**Check:**
1. MikroTik proxy is enabled: `/ip proxy print`
2. Parent proxy settings are correct: `parent-proxy=10.42.4.19 parent-proxy-port=8080`
3. NAT rule uses `action=redirect to-ports=8888` (not dst-nat)
4. Client is in overdue-customers address list: `/ip firewall address-list print`
5. FastAPI logs show X-Forwarded-For header

**Verify MikroTik Proxy:**
```routeros
/ip proxy print
# Should show: enabled=yes port=8888 parent-proxy=10.42.4.19:8080
```

### Issue: MikroTik proxy not working

**Solution:**
```routeros
# Restart proxy service
/ip proxy
set enabled=no
set enabled=yes

# Check proxy is listening
/ip firewall connection print where dst-port=8888
```

### Issue: Headers not showing in logs

**Check:**
1. FastAPI app logging level is DEBUG
2. Check environment variable: `LOG_LEVEL=DEBUG`
3. Watch logs in real-time: `docker logs -f apollo-captive-paymentgateway`

### Issue: Clients not being redirected

**Check:**
1. Client IP is in address list: `/ip firewall address-list print where list=overdue-customers`
2. NAT rule is active: `/ip firewall nat print where chain=dstnat`
3. Test from client device, not from router itself

## Production Deployment

### Build and push updated image:

```bash
# Rebuild and push to Docker Hub
cd /home/mcandres/sandbox/APOLLO/apollo-captive-paymentgateway
./docker-build-push.sh 1.0.1

# Or manually:
docker build -t marcandres888/apollo-captive-paymentgateway:1.0.1 .
docker push marcandres888/apollo-captive-paymentgateway:1.0.1
```

### Deploy on production:

```bash
# Pull latest image
docker pull marcandres888/apollo-captive-paymentgateway:latest

# Run container
docker run -d \
  --name apollo-captive-paymentgateway \
  --restart unless-stopped \
  -p 8080:8080 \
  -e PAYMENT_URL=https://www.coronatel.com/ \
  -e APOLLO_PROVISIONER_URL=http://10.42.4.19:5000/api/v1 \
  marcandres888/apollo-captive-paymentgateway:latest

# Or use Docker Compose
docker-compose up -d
```

### Complete MikroTik Configuration

```routeros
# 1. Enable web proxy
/ip proxy
set enabled=yes port=8888 \
    parent-proxy=10.42.4.19 parent-proxy-port=8080

# 2. Create overdue customers list
/ip firewall address-list
add list=overdue-customers address=10.88.1.100 comment="Overdue customer"

# 3. Redirect HTTP to proxy
/ip firewall nat
add chain=dstnat protocol=tcp dst-port=80 \
    src-address-list=overdue-customers \
    action=redirect to-ports=8888 \
    comment="Captive Portal via MikroTik Proxy"

# 4. Block HTTPS
/ip firewall filter
add chain=forward protocol=tcp dst-port=443 \
    src-address-list=overdue-customers \
    action=drop comment="Block HTTPS for overdue"
```

## Summary

✅ **MikroTik Web Proxy** automatically adds `X-Forwarded-For` headers  
✅ **FastAPI** extracts client IP from `X-Forwarded-For` header  
✅ **No additional software** needed - uses built-in MikroTik feature  
✅ **Simple setup** - just enable proxy and redirect traffic  
✅ **Logs** show original client IP for debugging  
✅ **Ready** for user lookup by IP and personalized QR codes  

## Quick Reference

### Verify Setup is Working

```bash
# 1. Check MikroTik proxy is enabled
/ip proxy print

# 2. Check address list has overdue customers
/ip firewall address-list print where list=overdue-customers

# 3. Check NAT redirect rule
/ip firewall nat print where chain=dstnat

# 4. Watch FastAPI logs
docker logs -f apollo-captive-paymentgateway

# 5. Test from client device
# Open browser, try to visit any HTTP site
# Should see payment page with correct client IP in logs
```

### Expected Log Output

When working correctly, you'll see:

```
📨 INCOMING REQUEST HEADERS:
  x-forwarded-for: 10.88.1.100     ← Client's real IP
  via: 1.1 MikroTik-HttpProxy      ← Confirms MikroTik proxy
  
🔍 CLIENT INFORMATION EXTRACTED:
  📍 Client IP: 10.88.1.100         ← Correctly extracted!
```

## Why MikroTik Web Proxy Works Best

✅ **Built-in feature** - No extra infrastructure needed  
✅ **Automatic header handling** - MikroTik adds X-Forwarded-For automatically  
✅ **Simpler architecture** - One less service to manage  
✅ **Lower latency** - Direct proxy without extra hops  
✅ **Easier troubleshooting** - Everything managed in MikroTik  
✅ **Production tested** - Confirmed working in your environment
