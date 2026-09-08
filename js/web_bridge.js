/**
 * HARNESS // Web & Cloud Polyfill API Bridge (Neutralized)
 * Neutralized to prevent mock data collision with native PyWebView and api_bridge.js.
 * Real data is provided by PyWebView native API or api_bridge.js HTTP RPC.
 */
(function () {
  // No-op: api_bridge.js provides real RPC to server.py, and main.py uses native PyWebView.
  return;
})();
