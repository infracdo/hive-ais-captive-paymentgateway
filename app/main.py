"""
Apollo Captive Payment Gateway - Main Application

FastAPI application for ISP captive portal payment gateway.
Intercepts overdue customer HTTP requests and displays payment page.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import traceback
from datetime import datetime
import httpx
from typing import Optional

from app.config import settings

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    logger.info("=" * 80)
    logger.info(f"🚀 Starting {settings.APP_NAME}")
    logger.info(f"📌 Version: {settings.APP_VERSION}")
    logger.info(f"🌐 Host: {settings.HOST}:{settings.PORT}")
    logger.info(f"💳 Payment URL: {settings.PAYMENT_URL}")
    logger.info(f"🔧 Provisioner API: {settings.APOLLO_PROVISIONER_URL}")
    logger.info("=" * 80)

    yield

    logger.info("=" * 80)
    logger.info(f"🛑 Shutting down {settings.APP_NAME}")
    logger.info("=" * 80)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Payment portal for overdue ISP customers",
    lifespan=lifespan
)


# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests including invalid ones"""
    try:
        # Log request details
        logger.debug("=" * 80)
        logger.debug(f"📥 INCOMING REQUEST")
        logger.debug(f"  Method: {request.method}")
        logger.debug(f"  URL: {request.url}")
        logger.debug(f"  Client: {request.client.host if request.client else 'Unknown'}:{request.client.port if request.client else 'Unknown'}")
        logger.debug(f"  Headers: {dict(request.headers)}")
        logger.debug("=" * 80)

        response = await call_next(request)
        return response
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ REQUEST PROCESSING ERROR")
        logger.error(f"  Error Type: {type(e).__name__}")
        logger.error(f"  Error Message: {str(e)}")
        logger.error(f"  Method: {request.method if hasattr(request, 'method') else 'Unknown'}")
        logger.error(f"  URL: {request.url if hasattr(request, 'url') else 'Unknown'}")
        logger.error(f"  Client: {request.client.host if hasattr(request, 'client') and request.client else 'Unknown'}")
        logger.error(f"  Traceback: {traceback.format_exc()}")
        logger.error("=" * 80)
        raise


