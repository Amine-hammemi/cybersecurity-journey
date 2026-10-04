import asyncio
import sys
import time

async def grab_banner(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int) -> str:
    """Extracts clean, readable banners from common services."""
    try:
        data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
    except asyncio.TimeoutError:
        data = b""

    if not data:
        try:
            if port in (80, 631, 8000, 8080):
                writer.write(b"HEAD / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            elif port == 3306:
                writer.write(b"\x00\x00\x00\x00") 
            elif port == 5432:
                # Direct unencrypted PostgreSQL Startup Packet containing an invalid user
                # This safely forces Postgres to throw a verbose error containing its environment details
                writer.write(b"\x00\x00\x00\x28\x00\x03\x00\x00user\x00postgres_probe\x00\x00")
            else:
                writer.write(b"\r\n")
                
            await writer.drain()
            data = await asyncio.wait_for(reader.read(1024), timeout=1.2)
        except Exception:
            data = b""

    if data:
        # Regex parsing for MySQL binary noise
        if port == 3306:
            import re
            decoded = data.decode(errors="ignore")
            versions = re.findall(r'[0-9]+\.[0-9]+\.[0-9]+[-\w\.]+', decoded)
            if versions:
                return f"MySQL {versions[0]}"

        # Standard sanitization for text outputs
        clean_text = "".join(chr(b) if 32 <= b < 127 else " " for b in data)
        clean_text = " ".join(clean_text.split()).strip()
        return clean_text[:75]
    
    return "(no banner)"




async def check_port(target_ip: str, port: int, semaphore: asyncio.Semaphore, timeout: float = 1.0) -> tuple[int, str, str]:
    async with semaphore:
        try:
            # Single connection attempt
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(target_ip, port), timeout=timeout
            )
            
            # Pass the open connection to grab the banner
            banner = await grab_banner(reader, writer, port)
            
            # Clean up the connection safely
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
                
            return (port, "open", banner)
            
        except asyncio.TimeoutError:
            return (port, "filtered", "")
        except (ConnectionRefusedError, OSError):
            return (port, "closed", "")



async def scan_range(target_ip: str, start_port: int, end_port: int, timeout: float = 1.0, max_concurrent: int = 500):
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [
        check_port(target_ip, port, semaphore, timeout)
        for port in range(start_port, end_port + 1)
    ]
    results = await asyncio.gather(*tasks)
    return results


async def main():
    target = sys.argv[1]
    start_port = int(sys.argv[2])
    end_port = int(sys.argv[3])

    start_time = time.time()
    results = await scan_range(target, start_port, end_port)
    elapsed = time.time() - start_time

    for port, state, banner in sorted(results):
        if state == "open":
            print(f"{target}:{port} -> {state}  [{banner}]")

    open_count = sum(1 for _, state, _ in results if state == "open")
    print(f"\nScanned {end_port - start_port + 1} ports in {elapsed:.2f}s — {open_count} open")

if __name__ == "__main__":
    asyncio.run(main())