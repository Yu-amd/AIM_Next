#!/usr/bin/env python3
"""
Web Application for AIM GPU Sharing vLLM Model Endpoint

A modern web interface for interacting with deployed vLLM models.

Usage:
    python3 web_app.py [--endpoint URL] [--port PORT]
"""

from flask import Flask, render_template_string, request, jsonify
import requests
import json
import os
from typing import List, Dict

app = Flask(__name__)

# Configuration
ENDPOINT_URL = os.getenv('VLLM_ENDPOINT', 'http://localhost:8000/v1')
MODEL_NAME = None

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIM GPU Sharing - Model Chat</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 900px;
            height: 80vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f5f5f5;
        }
        
        .message {
            margin-bottom: 20px;
            display: flex;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 18px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .message.assistant .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
        }
        
        .input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .input-form {
            display: flex;
            gap: 10px;
        }
        
        .input-form input {
            flex: 1;
            padding: 12px 18px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .input-form input:focus {
            border-color: #667eea;
        }
        
        .input-form button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .input-form button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .input-form button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 AIM GPU Sharing - Model Chat</h1>
            <p>Powered by vLLM on AMD GPUs</p>
        </div>
        
        <div class="chat-container" id="chatContainer">
            <div class="message assistant">
                <div class="message-content">
                    👋 Hello! I'm your AI assistant running on AMD GPU with GPU sharing. How can I help you today?
                </div>
            </div>
        </div>
        
        <div class="input-container">
            <form class="input-form" id="chatForm">
                <input 
                    type="text" 
                    id="userInput" 
                    placeholder="Type your message here..." 
                    autocomplete="off"
                    required
                />
                <button type="submit" id="sendButton">Send</button>
            </form>
        </div>
    </div>
    
    <script>
        const chatContainer = document.getElementById('chatContainer');
        const chatForm = document.getElementById('chatForm');
        const userInput = document.getElementById('userInput');
        const sendButton = document.getElementById('sendButton');
        
        function addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            
            messageDiv.appendChild(contentDiv);
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            return contentDiv;
        }
        
        async function sendMessage(message) {
            // Add user message
            addMessage('user', message);
            userInput.value = '';
            sendButton.disabled = true;
            sendButton.innerHTML = '<div class="loading"></div>';
            
            // Add loading indicator for assistant
            const loadingDiv = addMessage('assistant', '');
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'loading';
            loadingDiv.appendChild(loadingIndicator);
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Remove loading indicator
                loadingDiv.innerHTML = '';
                
                // Add response
                if (data.error) {
                    loadingDiv.textContent = `Error: ${data.error}`;
                    loadingDiv.style.background = '#fee';
                    loadingDiv.style.color = '#c33';
                } else {
                    loadingDiv.textContent = data.response;
                    loadingDiv.style.background = '';
                    loadingDiv.style.color = '';
                }
            } catch (error) {
                loadingDiv.innerHTML = '';
                loadingDiv.textContent = `Error: ${error.message}`;
                loadingDiv.style.background = '#fee';
                loadingDiv.style.color = '#c33';
            } finally {
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                userInput.focus();
            }
        }
        
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = userInput.value.trim();
            if (message) {
                sendMessage(message);
            }
        });
        
        // Focus input on load
        userInput.focus();
    </script>
</body>
</html>
"""


def get_model_name():
    """Get the first available model name."""
    global MODEL_NAME
    if MODEL_NAME:
        return MODEL_NAME
    
    try:
        response = requests.get(f"{ENDPOINT_URL}/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                MODEL_NAME = data["data"][0]["id"]
                return MODEL_NAME
    except Exception:
        pass
    
    return "default"


@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat API requests."""
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        model_name = get_model_name()
        
        # Prepare request to vLLM endpoint
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": message}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        response = requests.post(
            f"{ENDPOINT_URL}/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return jsonify({'response': content})
        else:
            return jsonify({
                'error': f"API error: {response.status_code} - {response.text}"
            }), 500
            
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"Connection error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models', methods=['GET'])
def models():
    """Get list of available models."""
    try:
        response = requests.get(f"{ENDPOINT_URL}/models", timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to get models'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        response = requests.get(f"{ENDPOINT_URL}/health", timeout=5)
        return jsonify({
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'endpoint': ENDPOINT_URL
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'endpoint': ENDPOINT_URL
        }), 503


def main():
    import argparse
    global ENDPOINT_URL
    
    parser = argparse.ArgumentParser(description='Web app for AIM GPU Sharing vLLM endpoint')
    parser.add_argument('--endpoint', default=ENDPOINT_URL, help='vLLM endpoint URL')
    parser.add_argument('--port', type=int, default=5000, help='Web server port')
    parser.add_argument('--host', default='0.0.0.0', help='Web server host')
    
    args = parser.parse_args()
    
    ENDPOINT_URL = args.endpoint
    
    print("=" * 60)
    print("AIM GPU Sharing - Web Application")
    print("=" * 60)
    print(f"vLLM Endpoint: {ENDPOINT_URL}")
    print(f"Web Server: http://{args.host}:{args.port}")
    print("=" * 60)
    print()
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()

