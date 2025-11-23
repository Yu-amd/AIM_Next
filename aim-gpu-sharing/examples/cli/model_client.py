#!/usr/bin/env python3
"""
CLI Client for AIM GPU Sharing vLLM Model Endpoint

This demonstrates how to interact with a deployed vLLM model endpoint
using the OpenAI-compatible API.

Usage:
    python3 model_client.py [--endpoint URL] [--model MODEL_ID]
"""

import argparse
import requests
import json
import sys
from typing import List, Dict, Optional


class ModelClient:
    """Client for interacting with vLLM OpenAI-compatible endpoint."""
    
    def __init__(self, endpoint_url: str = "http://localhost:8000/v1"):
        """
        Initialize the client.
        
        Args:
            endpoint_url: Base URL of the vLLM endpoint
        """
        self.endpoint_url = endpoint_url.rstrip('/')
        self.model_name = None
    
    def get_models(self) -> List[Dict]:
        """Get list of available models."""
        try:
            response = requests.get(f"{self.endpoint_url}/models", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Error getting models: {e}", file=sys.stderr)
            return []
    
    def chat(self, messages: List[Dict], stream: bool = False, **kwargs) -> str:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to stream the response
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Complete response text (if not streaming) or generator (if streaming)
        """
        if not self.model_name:
            models = self.get_models()
            if models:
                self.model_name = models[0]["id"]
            else:
                raise ValueError("No models available")
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.endpoint_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_streaming_response(response)
            else:
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"Error in chat request: {e}", file=sys.stderr)
            raise
    
    def _handle_streaming_response(self, response):
        """Handle streaming response."""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    
                    if data == '[DONE]':
                        break
                    
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue
    
    def interactive_chat(self):
        """Start an interactive chat session."""
        print("=" * 60)
        print("AIM GPU Sharing - Model Client")
        print("=" * 60)
        print()
        
        # Get available models
        models = self.get_models()
        if models:
            print(f"Available models:")
            for model in models:
                print(f"  - {model['id']}")
            self.model_name = models[0]["id"]
            print(f"\nUsing model: {self.model_name}")
        else:
            print("Warning: No models detected, using default")
            self.model_name = "default"
        
        print()
        print("Enter your messages (type 'quit' or 'exit' to end)")
        print("=" * 60)
        print()
        
        conversation = []
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Add user message
                conversation.append({"role": "user", "content": user_input})
                
                # Get response
                print("\nAssistant: ", end="", flush=True)
                
                full_response = ""
                for chunk in self.chat(conversation, stream=True, temperature=0.7, max_tokens=1000):
                    print(chunk, end="", flush=True)
                    full_response += chunk
                
                print("\n")
                
                # Add assistant response
                conversation.append({"role": "assistant", "content": full_response})
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}", file=sys.stderr)
                print("Please try again.\n")


def main():
    parser = argparse.ArgumentParser(
        description="CLI client for AIM GPU Sharing vLLM endpoint"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/v1",
        help="vLLM endpoint URL (default: http://localhost:8000/v1)"
    )
    parser.add_argument(
        "--model",
        help="Model ID to use (default: auto-detect)"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )
    parser.add_argument(
        "--message",
        help="Single message to send (non-interactive mode)"
    )
    
    args = parser.parse_args()
    
    client = ModelClient(endpoint_url=args.endpoint)
    
    if args.model:
        client.model_name = args.model
    
    if args.list_models:
        models = client.get_models()
        if models:
            print("Available models:")
            for model in models:
                print(f"  - {model['id']}")
        else:
            print("No models available")
        return
    
    if args.message:
        # Non-interactive mode
        response = client.chat(
            [{"role": "user", "content": args.message}],
            temperature=0.7,
            max_tokens=1000
        )
        print(response)
    else:
        # Interactive mode
        client.interactive_chat()


if __name__ == '__main__':
    main()

