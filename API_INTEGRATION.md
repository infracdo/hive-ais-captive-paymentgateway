# API Integration - Apollo Captive Payment Gateway

## Overview

The captive payment gateway now integrates with the Apollo Device Provisioner API to fetch user session details based on their IP address.

## Implementation Details

### 1. Configuration Updates

**File:** `app/config.py`

Added new environment variables:
- `APOLLO_PROVISIONER_URL` - Base URL (default: `http://10.42.4.19:8000`)
- `APOLLO_PROVISIONER_API_PREFIX` - API prefix (default: `/api/v1`)
- `APOLLO_PROVISIONER_TIMEOUT` - Request timeout in seconds (default: 10)

**File:** `.env.example`

Updated with new variables:
```bash
APOLLO_PROVISIONER_URL=http://10.42.4.19:8000
APOLLO_PROVISIONER_API_PREFIX=/api/v1
APOLLO_PROVISIONER_TIMEOUT=10
```

### 2. API Integration Function

**File:** `app/main.py`

Added `get_user_by_ip(client_ip: str)` function that:
- Queries the accounting API: `/api/v1/accounting/requests/by-ip/framed/{ip}`
- Uses query parameters: `acct_status_type=Start` and `count=1`
- Returns the latest accounting record for the IP
- Handles timeouts and errors gracefully
- Comprehensive logging for debugging

**Function Flow:**
```python
1. Extract client IP from request headers (X-Forwarded-For)
2. Call API: GET {PROVISIONER_URL}/api/v1/accounting/requests/by-ip/framed/{client_ip}?acct_status_type=Start&count=1
3. Parse response and extract user details
4. Return user data or None if not found
```

### 3. User Data Retrieved

When a user is found, the following information is available:
- `user_name` - PPPoE username
- `acct_session_id` - Current session ID
- `framed_ip_address` - Assigned IP address
- `calling_station_id` - MAC address
- `nas_identifier` - Router/NAS name (e.g., "MikroTik")
- `nas_ip_address` - Router IP
- `acct_status_type` - Session status (Start/Stop/Alive)
- `created_at` - Session start time
- `updated_at` - Last update time

### 4. Template Updates

**File:** `app/templates/payment.html`

Updated to display:
- Username
- Session ID
- Assigned IP
- MAC address
- Connected router (NAS)
- Session status
- Account status (OVERDUE)

Shows informative message if user not found in accounting records.

## API Call Example

### Request
```bash
GET http://10.42.4.19:8000/api/v1/accounting/requests/by-ip/framed/10.88.0.2?acct_status_type=Start&count=1
```

### Response
```json
{
  "total": 1,
  "items": [
    {
      "id": 123,
      "user_name": "user002",
      "acct_session_id": "812006a2",
      "framed_ip_address": "10.88.0.2",
      "calling_station_id": "E0:07:C2:CE:D2:86",
      "nas_identifier": "MikroTik",
      "nas_ip_address": "10.42.3.28",
      "acct_status_type": "Start",
      "created_at": "2025-11-07T09:09:12.123456",
      "updated_at": "2025-11-07T09:09:12.123456"
    }
  ],
  "page": 1,
  "page_size": 1,
  "total_pages": 1
}
```

## Logging Output

The application provides detailed logging for debugging:

### Client Request Logging
```
================================================================================
📥 INCOMING REQUEST
  Method: GET
  URL: http://captive.portal/
  Client: 10.88.0.1:12345
  Headers: {...}
================================================================================
🔍 CLIENT INFORMATION EXTRACTED:
  📍 Client IP: 10.88.0.2
  🌐 User Agent: Mozilla/5.0...
  🏠 Host: connectivitycheck.gstatic.com
  📂 Path: /generate_204
  ⏰ Timestamp: 2025-11-07T09:09:12.359787
================================================================================
```

### API Query Logging
```
================================================================================
🔍 QUERYING APOLLO DEVICE PROVISIONER API
  API URL: http://10.42.4.19:8000/api/v1/accounting/requests/by-ip/framed/10.88.0.2
  Client IP: 10.88.0.2
  Timeout: 10s
  Response Status: 200
  Total Records: 1
  ✅ USER FOUND:
    Username: user002
    Session ID: 812006a2
    NAS IP: 10.42.3.28
    MAC Address: E0:07:C2:CE:D2:86
    Assigned IP: 10.88.0.2
    Status: Start
================================================================================
```

## Error Handling

The integration handles various error scenarios:

1. **API Timeout** - Returns None, displays generic payment page
2. **API Connection Error** - Returns None, shows message to contact support
3. **User Not Found** - Returns None, shows informative alert
4. **Invalid Response** - Returns None, logs error details

All errors are logged with full details for troubleshooting.

## Testing

### 1. Start Apollo Device Provisioner
```bash
cd /home/mcandres/sandbox/APOLLO/apollo-device-provisioner
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Captive Payment Gateway
```bash
cd /home/mcandres/sandbox/APOLLO/apollo-captive-paymentgateway
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 3. Test User Lookup
```bash
# Test with a known IP from accounting records
curl http://localhost:8080/ -H "X-Forwarded-For: 10.88.0.2"
```

### 4. Check Logs
Monitor both applications for detailed logging:
- Device Provisioner: API request logs
- Payment Gateway: Client extraction and API query logs

## Docker Deployment

The application is Docker-ready with docker-compose.yml:

```bash
# Build and push to Docker Hub
./docker-build-push.sh 1.1.0

# Run with docker-compose
docker-compose up -d
```

Environment variables are configured in `.env` file or docker-compose.yml.

## Next Steps

- ✅ API integration implemented
- ✅ User session display on payment page
- ✅ Comprehensive logging for debugging
- ⏭️ Add QR code generation for payment
- ⏭️ Integrate with actual payment system API
- ⏭️ Add payment status verification
- ⏭️ Auto-restore service after payment confirmation

## Architecture Flow

```
Client (10.88.0.2)
    ↓ HTTP Request
MikroTik Router (adds X-Forwarded-For: 10.88.0.2)
    ↓ Proxy
Payment Gateway (port 8080)
    ├─ Extract client IP from X-Forwarded-For
    ├─ Query API: GET /api/v1/accounting/requests/by-ip/framed/10.88.0.2
    ↓
Device Provisioner API (port 8000)
    ├─ Query PostgreSQL accounting table
    ├─ Return user session details
    ↓
Payment Gateway
    └─ Render payment.html with user details
```
