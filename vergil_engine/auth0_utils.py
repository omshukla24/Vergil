import urllib.parse
import jwt
import requests
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from vergil_engine.config import settings

# ---------- RS256 JWT Verification ----------

security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI dependency that intercepts the Bearer token, fetches Auth0's
    JWKS public keys, and verifies the RS256 signature mathematically.
    Returns the decoded payload on success; raises 401 on any failure.
    """
    token = credentials.credentials
    jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    jwks_client = jwt.PyJWKClient(jwks_url)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ---------- Step-Up / Quorum URL Helpers ----------


def generate_step_up_url(action_id: str, user_id: str, redirect_uri: str) -> str:
    """
    Generates an Auth0 URL forcing Step-Up Authentication.
    We pass `acr_values` to indicate Step-Up requirements.
    """
    params = {
        "response_type": "code",
        "client_id": settings.auth0_client_id,
        "redirect_uri": redirect_uri,
        "audience": settings.auth0_audience,
        "scope": "openid profile email",
        # Custom state to track context during callback
        "state": f"action_id={action_id}&user_id={user_id}",
        # Force Step-up by requesting specific acr_values
        "acr_values": "http://schemas.openid.net/pape/policies/2007/06/none",
        "prompt": "login" # optional: forces re-authentication visually typically
    }
    qs = urllib.parse.urlencode(params)
    return f"https://{settings.auth0_domain}/authorize?{qs}"

def generate_quorum_urls(action_id: str, trustees: list[str], redirect_uri: str) -> dict[str, str]:
    """
    Generates step-up URLs for all trustees involved in a high-stakes quorum.
    """
    urls = {}
    for trustee in trustees:
        # Pass login_hint optionally to direct the specific user
        # params["login_hint"] = trustee
        urls[trustee] = generate_step_up_url(action_id, trustee, redirect_uri)
    return urls

def decode_state(state: str) -> dict[str, str]:
    """
    Helper to parse 'action_id=xxx&user_id=yyy' from state parameter.
    """
    parsed = urllib.parse.parse_qs(state)
    return {k: v[0] for k, v in parsed.items()}
