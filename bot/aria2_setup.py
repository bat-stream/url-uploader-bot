import subprocess
import time
import aria2p

# Start aria2c RPC process
aria2_process = subprocess.Popen([
    "aria2c",
    "--enable-rpc",
    "--rpc-listen-all=false",
    "--rpc-allow-origin-all",
    "--rpc-listen-port=6807",
    "--dir=downloads",
    "--max-concurrent-downloads=5",
    "--continue=true",
    "--split=5",
    "--max-connection-per-server=5",
    "--min-split-size=1M"
])
time.sleep(2)

# Connect aria2 API client
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6807))
