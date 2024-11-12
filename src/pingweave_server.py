import os
import sys
import subprocess
import configparser  # default library
import asyncio  # default library

try:
    import yaml
except ImportError:
    print("PyYAML library not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml

from logger import initialize_pinglist_logger

# parameter
COLLECT_PERIOD_SECONDS = 10
LOAD_PINGLIST_SECONDS = 5

# absolute paths of this script and pinglist.yaml
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PINGLIST_PATH = os.path.join(SCRIPT_DIR, "../config/pinglist.yaml")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "../config/pingweave.ini")
UPLOAD_PATH = os.path.join(SCRIPT_DIR, "../upload")
DOWNLOAD_PATH = os.path.join(SCRIPT_DIR, "../download")

# Variables to save pinglist
pinglist_in_memory = {}
address_store = {}  # ip -> (gid, lid, qpn)
pinglist_lock = asyncio.Lock()
address_store_lock = asyncio.Lock()

# ConfigParser object
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

control_host = config["controller"]["host"]
control_port = config["controller"]["port"]
logger = initialize_pinglist_logger(control_host, "server")


def check_ip_active(target_ip):
    try:
        # Linux/Unix - based 'ip addr' command
        result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(
                f"Error running 'ip addr' command. Return code: {result.returncode}"
            )
            logger.error(f"Standard error output: {result.stderr.strip()}")
            return False

        # Check ip address from output
        if target_ip in result.stdout:
            return True
        else:
            logger.error(f"No active interface found with IP address {target_ip}.")
            return False

    except Exception as e:
        logger.error(f"An unexpected error occurred while checking IP: {e}")
        return False


async def load_pinglist():
    global pinglist_in_memory

    try:
        # use a lock to hold client request during file loading
        async with pinglist_lock:
            if os.path.isfile(PINGLIST_PATH):
                with open(PINGLIST_PATH, "r") as file:
                    # YAML -> dictionary (parsing)
                    pinglist_in_memory = yaml.safe_load(file)
                    logger.info("Pinglist is loaded successfully.")
            else:
                logger.error(f"Pinglist file not found at {PINGLIST_PATH}")
    except Exception as e:
        logger.error(f"Error loading pinglist: {e}")


async def load_pinglist_periodically():
    while True:
        await load_pinglist()
        await asyncio.sleep(LOAD_PINGLIST_SECONDS)


async def handle_client(reader, writer):
    try:
        client_address = writer.get_extra_info("peername")
        if client_address:
            client_ip, client_port = client_address

        request = await reader.read(512)

        if request.startswith(b"GET /pinglist"):
            async with pinglist_lock:  # pinglist_in_memory에 대한 잠금
                response = str(pinglist_in_memory).encode()
                writer.write(response)
                await writer.drain()
                logger.info(
                    f"(SEND) pinglist data to client: {client_ip}:{client_port}"
                )

        elif request.startswith(b"GET /address_store"):
            async with address_store_lock:  # address_store에 대한 별도 잠금
                response = str(address_store).encode()
                writer.write(response)
                await writer.drain()
                logger.info(
                    f"(SEND) address_store to client: {client_ip}:{client_port}"
                )

        elif request.startswith(b"POST /address"):
            content = request.decode().splitlines()[1:]  # 첫 줄 무시
            if len(content) == 5:  # IP, GID, LID, QPN, datetime
                ip_address, gid, lid, qpn, dtime = content

                async with address_store_lock:  # address_store 업데이트에 대한 잠금
                    address_store[ip_address] = [gid, lid, int(qpn)]
                    logger.info(
                        f"(RECV) POST from {client_ip}:{client_port} and updated the store."
                    )

                    if len(address_store) > 10000:
                        logger.error(
                            f"Too many registered ip->(gid,lid) entries: {len(address_store)}"
                        )
                        logger.critical(
                            "Clean up the address_store. Check your config."
                        )
                        address_store.clear()

            else:
                logger.warning(
                    f"(RECV) POST format is incorrect from {client_ip}:{client_port}"
                )

        writer.close()
        await writer.wait_closed()
    except Exception as e:
        logger.error(f"Error handling client data from {client_ip}:{client_port}: {e}")


async def main():
    if not check_ip_active(control_host):
        logger.error(f"No active interface with the target IP {control_host}.")
        exit(1)

    asyncio.create_task(load_pinglist_periodically())

    server = await asyncio.start_server(handle_client, control_host, control_port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
