#!/usr/bin/env python3
"""
Simple MCP client to interact with Uptime Arena
"""
import asyncio
import json
import websockets
import sys

async def main():
    # MCP WebSocket endpoint
    uri = "ws://18.222.128.167:8080/mcp/JY26qIQ4LxN99wl-Z2xxxA?token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzZXNzaW9uOkpZMjZxSVE0THhOOTl3bC1aMnh4eEEiLCJpc3MiOiJ1cHRpbWVhcmVuYS5pbyIsImF1ZCI6InVwdGltZWFyZW5hLW1jcCIsImFnZW50X2lkIjoiYzhkNDNmZTgtNDk5Ni00NThhLWE4NDctOTg1N2Q5N2RmNmExIiwicHJvYmxlbV9pZCI6ImluY29ycmVjdF9wb3J0X2Fzc2lnbm1lbnQiLCJhbGxvd2VkX25hbWVzcGFjZXMiOlsiYXN0cm9ub215LXNob3AiLCJvYnNlcnZlIl0sInRpZXIiOiJmcmVlIiwiaWF0IjoxNzcxMzY5NTYyLCJleHAiOjE3NzEzNzEzNjIsImp0aSI6IlBwczBsNUJkc0dVVldMWF9WcFM3QXcifQ.fRm2EqtrHX86xbqBI__jqmr0cGjI267TJyQXO_Q4wIN5Bd6KUbceTJQ-VUqS9SJBiSAI5J9pn5DLyq9Iw-bnU-DDYEmYqAunDoy8-eDMX4-r8hCU8H_aV2O1tVyjHqEC170H7_wBKXXzEdJQo-XY0BijDTGAJviZIU9DEGMCJSZutu9Z-0SWpmz49evYMUgl_WuA3KAtWKLxYFQA4jMak7z4Jo1gLGfyuyZc8XeXLqBgxEuzNASIdGD3MTF0jr_2ZOKpdDHQYv2jd_vW5lqgmJDkhe_3EHwZnWRDLoLjGkfHB0kbfNBekOoflSSzKP2qmI97nY_eT0NDkSJmAyHoIw"

    print("Connecting to MCP server...")
    async with websockets.connect(uri) as ws:
        # Send initialize request
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "cli-client",
                    "version": "1.0"
                }
            }
        }
        await ws.send(json.dumps(init_msg))
        response = await ws.recv()
        print(f"Init response: {response}")

        # List available tools
        tools_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        await ws.send(json.dumps(tools_msg))
        response = await ws.recv()
        print(f"Tools: {response}")

        # Try to run a kubectl command to diagnose
        # First let's see what's in the astronomy-shop namespace
        kubectl_msg = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "kubectl_get",
                "arguments": {
                    "resource": "services",
                    "namespace": "astronomy-shop"
                }
            }
        }
        await ws.send(json.dumps(kubectl_msg))
        response = await ws.recv()
        print(f"Services: {response}")

if __name__ == "__main__":
    asyncio.run(main())