# Exception handlers for invalid requests
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with detailed logging"""
    logger.warning("=" * 80)
    logger.warning(f"⚠️  HTTP EXCEPTION: {exc.status_code}")
    logger.warning(f"  Detail: {exc.detail}")
    logger.warning(f"  Method: {request.method}")
    logger.warning(f"  URL: {request.url}")
    logger.warning(f"  Client: {request.client.host if request.client else 'Unknown'}")
    logger.warning(f"  Headers: {dict(request.headers)}")
    logger.warning("=" * 80)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging"""
    logger.warning("=" * 80)
    logger.warning(f"⚠️  VALIDATION ERROR")
    logger.warning(f"  Errors: {exc.errors()}")
    logger.warning(f"  Body: {exc.body}")
    logger.warning(f"  Method: {request.method}")
    logger.warning(f"  URL: {request.url}")
    logger.warning(f"  Client: {request.client.host if request.client else 'Unknown'}")
    logger.warning(f"  Headers: {dict(request.headers)}")
    logger.warning("=" * 80)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "details": exc.errors()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with detailed logging"""
    logger.error("=" * 80)
    logger.error(f"❌ UNHANDLED EXCEPTION: {type(exc).__name__}")
    logger.error(f"  Message: {str(exc)}")
    logger.error(f"  Method: {request.method}")
    logger.error(f"  URL: {request.url}")
    logger.error(f"  Client: {request.client.host if request.client else 'Unknown'}")
    logger.error(f"  Headers: {dict(request.headers)}")
    logger.error(f"  Traceback:")
    for line in traceback.format_exc().split('\n'):
        if line.strip():
            logger.error(f"    {line}")
    logger.error("=" * 80)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")


def extract_client_info(request: Request) -> dict:
    """
    Extract client information from request headers.
    Logs all incoming headers for debugging.

    Returns:
        dict: Client information including IP, user agent, etc.
    """
    # Log all headers for debugging
    logger.debug("=" * 80)
    logger.debug("📨 INCOMING REQUEST HEADERS:")
    for header_name, header_value in request.headers.items():
        logger.debug(f"  {header_name}: {header_value}")
    logger.debug("=" * 80)

    # Extract client IP from various proxy headers (MikroTik sends X-Forwarded-For)
    x_forwarded_for = request.headers.get("X-Forwarded-For", "")
    client_ip = (
        x_forwarded_for.split(",")[0].strip() if x_forwarded_for else
        request.headers.get("X-Real-IP") or
        request.headers.get("CF-Connecting-IP") or
        request.headers.get("True-Client-IP") or
        request.client.host if request.client else "unknown"
    )

    # Extract other useful info
    user_agent = request.headers.get("User-Agent", "Unknown")
    host = request.headers.get("Host", "")
    referer = request.headers.get("Referer", "")

    client_info = {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "host": host,
        "referer": referer,
        "path": request.url.path,
        "query": str(request.url.query) if request.url.query else "",
        "timestamp": datetime.now().isoformat()
    }

    # Log extracted client information
    logger.info("=" * 80)
    logger.info("🔍 CLIENT INFORMATION EXTRACTED:")
    logger.info(f"  📍 Client IP: {client_info['client_ip']}")
    logger.info(f"  🌐 User Agent: {client_info['user_agent']}")
    logger.info(f"  🏠 Host: {client_info['host']}")
    logger.info(f"  📂 Path: {client_info['path']}")
    if client_info['query']:
        logger.info(f"  ❓ Query: {client_info['query']}")
    logger.info(f"  ⏰ Timestamp: {client_info['timestamp']}")
    logger.info("=" * 80)

    return client_info


async def get_user_by_ip(client_ip: str) -> Optional[dict]:
    """
    Query Apollo Device Provisioner API to get user details by IP address.

    Args:
        client_ip: Client's IP address from framed_ip_address

    Returns:
        dict: User accounting details or None if not found
    """
    try:
        api_url = f"{settings.APOLLO_PROVISIONER_URL}{settings.APOLLO_PROVISIONER_API_PREFIX}/accounting/requests/by-ip/framed/{client_ip}"

        logger.info("=" * 80)
        logger.info("🔍 QUERYING APOLLO DEVICE PROVISIONER API")
        logger.info(f"  API URL: {api_url}")
        logger.info(f"  Client IP: {client_ip}")
        logger.info(f"  Timeout: {settings.APOLLO_PROVISIONER_TIMEOUT}s")

        async with httpx.AsyncClient(timeout=settings.APOLLO_PROVISIONER_TIMEOUT) as client:
            response = await client.get(
                api_url,
                params={
                    "acct_status_type": "Start",
                    "count": 1
                }
            )

            logger.info(f"  Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"  Total Records: {data.get('total', 0)}")

                if data.get('items') and len(data['items']) > 0:
                    user_data = data['items'][0]
                    logger.info("  ✅ USER FOUND:")
                    logger.info(f"    Username: {user_data.get('user_name')}")
                    logger.info(f"    Session ID: {user_data.get('acct_session_id')}")
                    logger.info(f"    NAS IP: {user_data.get('nas_ip_address')}")
                    logger.info(f"    MAC Address: {user_data.get('calling_station_id')}")
                    logger.info(f"    Assigned IP: {user_data.get('framed_ip_address')}")
                    logger.info(f"    Status: {user_data.get('acct_status_type')}")
                    logger.info("=" * 80)
                    return user_data
                else:
                    logger.warning("  ⚠️  No user found for this IP address")
                    logger.info("=" * 80)
                    return None
            else:
                logger.error(f"  ❌ API Error: {response.status_code}")
                logger.error(f"  Response: {response.text}")
                logger.info("=" * 80)
                return None

    except httpx.TimeoutException:
        logger.error("=" * 80)
        logger.error("❌ API TIMEOUT")
        logger.error(f"  API URL: {api_url}")
        logger.error(f"  Timeout: {settings.APOLLO_PROVISIONER_TIMEOUT}s")
        logger.error("=" * 80)
        return None
    except httpx.RequestError as e:
        logger.error("=" * 80)
        logger.error("❌ API REQUEST ERROR")
        logger.error(f"  API URL: {api_url}")
        logger.error(f"  Error: {str(e)}")
        logger.error("=" * 80)
        return None
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ UNEXPECTED ERROR QUERYING API")
        logger.error(f"  API URL: {api_url}")
        logger.error(f"  Error Type: {type(e).__name__}")
        logger.error(f"  Error Message: {str(e)}")
        logger.error(f"  Traceback: {traceback.format_exc()}")
        logger.error("=" * 80)
        return None


def is_captive_portal_check(path: str) -> bool:
    """
    Check if the request is a captive portal detection request.

    Args:
        path: Request URL path

    Returns:
        bool: True if this is a captive portal check
    """
    captive_portal_paths = [
        "/generate_204",          # Android, Chrome
        "/gen_204",               # Android alternative
        "/hotspot-detect.html",   # iOS, macOS
        "/connecttest.txt",       # Windows
        "/redirect",              # Generic
        "/success.txt",           # Firefox
        "/canonical.html",        # Ubuntu
    ]
    return path in captive_portal_paths


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/config")
async def get_config():
    """Get current configuration (non-sensitive)"""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "payment_url": settings.PAYMENT_URL,
        "provisioner_url": settings.APOLLO_PROVISIONER_URL
    }


@app.post("/api/clear-overdue")
async def clear_overdue_status(request: Request):
    """
    Proxy endpoint to clear overdue status for a user.
    This acts as an intermediary to the device provisioner API.

    Expects JSON body: {"username": "user002"}
    """
    try:
        # Parse request body
        body = await request.json()
        username = body.get("username")

        if not username:
            logger.error("❌ Clear overdue request missing username")
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Username is required"}
            )

        # Build API URL
        api_url = f"{settings.APOLLO_PROVISIONER_URL}{settings.APOLLO_PROVISIONER_API_PREFIX}/pppoe/users/{username}/clear-overdue"

        logger.info("=" * 80)
        logger.info("💳 CLEARING OVERDUE STATUS")
        logger.info(f"  Username: {username}")
        logger.info(f"  API URL: {api_url}")
        logger.info(f"  Client IP: {request.client.host if request.client else 'Unknown'}")

        # Call the device provisioner API
        async with httpx.AsyncClient(timeout=settings.APOLLO_PROVISIONER_TIMEOUT) as client:
            response = await client.post(api_url)

            logger.info(f"  Response Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info("  ✅ OVERDUE STATUS CLEARED SUCCESSFULLY")
                logger.info(f"  Result: {result}")
                logger.info("=" * 80)

                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Payment processed successfully. Your service will be restored shortly.",
                        "username": username,
                        "data": result
                    }
                )
            else:
                error_text = response.text
                logger.error(f"  ❌ API Error: {response.status_code}")
                logger.error(f"  Response: {error_text}")
                logger.info("=" * 80)

                return JSONResponse(
                    status_code=response.status_code,
                    content={
                        "success": False,
                        "error": f"Failed to process payment: {error_text}",
                        "username": username
                    }
                )

    except httpx.TimeoutException:
        logger.error("=" * 80)
        logger.error("❌ API TIMEOUT - Clear Overdue")
        logger.error(f"  API URL: {api_url}")
        logger.error(f"  Timeout: {settings.APOLLO_PROVISIONER_TIMEOUT}s")
        logger.error("=" * 80)

        return JSONResponse(
            status_code=504,
            content={
                "success": False,
                "error": "Payment processing timeout. Please try again."
            }
        )

    except httpx.RequestError as e:
        logger.error("=" * 80)
        logger.error("❌ API REQUEST ERROR - Clear Overdue")
        logger.error(f"  Error: {str(e)}")
        logger.error("=" * 80)

        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": "Unable to connect to payment service. Please try again later."
            }
        )

    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ UNEXPECTED ERROR - Clear Overdue")
        logger.error(f"  Error Type: {type(e).__name__}")
        logger.error(f"  Error Message: {str(e)}")
        logger.error(f"  Traceback: {traceback.format_exc()}")
        logger.error("=" * 80)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "An unexpected error occurred. Please contact support."
            }
        )


@app.get("/", response_class=HTMLResponse)
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def payment_portal(request: Request, full_path: str = ""):
    """
    Main payment portal handler.
    Catches all HTTP requests and displays payment page.
    Queries Apollo Device Provisioner API to get user details by IP.
    """
    # Extract and log client info
    client_info = extract_client_info(request)

    # Check if this is a captive portal detection request
    if is_captive_portal_check(client_info['path']):
        logger.info(f"🔍 Captive portal detection request from {client_info['client_ip']}")

    # Query device-provisioner API to get user details by IP
    user_details = await get_user_by_ip(client_info['client_ip'])

    # Render payment page using Jinja2 template
    return templates.TemplateResponse(
        "payment.html",
        {
            "request": request,
            "app_name": settings.APP_NAME,
            "payment_url": settings.PAYMENT_URL,
            "client_info": client_info,
            "user": user_details
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG
    )
