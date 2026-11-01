# Home lab setup

This is the lab I built to practice security on my own machine, so I never have to scan or attack anything on my home network. I'm documenting it so I can rebuild it quickly and remember why I made each choice.

## What it is

- Host: Ubuntu 24.04, 16 GB RAM, Intel Core i5-1235U (12th gen), KVM/libvirt with virt-manager
- Attacker VM: Kali Linux 2026.3, about 5 GB RAM, 3 vCPUs, about 38 GB disk (qcow2)
- Target: OWASP Juice Shop, running in Docker on the host ([Docker Desktop / native engine])
- Network: a libvirt network called `isolated-lab`

```
Host (Ubuntu) ── Wi-Fi ──► home network / internet
   │
   ├── Docker: Juice Shop, published on 192.168.100.1:3000
   │
   └── virbr1 = isolated-lab (192.168.100.0/24, no route out)
          └── Kali VM (attacker), 192.168.100.x from DHCP
```

The attacker and the target are two separate machines on purpose. That is closer to a real test than running both inside Kali, and Nmap and Wireshark see real network traffic between them.

## The network

`lab-net.xml` defines the isolated network. The important part is that it has no `<forward>` tag, so libvirt creates a private virtual switch with no route to my Wi-Fi, my router or the internet.

- Subnet: 192.168.100.0/24
- Host side of the bridge (virbr1): 192.168.100.1
- DHCP range: 192.168.100.10 to 192.168.100.100

To create it:

```bash
sudo virsh net-define lab-net.xml
sudo virsh net-start isolated-lab
sudo virsh net-autostart isolated-lab
```

The bridge `virbr1` only comes up while a VM using `isolated-lab` is running.

## Kali VM

I installed Kali from the installer ISO. During setup the VM had two network cards: one on `isolated-lab` and a temporary one on libvirt's default NAT network, used only to update and install tools. Once that was done I removed the NAT card, so Kali now only sees the lab network.

I checked the isolation from inside Kali:

```bash
ping -c 2 192.168.100.1   # works
ping -c 2 8.8.8.8         # fails, as it should
```

Installed on top of the base system: nmap, wireshark, curl, git, net-tools.

I did not install Docker in Kali. The target runs on the host, and Kali has no internet to pull images.

After everything was updated and tested I took a snapshot called `clean-base`, so I can go back to a clean state after breaking things.

When I need internet in Kali again, I shut it down, add a NAT card, do the update or install, remove the card, and take a new snapshot.

## Juice Shop (target on the host)

I run it in Docker on the host and publish it on the lab bridge address only. That way Kali can reach it, but my Wi-Fi network can't:

```bash
docker run -d --name juice-shop -p 192.168.100.1:3000:3000 bkimminich/juice-shop
```

For browser-only challenges I can also use it from the host at `http://192.168.100.1:3000`.

### Firewall rule

At first Firefox in Kali showed nothing. The cause was Ubuntu's firewall (ufw), which dropped incoming traffic from the lab bridge. This rule fixed it:

```bash
sudo ufw allow in on virbr1 to any port 3000 proto tcp
```

It allows port 3000 only on `virbr1`, not on the Wi-Fi interface. Useful commands:

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ufw delete N
```

### How I check connectivity

From Kali:

```bash
ping -c 2 192.168.100.1
nc -vz -w3 192.168.100.1 3000
curl -I --max-time 5 http://192.168.100.1:3000
```

On the host:

```bash
ss -tlnp | grep 3000
sudo tcpdump -i virbr1 -n port 3000
```

A timeout means packets are being dropped (usually a firewall). "Connection refused" means the packet arrived but nothing is listening.

## Problems I ran into

- **ISO used as a disk:** the Kali file I downloaded was the installer ISO, but I had renamed it `.qcow2` and attached it as a disk. The installer then showed a 4.8 GB disk, which was the clue. I renamed it back to `.iso`, created a real qcow2 disk and installed again.
- **Low disk space on the host:** I had about 14 GB free, mostly because of Docker Desktop's VM file. I backed up my volumes, purged Docker Desktop's data and got the space back.
- **Broken first upgrade:** `apt full-upgrade` in Kali failed with a libc6 version mismatch. I fixed it with `dpkg --configure -a` and `apt --fix-broken install`, then upgraded again.
- **Docker pull failed in Kali:** Kali has no internet by design, so it couldn't download the image. I moved the target to the host instead.
- **Kali couldn't reach Juice Shop:** fixed with the ufw rule above.

## What's next

- Nmap and Wireshark practice against Juice Shop, with write-ups
- Juice Shop challenges
- Home SOC with Wazuh and Suricata
- Security audit of my own app, SmartPoint
