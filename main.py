import os
import subprocess
import logging
import json
import requests
import time
import socket


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(msg)s")

logger = logging.getLogger(__name__)


CERT_PATH = os.environ.get("CERTS_DIR", "/certs")
CERT_EMAIL = os.environ.get("CERT_EMAIL", "certs@rcja.org")
VULTR_API_KEY = os.environ.get("VULTR_API_KEY")
VULTR_BASE_URL = os.environ.get("VULTR_BASE_URL", "https://api.vultr.com/v1/")
USE_STAGING = os.environ.get("USE_STAGING", "no").lower() in ("y", "yes", "1")


def vultr_list_zones():
    global VULTR_API_KEY
    global VULTR_BASE_URL

    logger.info("Listing Vultr zones")

    r = requests.get(VULTR_BASE_URL + "dns/list", headers={
        "API-Key": VULTR_API_KEY
    })
    time.sleep(0.6)  # Vultr limits API requests to 2 per second
    r.raise_for_status()

    domains = [x["domain"] for x in r.json()]
    return domains


def vultr_make_txt_record(zone, name, value):
    global VULTR_API_KEY
    global VULTR_BASE_URL

    logger.info("Making TXT record in {0} for {1} = {2}".format(
        zone, name, value
    ))

    r = requests.post(VULTR_BASE_URL + "dns/create_record", headers={
        "API-Key": VULTR_API_KEY
    }, data={
        "domain": zone,
        "name": name,
        "type": "TXT",
        "data": "\"{0}\"".format(value),
        "ttl": 300
    })
    time.sleep(0.6)
    r.raise_for_status()


def vultr_remove_txt_record(zone, name):
    global VULTR_API_KEY
    global VULTR_BASE_URL

    logger.info("Removing TXT record in {0} of {1}".format(zone, name))

    r = requests.get(VULTR_BASE_URL + "dns/records", headers={
        "API-Key": VULTR_API_KEY
    }, params={
        "domain": zone
    })
    time.sleep(0.6)
    r.raise_for_status()
    records = [x["RECORDID"] for x in r.json()
               if x["type"] == "TXT" and x["name"] == name]

    record = records[0]
    r = requests.post(VULTR_BASE_URL + "dns/delete_record", headers={
        "API-Key": VULTR_API_KEY
    }, data={
        "domain": zone,
        "RECORDID": record
    })
    time.sleep(0.6)
    r.raise_for_status()


def parse_domains(prefix="DOMAINS_"):
    domains = {}

    for name, value in os.environ.items():
        if not name.startswith(prefix):
            continue

        value = value.split(":")
        primary = value[0]
        aliases = []

        if len(value) > 1:
            aliases = value[1].split(",")

        aliases.append(primary)
        aliases = set(map(lambda s: s.strip(), aliases))

        domains[primary] = aliases

    return domains


def generate_certs(domains):
    for domain in domains.keys():
        generate_cert(domain)


def execute_cmd(domain, data):
    if data["cmd"] == "perform_challenge":
        return perform_challenge(domain, data)
    else:
        logger.error("Unknown command: {0} - ".format(data["cmd"], data))
        return None


def perform_challenge(domain, data):
    logger.info("Performing challenge for {0}".format(domain))

    zones = vultr_list_zones()
    zones.sort(key=lambda zone: len(zone), reverse=True)

    zone = None
    for zone_name in zones:
        if domain.endswith(zone_name):
            zone = zone_name
            break

    name = data["txt_domain"].replace("." + zone, "")

    vultr_make_txt_record(zone, name, data["validation"])
    return ("\n".encode("utf-8"), (zone, name))


def generate_cert(domain):
    global CERT_EMAIL
    global USE_STAGING

    logger.info("Creating certificate for {0}".format(domain))
    logger.info("Using email address: {0}".format(CERT_EMAIL))

    cmd = ["certbot", "--staging", "--text", "--agree-tos", "--email",
           CERT_EMAIL, "--expand", "--keep",
           "--configurator", "certbot-external-auth:out",
           "--certbot-external-auth:out-public-ip-logging-ok", "-d",
           domain, "--preferred-challenges", "dns", "run"]

    if not USE_STAGING:
        cmd.remove("--staging")
    else:
        logger.warn("Using staging server")

    exit_code = 1
    dns = None
    with subprocess.Popen(cmd, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE) as process:
        for line in process.stdout:
            data = json.loads(line.strip())
            response = execute_cmd(domain, data)
            if response is not None:
                process.communicate(input=response[0])
                dns = response[1]
                break
        exit_code = process.wait()

    if dns is not None:
        vultr_remove_txt_record(dns[0], dns[1])

    if exit_code == 0:
        logger.info("Successfully made certificate for {0}".format(domain))
        return True
    else:
        logger.error("Error occured during certificate creation")
        return False


def get_rcj_server():
    return socket.gethostbyname("rcj_soccer")


def start_nginx():
    with open("/etc/nginx/nginx.conf", "r") as f:
        contents = f.read().replace("$RCJ_SOCCER$", get_rcj_server())
    with open("/etc/nginx/nginx.conf", "w") as f:
        f.write(contents)

    with open("/etc/nginx/nginx.conf", "r") as f:
        print(f.read())

    subprocess.run(["nginx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == "__main__":
    domains = parse_domains()
    generate_certs(domains)
    start_nginx()
