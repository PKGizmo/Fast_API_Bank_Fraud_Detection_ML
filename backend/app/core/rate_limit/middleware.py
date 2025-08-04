from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Tuple
import time
from datetime import datetime, timedelta, timezone
from backend.app.core.rate_limit.config import (
    DEFAULT_RATE_LIMITS,
    RateLimitConfig,
    RATE_LIMIT_WHITELIST,
)
from backend.app.core.rate_limit.models import RateLimitLog
from backend.app.core.logging import get_logger
from backend.app.core.db import engine
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import jwt
from backend.app.core.config import settings

logger = get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    # ASGI - Asynchronous Server Gateway Interface
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        try:
            from redis import Redis

            self.redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
            self.redis_client.ping()
            logger.info("Successfully connected to Redis for rate limiting")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def _get_rate_limit_key(self, request: Request, endpoint: str) -> str:
        """
        Private method to generate unique key for the rate limiting based on
        the endpoint, the IP address and the user ID.
        """
        try:
            ip = request.client.host if request.client else "anonymous"

            access_token = request.cookies.get(settings.COOKIE_ACCESS_NAME)

            # If we get access token, it means that the user is authenticated
            if access_token:
                try:
                    payload = jwt.decode(
                        access_token,
                        settings.SIGNING_KEY,
                        algorithms=[settings.JWT_ALGORITHM],
                    )
                    user_id = payload.get("id")
                    key = f"ratelimit:{endpoint}:{ip}:{user_id}"
                except jwt.InvalidTokenError:
                    key = f"ratelimit:{endpoint}:{ip}"
            else:
                key = f"ratelimit:{endpoint}:{ip}"
            return key
        except Exception:
            return f"ratelimit:{endpoint}:{ip}"

    async def _get_limit_config(self, endpoint: str) -> RateLimitConfig:
        return DEFAULT_RATE_LIMITS.get(endpoint, DEFAULT_RATE_LIMITS["default"])

    async def _check_rate_limit(
        self, key: str, config: RateLimitConfig
    ) -> Tuple[bool, int | None, datetime | None]:
        try:
            pipe = self.redis_client.pipeline()
            current_count = int(str(self.redis_client.get(key) or 0))

            # The Time to Leave
            ttl = self.redis_client.ttl(key)

            if current_count >= config.max_requests:
                if config.block_on_exceed:
                    block_until = datetime.now(timezone.utc) + timedelta(
                        seconds=(
                            float(str(ttl))
                            if float(str(ttl)) > 0
                            else config.window_seconds
                        ),
                    )

                    return True, current_count, block_until
                return True, current_count, None

            # If ttl == -2 it means that the key doesn't exist
            if ttl == -2:
                pipe.setex(key, config.window_seconds, 1)
            else:
                pipe.incr(key)
            pipe.execute()

            return False, (current_count + 1), None

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return False, None, None

    async def _log_violation(
        self,
        request: Request,
        endpoint: str,
        count: int,
        blocked_until: datetime | None,
        session: AsyncSession,
    ):
        try:
            user_id = None
            access_token = request.cookies.get(settings.COOKIE_ACCESS_NAME)

            if access_token:
                try:
                    payload = jwt.decode(
                        access_token,
                        settings.SIGNING_KEY,
                        algorithms=[settings.JWT_ALGORITHM],
                    )
                    user_id = payload.get("id")

                except jwt.InvalidKeyError:
                    pass

            window_start = datetime.now(timezone.utc)
            window_end = (
                blocked_until if blocked_until else window_start + timedelta(hours=1)
            )

            violation_log = RateLimitLog(
                ip_address=request.client.host if request.client else "unknown",
                user_id=user_id,
                endpoint=endpoint,
                request_count=count,
                request_method=str(request.method),
                request_path=str(request.url.path),
                window_start=window_start,
                window_end=window_end,
                blocked_until=blocked_until,
            )

            session.add(violation_log)
            await session.commit()
            await session.refresh(violation_log)

            logger.info(
                f"Rate limit violation logged for the IP: {violation_log.ip_address}",
                f"User ID: {violation_log.user_id}, Endpoint: {violation_log.endpoint}",
            )

        except Exception as e:
            logger.error(f"Failed to log rate limit violations: {str(e)}")
            await session.rollback()
            raise

    async def dispatch(self, request: Request, call_next):
        """
        Main middleware function to process each request
        """
        try:
            endpoint = request.url.path

            if endpoint in RATE_LIMIT_WHITELIST:
                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = "unlimited"
                response.headers["X-RateLimit-Remaining"] = "unlimited"
                return response

            config = await self._get_limit_config(endpoint)

            key = await self._get_rate_limit_key(request, endpoint)

            is_limited, count, blocked_until = await self._check_rate_limit(key, config)

            headers = {
                "X-RateLimit-Limit": str(config.max_requests),
                "X-RateLimit-Remaining": str(
                    max(0, config.max_requests - (count or 0))
                ),
                "X-RateLimit-Reset": str(int(time.time() + config.window_seconds)),
            }

            if is_limited:
                async with AsyncSession(engine) as session:
                    await self._log_violation(
                        request,
                        endpoint,
                        count or 0,
                        blocked_until,
                        session,
                    )

                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "status": "error",
                        "message": "Too many requests",
                        "action": "Please wait before trying again",
                        "retry_after": f"{config.window_seconds} seconds",
                    },
                )

                for header_key, value in headers.items():
                    response.headers[header_key] = value

                if blocked_until:
                    response.headers["Retry-After"] = str(config.window_seconds)
                return response

            response = await call_next(request)

            for header_key, value in headers.items():
                response.headers[header_key] = value
            return response

        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}")
            return await call_next(request)
