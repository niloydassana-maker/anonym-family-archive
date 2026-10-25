"""Token Harbor Local Gateway Proxy for Cline.

Exposes a local OpenAI-compatible API endpoint on http://127.0.0.1:8080/v1
backed by the 17-key Token Harbor rotation pool.
Cline connects to http://127.0.0.1:8080/v1 with model `deepseek-v4.1-flash:free`.
"""

import sys
import os
import json
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

BASE_DIR = r"D:\anonym"
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from tokenharbor_router import TokenHarborRouter, DEEPSEEK_FLASH_MODEL, TOKEN_HARBOR_URL

PORT = 8080
router = TokenHarborRouter()

class ClineProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        print(f"[{time.strftime('%H:%M:%S')}] {self.command} {self.path} - {args[0] if args else ''}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/v1/models", "/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = {
                "object": "list",
                "data": [
                    {
                        "id": DEEPSEEK_FLASH_MODEL,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "tokenharbor"
                    },
                    {
                        "id": "deepseek-ai/deepseek-v4.1-flash",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "tokenharbor"
                    }
                ]
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        if self.path in ("/health", "/status", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            st = router.status()
            self.wfile.write(json.dumps(st, indent=2).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path not in ("/v1/chat/completions", "/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode("utf-8"))
            return

        messages = body.get("messages", [])
        stream = body.get("stream", False)
        temperature = body.get("temperature", 0.2)
        max_tokens = body.get("max_tokens", 4000)

        # Extract system prompt and user text if standard format
        system_prompt = None
        user_prompt_parts = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle Cline multi-part content
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content = "\n".join(text_parts)
            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user":
                user_prompt_parts.append(content)
            elif role == "assistant":
                user_prompt_parts.append(f"[Prior Assistant]:\n{content}")

        combined_prompt = "\n\n".join(user_prompt_parts) if user_prompt_parts else "Hello"

        # Dispatch via 17-key Token Harbor Router (with 120s timeout and automatic 429 rotation)
        success, text, model_used, error_msg = router.call(
            prompt=combined_prompt,
            system_prompt=system_prompt,
            timeout=120
        )

        if not success or not text:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            err_resp = {
                "error": {
                    "message": error_msg or "Token Harbor generation failed across all ready keys",
                    "type": "tokenharbor_error",
                    "code": 502
                }
            }
            self.wfile.write(json.dumps(err_resp).encode("utf-8"))
            return

        # Format OpenAI compatible response
        resp_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created_ts = int(time.time())

        if stream:
            # Server-Sent Events stream for Cline
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Emit single delta chunk followed by [DONE]
            chunk = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": model_used,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": text},
                        "finish_reason": "stop"
                    }
                ]
            }
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            resp = {
                "id": resp_id,
                "object": "chat.completion",
                "created": created_ts,
                "model": model_used,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(combined_prompt) // 4,
                    "completion_tokens": len(text) // 4,
                    "total_tokens": (len(combined_prompt) + len(text)) // 4
                }
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, ClineProxyHandler)
    st = router.status()
    print("=" * 65)
    print(f"🚀 TOKEN HARBOR CLINE GATEWAY PROXY LIVE on http://127.0.0.1:{PORT}/v1")
    print(f"🔑 Loaded Keys: {st.get('total_keys', 0)} | States: {st.get('states', {})}")
    print(f"🤖 Default Model: {DEEPSEEK_FLASH_MODEL}")
    print("=" * 65)
    print("Ready to serve Cline requests with automatic 17-key rotation & 429 backoff.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Cline gateway proxy...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
