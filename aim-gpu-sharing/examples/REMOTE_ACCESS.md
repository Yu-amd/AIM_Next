# Remote Access Guide for Web Application

When accessing the node remotely, you have several options to access the web application UI.

## Option 1: SSH Port Forwarding (Recommended)

This is the most secure method and works even if the node's firewall blocks external access.

### Step 1: Start the Web App on Remote Node

On the remote node, start the web app:
```bash
python3 examples/web/web_app.py --endpoint http://localhost:8000/v1 --port 5000 --host 0.0.0.0
```

### Step 2: Create SSH Tunnel from Local Machine

On your **local machine**, create an SSH tunnel:
```bash
ssh -L 5000:localhost:5000 user@remote-node-ip
```

Or if you're already SSH'd into the remote node, open a **new terminal on your local machine** and run:
```bash
ssh -L 5000:localhost:5000 user@remote-node-ip
```

### Step 3: Access Web UI

Open your browser on your **local machine** and go to:
```
http://localhost:5000
```

## Option 2: Direct Access via Node IP

If the node's firewall allows external access to port 5000:

### Step 1: Start Web App

On the remote node:
```bash
python3 examples/web/web_app.py --endpoint http://localhost:8000/v1 --port 5000 --host 0.0.0.0
```

### Step 2: Access via Node IP

On your **local machine**, open browser and go to:
```
http://<remote-node-ip>:5000
```

**Note:** Make sure port 5000 is open in the firewall:
```bash
# On the remote node, if using ufw:
sudo ufw allow 5000/tcp

# Or if using iptables:
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

## Option 3: Use Different Port

If port 5000 is already in use or blocked:

### Step 1: Start Web App on Different Port

```bash
python3 examples/web/web_app.py --endpoint http://localhost:8000/v1 --port 8080 --host 0.0.0.0
```

### Step 2: Use SSH Port Forwarding

```bash
ssh -L 8080:localhost:8080 user@remote-node-ip
```

Then access: `http://localhost:8080`

## Option 4: Background Process with SSH

If you want to keep the web app running after disconnecting:

### Step 1: Start Web App in Background

```bash
nohup python3 examples/web/web_app.py --endpoint http://localhost:8000/v1 --port 5000 --host 0.0.0.0 > web_app.log 2>&1 &
```

### Step 2: Check if Running

```bash
ps aux | grep web_app.py
netstat -tlnp | grep 5000
```

### Step 3: Access via SSH Tunnel

```bash
ssh -L 5000:localhost:5000 user@remote-node-ip
```

## Troubleshooting

### Check if Web App is Running

```bash
# Check process
ps aux | grep web_app.py

# Check port
netstat -tlnp | grep 5000
# or
ss -tlnp | grep 5000
```

### Check if Port is Accessible

```bash
# From local machine, test connection
curl http://remote-node-ip:5000/api/health

# Or use telnet
telnet remote-node-ip 5000
```

### View Web App Logs

```bash
# If running in background
tail -f web_app.log

# If running in foreground, logs appear in terminal
```

### Firewall Configuration

**Ubuntu/Debian (ufw):**
```bash
sudo ufw allow 5000/tcp
sudo ufw status
```

**CentOS/RHEL (firewalld):**
```bash
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload
```

**Generic (iptables):**
```bash
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables-save
```

## Quick Reference

### Most Common Workflow

1. **On remote node:**
   ```bash
   python3 examples/web/web_app.py --endpoint http://localhost:8000/v1 --port 5000 --host 0.0.0.0
   ```

2. **On local machine (new terminal):**
   ```bash
   ssh -L 5000:localhost:5000 user@remote-node-ip
   ```

3. **In browser:**
   ```
   http://localhost:5000
   ```

## Security Note

- SSH port forwarding (Option 1) is the most secure as it doesn't expose the port externally
- If using direct access (Option 2), ensure your firewall is properly configured
- Consider using HTTPS in production environments

