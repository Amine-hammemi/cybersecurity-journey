iolated-lab: a private virtual network for the cybersecurity home lab.
There is **NO < forword >** element, so libvirt does not NAT or route this network to the host's LAN or the internet. 
VMs attached to it can only talk to each other and to the host bridge ( 192.168.100.1 ).

# Home Lab
An isolated virtual lab for practicing offensive and defensive security safely.
Everything runs on one linux laptop. Vulnerable targets and attack tools are kept on a network with no route to my home LAN or the internet.

## Architecture
```
Host (linux , KVM/Libvirt )
 |---- WI-FI ------> home network / internet (not reachable from the lab )
 |---- Docker --- OWASP Juice Shop ( 127.0.0.1:3000, host only)
 |---- virbr1 "isolated-lab" 192.168.100.0/24 (gateway 192.168.100.1)
          |---- Kali linux Vm (attacker)
```

## Components 
| Component | purpose |
| --- | --- |
| KVM + QEMU + libvirt + virt-manager | Native linux virtualization , with networks defined as code |
| `isolated-lab` network | Private switch with no forwording, so attacks cannot leak out |
| Kali Linux VM | Attack and analysis workstation (Nmap, Wireshark..)|
| Docker + OWASP Juice Shop | Intentianally vulnerable web app for legal practice |
| qcow2 snapshots | Restore a clean state after risky experiments |

### The network definition

[`lab-net.xml`](lab-net.xml) defines the `isolated-lab` network :

- **Subnet:** `192.168.100.0/24`