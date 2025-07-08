import aiohttp
import os
import importlib.metadata
import importlib.util
import sys

# Load original installed package modules under the canonical names
_dist = importlib.metadata.distribution('outline_api')
_pkg_path = _dist.locate_file('outline_api')

# Load dependency modules first so that outline_api.py can import them
for name in ['errors.py', 'prometheus.py', 'outline_api.py']:
    spec = importlib.util.spec_from_file_location(f'outline_api.{name[:-3]}', _pkg_path / name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f'outline_api.{name[:-3]}'] = mod
    spec.loader.exec_module(mod)

# Load the original __init__ under a temporary name to access its attributes
spec_init = importlib.util.spec_from_file_location(
    'outline_api._orig_init', _pkg_path / '__init__.py', submodule_search_locations=[str(_pkg_path)]
)
_orig = importlib.util.module_from_spec(spec_init)
sys.modules['outline_api._orig_init'] = _orig
spec_init.loader.exec_module(_orig)

__all__ = list(getattr(_orig, '__all__', [])) + ['create_named_key']
for name in getattr(_orig, '__all__', []):
    globals()[name] = getattr(_orig, name)

OUTLINE_API_URL = os.getenv('OUTLINE_API_URL', '')
OUTLINE_API_TOKEN = os.getenv('OUTLINE_API_TOKEN', '')

_headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {OUTLINE_API_TOKEN}',
}

async def create_named_key(vpn_name: str) -> dict:
    """Create a key and set its name using Outline API."""
    if not OUTLINE_API_URL:
        raise RuntimeError('OUTLINE_API_URL not configured')
    async with aiohttp.ClientSession(headers=_headers) as session:
        async with session.post(f"{OUTLINE_API_URL}/access-keys") as response:
            data = await response.json()
            key_id = data['id']
        payload = {'name': vpn_name}
        async with session.patch(f"{OUTLINE_API_URL}/access-keys/{key_id}", json=payload) as r:
            await r.text()
        return {'id': key_id, 'name': vpn_name}
