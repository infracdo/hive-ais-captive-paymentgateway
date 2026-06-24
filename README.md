# Apollo Captive Payment Gateway

FastAPI-based captive portal payment gateway for ISP customers with overdue accounts. Uses the same MaterialAdmin theme as apollo-customer-manager for consistent UI/UX across the Apollo platform.

## Architecture

```
apollo-captive-paymentgateway/
├── app/
│   ├── __init__.py
│   ├── config.py           # Application configuration
│   ├── main.py             # FastAPI application
│   ├── templates/
│   │   ├── base.html       # Base template with MaterialAdmin theme
│   │   └── payment.html    # Payment portal page
│   └── static/             # Additional static files (if needed)
├── materialadmin/          # MaterialAdmin theme assets
│   ├── css/
│   ├── js/
│   ├── fonts/
│   └── img/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── start.sh                # Development start script
└── README.md
```

## Features

✅ **FastAPI Framework** - Modern, async, production-ready web framework  
✅ **Jinja2 Templating** - Server-side rendering with template inheritance  
✅ **MaterialAdmin Theme** - Beautiful, responsive UI matching apollo-customer-manager  
✅ **Captive Portal Detection** - Automatic detection for all major platforms (Android, iOS, Windows, macOS)  
✅ **HTTP Header Debugging** - Comprehensive logging of all incoming headers  
✅ **Client IP Extraction** - Handles X-Forwarded-For, X-Real-IP, and other proxy headers  
✅ **Health Check Endpoint** - `/health` for Docker/Kubernetes monitoring  
✅ **Configuration Endpoint** - `/api/config` for runtime configuration access  
✅ **Docker Ready** - Multi-stage build for minimal production images  
✅ **Environment Variables** - Flexible configuration via .env file  

## Quick Start

### 1. Local Development

```bash
cd /home/mcandres/sandbox/APOLLO/apollo-captive-paymentgateway

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Install dependencies
pip install -r requirements.txt

# Run with start script
./start.sh

# Or run directly with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Access the application at `http://localhost:8080`

### 2. Docker Build

```bash
docker build -t apollo-captive-paymentgateway .
```

### 3. Docker Run

```bash
docker run -d \
  --name apollo-captive-paymentgateway \
  --restart unless-stopped \
  -p 8080:8080 \
  -e PAYMENT_URL=https://www.coronatel.com/ \
  -e APOLLO_PROVISIONER_URL=http://10.42.4.19:5000/api/v1 \
  apollo-captive-paymentgateway
```

### 4. Docker Compose

```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Apollo Captive Payment Gateway | Application name |
| `APP_VERSION` | 1.0.0 | Application version |
| `DEBUG` | True | Enable debug mode |
| `LOG_LEVEL` | DEBUG | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 8080 | Server port |
| `PAYMENT_URL` | https://www.coronatel.com/ | Payment portal URL |
| `APOLLO_PROVISIONER_URL` | http://10.42.4.19:5000/api/v1 | Device provisioner API URL |
| `APOLLO_PROVISIONER_TIMEOUT` | 10 | API timeout in seconds |

## API Endpoints

### Payment Portal
- **GET** `/` - Main payment portal (HTML)
- **GET** `/{any_path}` - Catches all routes, displays payment page (HTML)

### Health & Config
- **GET** `/health` - Health check endpoint (JSON)
- **GET** `/api/config` - Current configuration (JSON)

### Auto-Generated Documentation
- **GET** `/docs` - Swagger UI (interactive API docs)
- **GET** `/redoc` - ReDoc (alternative API documentation)

## MikroTik Integration

Configure your MikroTik router to redirect HTTP traffic from overdue users:

```routeros
# Add NAT rule to redirect HTTP traffic
/ip firewall nat add \
  chain=dstnat \
  protocol=tcp \
  dst-port=80 \
  src-address-list=overdue-customers \
  action=dst-nat \
  to-addresses=10.42.4.19 \
  to-ports=8080 \
  comment="Captive Portal - Overdue Customers"

# Block HTTPS to force HTTP usage
/ip firewall filter add \
  chain=forward \
  protocol=tcp \
  dst-port=443 \
  src-address-list=overdue-customers \
  action=drop \
  comment="Block HTTPS for Overdue Customers"
```

## HTTP Header Debugging

The application logs all incoming HTTP headers for troubleshooting. This is especially useful for verifying that MikroTik is sending the correct X-Forwarded-For header.

Example log output:
```
================================================================================
📨 INCOMING REQUEST HEADERS:
  host: 10.42.4.19:8080
  x-forwarded-for: 10.88.1.100
  user-agent: Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36
  accept: text/html,application/xhtml+xml
================================================================================
🔍 CLIENT INFORMATION EXTRACTED:
  📍 Client IP: 10.88.1.100
  🌐 User Agent: Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36
  🏠 Host: 10.42.4.19:8080
  📂 Path: /generate_204
  ⏰ Timestamp: 2025-11-07T10:30:45.123456
================================================================================
🔍 Captive portal detection request from 10.88.1.100
```

## Captive Portal Detection

The application automatically detects captive portal check requests from various platforms:

| Platform | Detection URL |
|----------|---------------|
| Android, Chrome | `/generate_204`, `/gen_204` |
| iOS, macOS | `/hotspot-detect.html` |
| Windows | `/connecttest.txt` |
| Firefox | `/success.txt` |
| Ubuntu | `/canonical.html` |

When a device sends a request to any of these URLs, the gateway returns HTTP 200 with the payment page instead of the expected HTTP 204, triggering the device's captive portal browser.

## Extending the Application

### Get User Details by IP

To show personalized payment information, add user lookup functionality:

```python
# Add to app/main.py

