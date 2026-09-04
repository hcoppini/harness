/**
 * Harness Executive OS - Universal Web Browser API Bridge
 * Enables full functionality in standard web browsers (Render, Cloudflare, Chrome, Safari, Edge)
 * by polyfilling window.pywebview.api using HTTP RPC calls to /api/rpc/<method>.
 */

(function () {
  "use strict";

  // Only install bridge if native PyWebView is not present
  if (typeof window === "undefined") return;

  if (!window.pywebview || !window.pywebview.api) {
    console.log("[Harness Bridge] Initializing Web Browser RPC Bridge for Cloud/Web deployment...");

    const rpcCall = async (methodName, args) => {
      try {
        const response = await fetch(`/api/rpc/${methodName}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ args: args || [] }),
        });

        if (!response.ok) {
          const errPayload = await response.json().catch(() => ({ error: response.statusText }));
          throw new Error(errPayload.error || `HTTP ${response.status} from /api/rpc/${methodName}`);
        }

        const data = await response.json();
        return data.result !== undefined ? data.result : data;
      } catch (err) {
        console.error(`[Harness Bridge] RPC Error in ${methodName}:`, err);
        throw err;
      }
    };

    const apiProxy = new Proxy(
      {},
      {
        get(target, prop) {
          if (typeof prop !== "string") return target[prop];
          if (prop === "then" || prop === "toJSON") return undefined;

          // Client-side optimizations for browser environment
          if (prop === "open_external_url") {
            return async function (url) {
              if (url && (url.startsWith("http://") || url.startsWith("https://"))) {
                window.open(url, "_blank", "noopener,noreferrer");
                return true;
              }
              return false;
            };
          }

          if (prop === "open_in_vscode") {
            return async function (localPath) {
              if (localPath) {
                // Try vscode:// protocol handler in browser
                const formatted = localPath.replace(/\\/g, "/");
                window.location.href = `vscode://file/${encodeURI(formatted)}`;
                return true;
              }
              return false;
            };
          }

          // Default: dynamic async function making RPC call
          return async function (...args) {
            return await rpcCall(prop, args);
          };
        },
      }
    );

    window.pywebview = {
      api: apiProxy,
    };

    // Dispatch pywebviewready event for event listeners
    const fireReady = () => {
      try {
        window.dispatchEvent(new Event("pywebviewready"));
      } catch (e) {}
    };

    if (document.readyState === "complete" || document.readyState === "interactive") {
      setTimeout(fireReady, 0);
    } else {
      document.addEventListener("DOMContentLoaded", fireReady);
    }
  }
})();
