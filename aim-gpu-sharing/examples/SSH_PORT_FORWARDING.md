# SSH Port Forwarding Guide for Web App

## Scenario: Web App on Remote Node, Access from Local Machine

### Architecture
```
Local Machine                    Remote Node
    |                                |
    |  SSH Tunnel                   |
    |  (ports 5000, 8001)           |
    |                                |
    └───────────────────────────────┘
                                    |
                            ┌───────┴────────┐
                            |                |
                    Web App (port 5000)   vLLM (port 8001)
                    (Flask)              (K8s port-forward)
```

## Step-by-Step Instructions

### Step 1: On Remote Node - Start vLLM Port Forward

Open a terminal on the remote node and run:

```bash
kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8001:8000
```

**Keep this terminal open!** The port-forward needs to stay active.

### Step 2: On Remote Node - Start Web App

Open **another terminal** on the remote node and run:

```bash
cd /root/AIM_Next/aim-gpu-sharing
python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0
```

**Keep this terminal open too!** The web app needs to keep running.

### Step 3: On Your Local Machine - Create SSH Tunnel

Open a terminal on **your local machine** and run:

```bash
ssh -L 5000:localhost:5000 -L 8001:localhost:8001 user@remote-node-ip
```

Replace:
- `user` with your SSH username
- `remote-node-ip` with the IP address of the remote node (e.g., `134.199.200.240`)

**Example:**
```bash
ssh -L 5000:localhost:5000 -L 8001:localhost:8001 root@134.199.200.240
```

This command:
- Forwards local port 5000 → remote port 5000 (web app)
- Forwards local port 8001 → remote port 8001 (vLLM API)
- Keeps the SSH connection open

**Keep this SSH session open!** The port forwarding only works while SSH is connected.

### Step 4: On Local Machine - Access Web App

Open your browser on your **local machine** and go to:

```
http://localhost:5000
```

The web app should load and be able to communicate with the vLLM API through the SSH tunnel.

## Alternative: Single Port Forward (Simpler)

If you only want to access the web app (and the web app handles the vLLM connection internally):

### On Remote Node:
```bash
# Terminal 1: vLLM port-forward
kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8001:8000

# Terminal 2: Web app
python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0
```

### On Local Machine:
```bash
# Only forward web app port (web app connects to vLLM on remote side)
ssh -L 5000:localhost:5000 user@remote-node-ip
```

Then open: `http://localhost:5000`

## Troubleshooting

### Port Already in Use

If you get "address already in use" errors:

```bash
# Check what's using the port
lsof -i :5000
# or
netstat -tlnp | grep 5000

# Use different ports
ssh -L 5001:localhost:5000 user@remote-node-ip
# Then access: http://localhost:5001
```

### Connection Refused

- Make sure the web app is running on the remote node
- Make sure it's bound to `0.0.0.0` (not just `127.0.0.1`)
- Check firewall rules on remote node

### Web App Can't Connect to vLLM

- Make sure the kubectl port-forward is still running
- Check that it's forwarding to port 8001 on remote node
- Verify web app endpoint is `http://localhost:8001/v1`

### SSH Connection Drops

- Use `-N` flag to prevent SSH from executing commands:
  ```bash
  ssh -N -L 5000:localhost:5000 -L 8001:localhost:8001 user@remote-node-ip
  ```
- Or use `autossh` for automatic reconnection:
  ```bash
  autossh -M 20000 -L 5000:localhost:5000 -L 8001:localhost:8001 user@remote-node-ip
  ```

## Quick Reference

**Remote Node (2 terminals needed):**
```bash
# Terminal 1
kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8001:8000

# Terminal 2
python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0
```

**Local Machine:**
```bash
ssh -L 5000:localhost:5000 -L 8001:localhost:8001 user@remote-node-ip
```

**Browser:**
```
http://localhost:5000
```

## Background Mode (Optional)

To run in background on remote node:

```bash
# vLLM port-forward in background
nohup kubectl port-forward -n aim-gpu-sharing svc/vllm-model-service 8001:8000 > /tmp/vllm-pf.log 2>&1 &

# Web app in background
nohup python3 examples/web/web_app.py --endpoint http://localhost:8001/v1 --port 5000 --host 0.0.0.0 > /tmp/web-app.log 2>&1 &
```

Check logs:
```bash
tail -f /tmp/vllm-pf.log
tail -f /tmp/web-app.log
```