import httpx

async def get_user_by_ip(client_ip: str):
    """Query apollo-device-provisioner for user details by IP"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.APOLLO_PROVISIONER_URL}/pppoe/users/by-ip/{client_ip}"
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Error fetching user by IP {client_ip}: {e}")
    return None

# Update payment_portal function
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def payment_portal(request: Request, full_path: str = ""):
    client_info = extract_client_info(request)
    
    # Get user details by IP
    user_details = await get_user_by_ip(client_info['client_ip'])
    
    return templates.TemplateResponse(
        "payment.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "payment_url": settings.PAYMENT_URL,
            "client_info": client_info,
            "user": user_details  # Pass user data to template
        }
    )
```

### Generate Payment QR Codes

Add QR code generation for personalized payment:

```python
# Install: pip install qrcode[pil]

import qrcode
import io
import base64

def generate_payment_qr(username: str, amount: float, reference: str) -> str:
    """Generate payment QR code"""
    # Create payment data (format depends on your payment gateway)
    payment_data = f"PAYMENT:{username}:{amount}:{reference}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(payment_data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str

# Use in payment_portal function
if user_details:
    user_details['qr_code'] = generate_payment_qr(
        user_details['username'],
        user_details['amount_due'],
        user_details['reference_number']
    )
```

The template (`payment.html`) already includes QR code display:
```html
{% if user.qr_code %}
<div class="info-section text-center">
    <h4><i class="md md-camera"></i> Scan to Pay</h4>
    <img src="data:image/png;base64,{{ user.qr_code }}" alt="Payment QR Code">
</div>
{% endif %}
```

## Docker Hub Deployment

### 1. Tag the Image

```bash
# Replace 'yourusername' with your Docker Hub username
docker tag apollo-captive-paymentgateway yourusername/apollo-captive-paymentgateway:latest
docker tag apollo-captive-paymentgateway yourusername/apollo-captive-paymentgateway:1.0.0
```

### 2. Login to Docker Hub

```bash
docker login
```

### 3. Push to Docker Hub

```bash
docker push yourusername/apollo-captive-paymentgateway:latest
docker push yourusername/apollo-captive-paymentgateway:1.0.0
```

### 4. Pull and Run on Production

```bash
# Pull latest image
docker pull yourusername/apollo-captive-paymentgateway:latest

# Run container
docker run -d \
  --name apollo-captive-paymentgateway \
  --restart unless-stopped \
  -p 10.42.4.19:8080:8080 \
  -e PAYMENT_URL=https://www.coronatel.com/ \
  -e APOLLO_PROVISIONER_URL=http://10.42.4.19:5000/api/v1 \
  -e LOG_LEVEL=INFO \
  yourusername/apollo-captive-paymentgateway:latest
```

## Project Structure Details

### app/config.py
Application configuration using Pydantic Settings. Loads from environment variables and .env file.

### app/main.py
Main FastAPI application with:
- Lifespan context manager for startup/shutdown
- Static files mounting (MaterialAdmin theme)
- Jinja2 templates configuration
- Client info extraction with header logging
- Captive portal detection
- Payment portal route handler

### app/templates/base.html
Base template with MaterialAdmin theme. Includes:
- Responsive CSS framework
- Material Design icons
- Beautiful gradient backgrounds
- Animation effects

### app/templates/payment.html
Payment portal page extending base.html. Features:
- Account status warning
- Payment instructions
- User-specific information display
- QR code display (when available)
- Contact information
- Debug information section
- Auto-refresh every 2 minutes

## Troubleshooting

### Issue: Static files not loading
**Solution:** Verify materialadmin directory exists and contains css/, js/, fonts/, img/ subdirectories.

```bash
ls -la materialadmin/
```

### Issue: Client IP shows as 127.0.0.1
**Solution:** Check MikroTik NAT configuration. Ensure X-Forwarded-For header is being sent by adding:
```routeros
/ip firewall mangle add \
  chain=prerouting \
  action=mark-routing \
  src-address-list=overdue-customers
```

### Issue: Captive portal not triggering
**Solution:** 
1. Verify HTTP (port 80) is redirected, not HTTPS (443)
2. Check device is in overdue-customers address list
3. Test with curl: `curl -v http://google.com` (should redirect to payment page)

### Issue: Templates not found
**Solution:** Run from project root directory where app/ directory is located:
```bash
cd /home/mcandres/sandbox/APOLLO/apollo-captive-paymentgateway
python -m uvicorn app.main:app
```

### Issue: Module import errors
**Solution:** Install dependencies and run as module:
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app
```

## Development

### Project Standards
This project follows the same structure as apollo-customer-manager:
- FastAPI for web framework
- Jinja2 for templating
- MaterialAdmin for UI theme
- Pydantic Settings for configuration
- Docker multi-stage builds for production

### Adding New Features
1. Update `app/main.py` with new endpoints
2. Create templates in `app/templates/`
3. Update `requirements.txt` if adding dependencies
4. Update Dockerfile if needed
5. Test locally before building Docker image
6. Update this README with documentation

## License

Part of the Apollo ISP Management Platform.

## Support

For issues or questions, contact CoronaTel support.

---

**Apollo Captive Payment Gateway** - Seamless payment portal for ISP customer management.
