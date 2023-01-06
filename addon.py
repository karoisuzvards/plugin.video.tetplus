import sys

from resources.lib import utils
from urllib.parse import parse_qsl
from resources.lib.router import router

utils.log('Initialised')

base_url = sys.argv[0]

# when calling from settings menu - addon handle is string
try:
    addon_handle = int(sys.argv[1])
except ValueError:
    addon_handle = sys.argv[1]
    
# when calling from settings menu - url params not passed
try:    
    args = dict(parse_qsl(sys.argv[2][1:]))
except IndexError:
    args = {}

if __name__ == "__main__":
    utils.log("got URL: " + "; ".join(sys.argv))

    router(base_url, addon_handle, args)
