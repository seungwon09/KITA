# KITA Fixed Link Guide

Current friend-test link is temporary:

https://hosting-invalid-journey-offices.trycloudflare.com

That link changes when the quick Cloudflare Tunnel stops. For a stable link, use a Cloudflare named tunnel with your own domain.

## What You Need

1. A Cloudflare account
2. A domain added to Cloudflare
3. Docker Desktop running
4. KITA running on `http://localhost:3000`

Cloudflare's official setup says a published application route maps a public hostname to a local service URL such as `http://localhost:3000`.

## Setup

Run:

```powershell
C:\Users\user\Documents\Codex\kita-deploy\SETUP_KITA_FIXED_TUNNEL.bat
```

When asked for hostname, enter something like:

```txt
kita.your-domain.com
```

The script will:

1. Start KITA with Docker
2. Open Cloudflare login
3. Create a tunnel named `kita-prod`
4. Create DNS for your hostname
5. Save local tunnel config

## Start Later

Run:

```powershell
C:\Users\user\Documents\Codex\kita-deploy\START_KITA_FIXED_TUNNEL.bat
```

Keep that window open while friends use KITA.

## Stop

Run:

```powershell
C:\Users\user\Documents\Codex\kita-deploy\STOP_KITA_PUBLIC_TUNNEL.bat
```

## Important

This is stable only if:

- Your PC is on
- Docker Desktop is on
- The fixed tunnel window is open
- Your internet is connected

For a real always-on launch, move this same Docker project to a VPS or cloud server.
