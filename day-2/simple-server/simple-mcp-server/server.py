import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Create an MCP server
mcp = FastMCP("Simple MCP Server")

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a prompt
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


# --- SailPoint Integration ---

async def get_sailpoint_token() -> Optional[str]:
    """Get OAuth2 token from SailPoint"""
    base_url = os.getenv("SAILPOINT_BASE_URL")
    client_id = os.getenv("SAILPOINT_CLIENT_ID")
    client_secret = os.getenv("SAILPOINT_CLIENT_SECRET")

    if not all([base_url, client_id, client_secret]):
        return None

    url = f"{base_url}/oauth/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=params)
            response.raise_for_status()
            return response.json().get("access_token")
    except Exception as e:
        print(f"Error getting SailPoint token: {e}")
        return None


@mcp.tool()
async def get_identity_details(identity_name: str) -> Dict[str, Any]:
    """
    Fetch details of an identity from SailPoint IdentityNow.
    If credentials are not configured, returns mock data for demonstration.
    """
    token = await get_sailpoint_token()
    base_url = os.getenv("SAILPOINT_BASE_URL")

    if not token or not base_url:
        # Return mock data if credentials are missing
        return {
            "status": "Mock Data (Credentials missing)",
            "identity": {
                "name": identity_name,
                "email": f"{identity_name.lower().replace(' ', '.')}@example.com",
                "status": "Active",
                "jobTitle": "Security Engineer",
                "department": "IAM Operations",
                "lastLogin": datetime.now().isoformat()
            }
        }

    # Search for the identity
    search_url = f"{base_url}/v3/search"
    query = {
        "indices": ["identities"],
        "query": {
            "query": f"name:\"{identity_name}\" OR email:\"{identity_name}\""
        }
    }

    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(search_url, json=query, headers=headers)
            response.raise_for_status()
            results = response.json()

            if results:
                return {"status": "Success", "identity": results[0]}
            else:
                return {"status": "Error", "message": f"Identity '{identity_name}' not found."}
    except Exception as e:
        return {"status": "Error", "message": str(e)}


@mcp.prompt()
def identity_info_prompt(identity_name: str) -> str:
    """Prompt to look up and summarize identity information"""
    return (
        f"Please use the `get_identity_details` tool to look up information for '{identity_name}'. "
        "Once you have the data, provide a professional summary of the identity, including their "
        "status, job title, and department. Highlight any potential risks if applicable."
    )


def main():
    mcp.run()


if __name__ == "__main__":
    main()
