# Learning Notes — Simple Port Scanner

Status: In progress — Python version built (sequential + async), banner grabbing next

I'm building this project to understand how port scanning actually works
under the hood, before touching the C++/Boost.Asio version described in
the original repo. These notes are my own record of what I learned, what
broke, and why — written as I went, not cleaned up after the fact.

1. [Objective](#1-objective)
2. [Prerequisites & why each matters](#2-prerequisites--why-each-matters)
3. [Core concepts & definitions](#3-core-concepts--definitions)
4. [Keyword glossary](#4-keyword-glossary)
5. [Real-world application](#5-real-world-application)
6. [Tool ecosystem](#6-tool-ecosystem)
7. [Open questions](#7-open-questions)
8. [Build log](#8-build-log)
9. [Limitations](#9-limitations)
10. [Test environment commands](#10-test-environment-commands)

## 1. Objective

**Technical objective:** build a program that, given a target IP and port
range, determines for each port whether it is open, closed, or filtered,
using the TCP three-way handshake as the detection mechanism, and
retrieves service banners from open ports.

**Learning objective:** I want to actually understand TCP connection
mechanics at the socket level and how async/concurrent programming works,
instead of treating tools like Nmap as black boxes.

## 2. Prerequisites & why each matters

| Prerequisite | Why it matters for this project |
|---|---|
| IP addresses, ports | These are literally the two inputs my scanner takes |
| TCP vs UDP | Determines which protocol mechanics I'm exploiting to detect state |
| TCP handshake | This is the actual detection mechanism the whole tool is built on |
| Sockets | The programming interface I use to send/receive the handshake |
| Classes (C++) | Will organize scan target, port list, and results into one structure |
| Lambdas | Will define what happens when each async connection attempt finishes |
| CMake | Will compile the C++ version across environments |
| Boost.Asio | Will provide the async networking engine (event loop, async connect) |
| Command line | How I run and pass arguments to the finished tool |

## 3. Core concepts & definitions

**Port states and what produces them:**
- **Open** — target replies SYN-ACK → a service is actively listening on that port
- **Closed** — target replies RST → the host is reachable, nothing is listening there
- **Filtered** — no reply at all within my timeout window → a firewall/packet filter is silently dropping my probe

**Concurrency:** running many port-check operations during overlapping
time windows instead of strictly one after another. Achieved via an event
loop that manages many pending operations and reacts as each one
completes, rather than blocking on one at a time.

**Event loop:** a continuously running process that tracks pending async
operations and invokes the right callback when each one resolves
(success, failure, or timeout).

<a id="grabbing">**Banner grabbing:**</a> after confirming a port is open,
opening a connection and reading the first data the service sends
unprompted — many services (SSH, FTP, SMTP) announce their name and
version immediately upon connection.

## 4. Keyword glossary

**Networking terms:**
- **Port** — a numbered endpoint (0–65535) on a host that identifies a specific service or process
- **TCP (Transmission Control Protocol)** — a connection-oriented protocol requiring a handshake before data transfer, with built-in reliability and ordering
- **UDP (User Datagram Protocol)** — a connectionless protocol with no handshake, no delivery guarantee
- **Three-way handshake** — SYN → SYN-ACK → ACK, the sequence that establishes a TCP connection
- **SYN** — a TCP flag signaling "I want to start a connection"
- **SYN-ACK** — a TCP flag combination signaling "I accept your connection request"
- **RST** — a TCP flag signaling "no connection exists / connection refused"
- **Socket** — an OS-level abstraction representing one endpoint of a network connection, identified by IP + port
- **Firewall / packet filter** — software or hardware that selectively allows or silently drops network traffic based on rules
- **CIDR notation** — a way to represent an IP address range (e.g. `192.168.1.0/24`)
- **Timeout** — the maximum time my scanner waits for a response before concluding no response is coming

**Programming terms:**
- **Class** — a structure bundling related data and functions together
- **Object** — a specific instance created from a class
- **Smart pointer (`shared_ptr`)** — a pointer that automatically manages the lifetime/memory of the object it points to
- **Lambda function** — an unnamed, inline function, often used as a callback
- **Callback** — a function passed to be executed later, when some event occurs
- **Asynchronous I/O** — I/O operations that don't block program execution while waiting for completion
- **Concurrency** — multiple operations in progress during overlapping time periods
- **Namespace** — a named scope that groups related code and avoids naming collisions (e.g. `boost::asio`)
- **Header file** — a C++ file (`.hpp`) containing declarations, included by source files that need them
- **Structured bindings** — C++20 syntax to unpack multiple values from a single object into named variables
- **Semaphore** — a concurrency primitive that limits how many operations can run simultaneously, forcing extras to wait for a free slot

**Security/pentesting terms:**
- **Reconnaissance (recon)** — the information-gathering phase of a security assessment, before any exploitation
- **Attack surface** — the total set of points (open ports, services, endpoints) an attacker could potentially target
- **Service fingerprinting** — identifying the exact software and version running behind an open port
- **SYN scan (stealth scan)** — sends SYN, receives SYN-ACK, but never completes the handshake with a final ACK; historically used to be less likely to get logged
- **Connect scan** — completes the full three-way handshake; this is what my project implements — simpler to code, doesn't need raw sockets/root privileges
- **Rate limiting / scan timing** — deliberately slowing a scan to avoid triggering intrusion detection thresholds
- <a id="IDS">**IDS/IPS (Intrusion Detection/Prevention System)</a>** — systems that monitor for and flag/block suspicious traffic patterns, including scan-like behavior

## 5. Real-world application

- **Where it fits in methodology:** port scanning is the first concrete technical step of the reconnaissance/enumeration phase in every standard pentest methodology (PTES, OSSTMM, NIST SP 800-115). Nothing else happens until you know what's exposed.
- **Scope validation:** in an authorized engagement, the client defines a scope (specific IP ranges, specific rules of engagement). My scan results would get checked against that scope — anything unexpected open is itself often a finding worth reporting.
- **Feeding the next phase:** every open port + banner becomes input for the next step — cross-referencing the identified service/version against CVE databases to find known vulnerabilities, which then determines what happens next (if anything, and if authorized).
- **Evasion considerations:** real pentest scans are often deliberately throttled or timed to avoid triggering the client's [IDS/IPS](#IDS), since part of many engagements is testing whether the blue team even detects the recon phase.
- **Legal/ethical boundary:** scanning any host without explicit written authorization is illegal in most jurisdictions (unauthorized access laws). Every real engagement starts with a signed scope/rules-of-engagement document before a single port gets scanned.
- **CTF/bug bounty relevance:** the same process — scan, identify service, look up known issues — is what happens in every CTF box and bug bounty recon phase, usually via Nmap or Masscan rather than a custom tool.

## 6. Tool ecosystem

| Tool | Relation to my project |
|---|---|
| Nmap | The industry-standard version of exactly what I'm building — worth benchmarking my scanner against it |
| Masscan | Same underlying concept, built for scanning huge address ranges at much greater scale |
| Netcat (`nc`) | Manual, single-connection version of [banner grabbing](#grabbing) — good for verifying my scanner's results by hand |
| Wireshark / tcpdump | Lets me visually confirm the SYN/SYN-ACK/RST packets my scanner is actually sending and receiving |
| Shodan | A passive alternative — a search engine of pre-scanned internet-facing devices, useful context for why active scanning matters |
| NVD/CVE databases | Where banner-grabbed version info gets looked up next, once I have a service name and version |

## 7. Open questions

- What privilege level does a full connect scan need vs. a raw SYN scan, and why?
- What does `connect_ex()` (Python) or `async_connect()` (C++) actually return in each of the three states?
- Why might a scan report a port "filtered" when it's actually open, and vice versa?

## 8. Build log

### Entry 1 — Synchronous single-port checker (Python)
**Date:** 20-09-2026

**What I built:** a function that checks one port and returns whether it's
open, closed, or filtered, using `socket.connect_ex()`.

**What I tested:**
- [x] Open port (via `python http.server`) → confirmed "open"
- [x] Closed port (unused port) → confirmed "closed"
- [x] Filtered port (via `ufw deny`) → confirmed "filtered", after debugging below

**What confused me:**
Open and closed states worked immediately. Filtered did not. I ran:
```bash
sudo ufw deny 9998
python3 single_port_check.py 127.0.0.1 9998
```
Despite the firewall rule being active, my script kept reporting the port
as *closed*. Even stranger: when I started a real service on that port
(`python3 -m http.server 9998`), it showed as *open*, completely bypassing
the firewall rule. It felt like `ufw` was ignoring my traffic entirely.

**Root cause:**

1. **Loopback bypass.** High-level firewalls like `ufw` are built to
   block threats from the outside world. When I test against `127.0.0.1`,
   the traffic never actually leaves my machine — it stays on the
   internal loopback interface (`lo`). By default, `ufw` doesn't touch
   loopback traffic, specifically so it doesn't break local apps. Since
   my traffic went straight through and nothing was listening on 9998,
   the kernel immediately sent back RST (`ECONNREFUSED`), which is why my
   script reported "closed" instead of "filtered."

2. **Rule order.** Firewalls evaluate rules top to bottom. Linux systems
   typically have a default rule at the very top allowing all loopback
   traffic. My `ufw deny` rule got appended to the *bottom* of the list —
   so the "allow loopback" rule matched first and let my traffic through
   before my deny rule ever got a chance to apply.

**How I fixed it:**
I needed to silently drop loopback traffic on that exact port, and force
the rule to the very top of the chain so nothing above it could match
first. I bypassed `ufw` and used `iptables` directly:
```bash
sudo iptables -I INPUT 1 -i lo -p tcp --dport 9998 -j DROP
```
Breaking the command down:
- `sudo` — need admin privileges to touch firewall routing
- `iptables` — the low-level utility that manages IPv4 packet filtering rules on Linux
- `-I INPUT 1` — insert this as rule #1 at the very top of the INPUT chain, so it's evaluated before the default "allow loopback" rule
- `-i lo` — only apply to the loopback interface, i.e. local `127.0.0.1` traffic
- `-p tcp` — only target TCP packets, matching what my script uses
- `--dport 9998` — only target this specific destination port
- `-j DROP` — silently discard the packet instead of rejecting it. This is the key difference from a normal deny: DROP gives no response at all, which is exactly what makes my socket time out — and a timeout is how my scanner detects "filtered"

As soon as I applied this, my script paused for the full timeout and then
correctly printed "filtered."

**Cleanup note:** running the same command with `-D` instead of `-I 1`
removes the rule afterward.

**What I learned:**
- Firewall rules are evaluated in order — a generic "allow" rule sitting above your specific "deny" rule makes the deny rule useless.
- Localhost behaves differently from a real external IP because of how the OS routes loopback traffic internally.
- "Filtered" isn't a status code the OS hands you — it's the *absence* of any response, which is why it can only be detected via a timeout, not an error.

---

### Entry 2 — Sequential range scanner
**Date:** 20-09-2026

**What I built:** extended `check_port()` into `scan_range()`, looping
over a port range sequentially, with timing added.

**What I measured:**
| Range | Time | Result |
|---|---|---|
| 1–100 | 0.00s | 1 open |
| 1–1000 | 0.01s | 2 open |
| 1–9998 | 1.11s | 4 open, 1 filtered |

*(Note on the 1 filtered result: at this point I still had the iptables
DROP rule on port 9998 active from Entry 1's testing — I hadn't cleaned
it up yet. So this wasn't a stray bug, just leftover state from my
previous test. Worth remembering: always verify your test environment is
clean before trusting a new measurement.)*

**What this proves:** closed and open ports resolve almost instantly
(RST or SYN-ACK comes back fast), so scanning thousands of them
sequentially is cheap — the 9998-port scan only cost 1.11s because just
one port was actually filtered.

The real cost of sequential scanning shows up specifically with filtered
ports, where each one blocks for the full timeout before the loop can
move to the next port. With N filtered ports and a 1s timeout, sequential
scanning costs at least N seconds from filtered ports alone, paid one at
a time.

**The solution:** asyncio lets all pending connection attempts wait out
their timeouts concurrently instead of one after another — so N filtered
ports cost roughly the time of *one* timeout total, not N timeouts,
because the waiting happens in parallel instead of blocking the next
check from starting.

---

### Entry 3 — Concurrent scanner with asyncio
**Date:** 21-09-2026

**What I built:** rewrote `check_port()` and `scan_range()` using
`asyncio.open_connection()` + `asyncio.wait_for()` for timeout handling,
and `asyncio.gather()` to run all port checks concurrently.

**Measured comparison (filtered-port test, 3 denied ports):**
| Filtered ports | Sequential | Async |
|---|---|---|
| 3 | 3.32s | 2.20s |
| 6 | 6.5s | 2.60s |

The gap widens as the number of filtered ports grows — exactly what I'd
expect, since sequential cost scales linearly with N filtered ports while
async cost stays close to a single timeout regardless of N (up to the
concurrency limit).

**How `gather()` changes when each timeout gets "paid":**

In the sequential for-loop, timeouts are paid one at a time, in series.
If port 9990 is filtered, the loop calls `check_port(9990)`, which blocks
for the full 1s timeout — only *after* that returns does the loop move on
to `check_port(9991)`. If 9991 is also filtered, that's another full
second paid *after* the first one finished. Total cost for N filtered
ports = N × timeout, because each wait fully completes before the next
one starts.

With `gather()`, all coroutines get scheduled onto the event loop before
any of them are awaited to completion. So `check_port(9990)` and
`check_port(9991)` both start their 1s timeout clocks at roughly the same
moment, and both clocks run down concurrently. Whichever times out first
returns first, but the other's timeout was already running in parallel —
not waiting for the first to finish. Total cost for N filtered ports ≈ 1
timeout, because the waiting overlaps instead of stacking.

In short: sequential pays timeouts by adding them up; `gather()` pays
timeouts by letting them run at the same time, so I only pay for the
slowest one, not the sum of all of them.

**How this maps to Boost.Asio for the C++ version later:**

`asyncio.gather()` is the equivalent of Boost.Asio's `io_context.run()`.

In the Python version, I create all the coroutine objects first (one per
port), then `gather()` hands them all to the event loop and runs them
concurrently until every one finishes.

In the C++ version, the pattern will be: call `async_connect()` for every
port first (each with its own lambda callback), which queues all those
operations on the `io_context` without blocking. Then I call
`io_context.run()` once — that's the actual event loop, processing all
queued operations and invoking each lambda as its connection resolves,
concurrently rather than one at a time.

So the pairing is:
- `asyncio.open_connection()` + `wait_for()` ↔ `async_connect()` + a deadline timer for the timeout
- the coroutine (`async def` function) ↔ the lambda callback
- `asyncio.gather(*tasks)` ↔ `io_context.run()`

Same underlying idea both times: queue all the work first, then let one
event loop process everything concurrently instead of blocking on each
operation before starting the next.

---

### Entry 3b — Bug: unbounded concurrency broke the scan
**Date:** 21-09-2026

Before I got the numbers above, my first asyncio version had no limit on
how many ports it checked at once — I fired off all 9998 connection
attempts simultaneously with no cap. Running it against `127.0.0.1 1
9998` gave me this: **Scanned 9998 ports in 1.85s — 0 open**

Zero open ports, even though I knew there were 4 (confirmed by the
sequential version moments earlier). It was also *slower* than sequential
(1.85s vs 0.61s), which made no sense if async was supposed to help.

**Debugging it:**
I checked my file descriptor limit first, suspecting I'd hit the classic
"too many open files" problem:
```bash
ulimit -n
# 1048576
```
That ruled out the usual explanation — the limit was way higher than
9998. What was actually happening: firing off ~10,000 simultaneous
connection attempts at once, all targeting `127.0.0.1`, created a burst
large enough to overwhelm the local TCP stack's connection handling
momentarily. Some of those connection attempts failed with `OSError`,
which my exception handling was — reasonably, given what it was written
for — classifying as "filtered." So genuinely open ports were getting
swallowed into false "filtered" results because of resource contention,
not because of anything happening on the wire.

**The fix — bounding concurrency with a semaphore:**
```python
semaphore = asyncio.Semaphore(500)

async def check_port(target_ip, port, semaphore, timeout=1.0):
    async with semaphore:
        # connection logic here
        ...
```
`asyncio.Semaphore(500)` caps how many `check_port()` calls can be
actively running at once. Port number 501 in the queue simply waits until
one of the first 500 finishes and releases its slot. I still get large
concurrency — hundreds at a time — without overwhelming the system the
way firing off all 9998 at once did.

After adding it, re-running the same scan correctly found all 4 open
ports again.

**What I learned:** "concurrent" doesn't mean "unlimited." Real scanners
like Nmap rate-limit themselves deliberately — partly for stealth/IDS
evasion, but also because unbounded concurrency breaks against real
system limits regardless of network conditions. This was a good reminder
that async isn't a free performance upgrade you bolt on without thinking
— it has its own failure modes that sequential code simply doesn't have.

**Also worth noting — a case where async lost fairly:**
Interestingly, on a scan with *no* filtered ports (plain 1–9998, all
open/closed), my semaphore-limited async version (1.65s) was still slower
than sequential (0.61s). This isn't a bug — it's the expected outcome.
Async's advantage comes specifically from overlapping *wait time* across
operations. When nothing is actually waiting (fast RST/SYN-ACK only),
there's no wait time to overlap — async just adds coroutine scheduling
and semaphore overhead with no benefit to offset it. A tight synchronous
loop has almost none of that overhead. Async only wins when there's real
blocking time to parallelize, which is exactly the filtered-port
scenario above.

## 9. Limitations (current state)

- No banner grabbing yet — next step
- No CLI argument parsing / flags (`--timeout`, `--concurrency`) — currently hardcoded
- IPv4 only, no IPv6 support
- No CIDR range support, single target only
- Scan is loud/detectable — no timing randomization or rate-limiting for IDS evasion (intentional for now, this is a learning project, not built for real engagements)

## 10. Test environment commands

```bash
python3 -m http.server 8000          # known open port for testing

# creating filtered ports (see Entry 1 for why both commands are needed)
sudo ufw deny 9998
sudo iptables -I INPUT 1 -i lo -p tcp --dport 9998 -j DROP
# repeated the same for 9997, 9996, 9995, 9994, 9993, 9992

sudo ufw enable
sudo ufw status                      # verify rules are active

# cleanup after testing
sudo ufw delete deny 9998
sudo iptables -D INPUT -i lo -p tcp --dport 9998 -j DROP
```