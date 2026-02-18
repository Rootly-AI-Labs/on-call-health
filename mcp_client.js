const WebSocket = require('ws');

const uri = "ws://18.222.128.167:8080/mcp/JY26qIQ4LxN99wl-Z2xxxA?token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzZXNzaW9uOkpZMjZxSVE0THhOOTl3bC1aMnh4eEEiLCJpc3MiOiJ1cHRpbWVhcmVuYS5pbyIsImF1ZCI6InVwdGltZWFyZW5hLW1jcCIsImFnZW50X2lkIjoiYzhkNDNmZTgtNDk5Ni00NThhLWE4NDctOTg1N2Q5N2RmNmExIiwicHJvYmxlbV9pZCI6ImluY29ycmVjdF9wb3J0X2Fzc2lnbm1lbnQiLCJhbGxvd2VkX25hbWVzcGFjZXMiOlsiYXN0cm9ub215LXNob3AiLCJvYnNlcnZlIl0sInRpZXIiOiJmcmVlIiwiaWF0IjoxNzcxMzY5NTYyLCJleHAiOjE3NzEzNzEzNjIsImp0aSI6IlBwczBsNUJkc0dVVldMWF9WcFM3QXcifQ.fRm2EqtrHX86xbqBI__jqmr0cGjI267TJyQXO_Q4wIN5Bd6KUbceTJQ-VUqS9SJBiSAI5J9pn5DLyq9Iw-bnU-DDYEmYqAunDoy8-eDMX4-r8hCU8H_aV2O1tVyjHqEC170H7_wBKXXzEdJQo-XY0BijDTGAJviZIU9DEGMCJSZutu9Z-0SWpmz49evYMUgl_WuA3KAtWKLxYFQA4jMak7z4Jo1gLGfyuyZc8XeXLqBgxEuzNASIdGD3MTF0jr_2ZOKpdDHQYv2jd_vW5lqgmJDkhe_3EHwZnWRDLoLjGkfHB0kbfNBekOoflSSzKP2qmI97nY_eT0NDkSJmAyHoIw";

console.log("Connecting to MCP server...");
const ws = new WebSocket(uri);

let id = 1;
const send = (method, params = {}) => {
  const msg = { jsonrpc: "2.0", id: id++, method, params };
  ws.send(JSON.stringify(msg));
  return id - 1;
};

ws.on('open', () => {
  console.log("Connected!");

  // Initialize
  send("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "cli-client", version: "1.0" }
  });
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);
  console.log("Received:", JSON.stringify(msg, null, 2));

  // After init, list tools
  if (msg.id === 1) {
    setTimeout(() => {
      console.log("\n--- Listing tools ---");
      send("tools/list", {});
    }, 500);
  }

  // If tools list, get services
  if (msg.result?.tools) {
    console.log("\n--- Tools available ---");
    msg.result.tools.forEach(t => console.log(`- ${t.name}: ${t.description}`));

    setTimeout(() => {
      console.log("\n--- Getting services ---");
      send("tools/call", {
        name: "kubectl_get",
        arguments: { resource: "services", namespace: "astronomy-shop" }
      });
    }, 500);
  }
});

ws.on('error', (err) => {
  console.error("Error:", err);
});

ws.on('close', () => {
  console.log("Disconnected");
});
