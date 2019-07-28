# rcj-app-server
*Build Status:* [![CircleCI](https://circleci.com/gh/rcjaustralia/rcj-app-server.svg?style=svg)](https://circleci.com/gh/rcjaustralia/rcj-app-server)
A very simple frontend for the other RCJ webapps such as rcj-soccer-platform.

It uses NGINX to terminate SSL and route requests through to the other applications. A Python control wrapper manages the NGINX process and generates SSL certificates using Lets Encrypt (tihs only works if the DNS is managed by [Vultr](https://vultr.com/)). There are many things to do, including automatic NGINX configuration generation, certificate renewal (currently the server must be restarted every 90 days to generate a new cert) and logging of NGINX to STDOUT / STDERR.

(Optional) To build this from source:

```bash

docker build -t proxy .
```

Or just run the pre-compiled version on Docker Hub:

```bash
docker run --restart always -d -e "CERT_EMAIL=your@email.com" -e "DOMAINS_SOCCER=soccer.rcja.org:soccer.rcj.org.au" -e "VULTR_API_KEY=YOUR_VULTR_API_KEY" -e "USE_STAGING=yes" --link rcj_soccer:rcj_soccer -p 80:80 -p 443:443 --name rcj_proxy rcjaustralia/rcj-app-server
```

To run in production, substitute *your@email.com*, *YOUR_VULTR_API_KEY* with an API key from Vultr (used for DNS as the acme challenge for Lets Encrypt) and set *USE_STAGING* to *no*.
