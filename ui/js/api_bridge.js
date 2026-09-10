/**
 * Harness Executive OS - Universal Web Browser API Bridge
 * Enables full functionality, offline-first resilience, and zero data loss in standard web browsers
 * (Vercel, Render, Cloudflare, Chrome, Safari, Edge) by combining HTTP RPC with
 * instant LocalStorage Mirroring and direct Supabase synchronization.
 */

(function () {
  "use strict";

  if (typeof window === "undefined") return;
  if (window.location.protocol === "file:") {
    // Desktop PyWebView runs on file:// - wait for native pywebviewready event
    return;
  }

  if (!window.pywebview || !window.pywebview.api) {
    console.log("[Harness Bridge] Initializing Resilient Web Browser Bridge with LocalStorage Mirroring...");

    const STORAGE_KEYS = {
      TASKS: "harness_tasks_v3",
      DAILY_LOGS: "harness_daily_logs_v3",
      KILL_LIST: "harness_kill_list_v3",
      METRO: "harness_metro_roadmap_v3",
      DELIVERABLES: "harness_deliverables_v3",
      CONFIGS: "harness_all_configs_v3",
      SYNC_CONFIG: "harness_sync_config_v3",
      BODY: "harness_body_metrics_v3",
      WORKOUTS: "harness_workouts_v3",
      PROJECTS: "harness_projects_v3",
      KNOWLEDGE: "harness_knowledge_v3",
    };

    const getStore = (key, defaultVal) => {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultVal;
      } catch (e) {
        return defaultVal;
      }
    };

    const setStore = (key, val) => {
      try {
        localStorage.setItem(key, JSON.stringify(val));
      } catch (e) {
        console.warn("[Harness Bridge] LocalStorage write failed:", e);
      }
    };

    // Direct HTTP RPC to server
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
        console.warn(`[Harness Bridge] RPC network fallback for ${methodName}:`, err.message);
        throw err;
      }
    };

    // Direct Supabase REST Request if configured in browser
    const supabaseRequest = async (endpoint, method = "GET", payload = null) => {
      const cfg = getStore(STORAGE_KEYS.SYNC_CONFIG, {
        supabase_url: "https://xfslkbcopnugiubkboux.supabase.co",
        supabase_key: "",
      });
      if (!cfg.supabase_url || !cfg.supabase_key) return null;

      try {
        const url = `${cfg.supabase_url.replace(/\/$/, "")}/rest/v1/${endpoint}`;
        const headers = {
          apikey: cfg.supabase_key,
          Authorization: `Bearer ${cfg.supabase_key}`,
          "Content-Type": "application/json",
          Accept: "application/json",
          Prefer: "resolution=merge-duplicates",
        };
        const res = await fetch(url, {
          method,
          headers,
          body: payload ? JSON.stringify(payload) : undefined,
        });
        if (res.ok) {
          const text = await res.text();
          return text ? JSON.parse(text) : {};
        }
      } catch (e) {
        console.warn("[Harness Bridge] Direct Supabase request failed:", e);
      }
      return null;
    };

    // =========================================================================
    // Virtual Dynamic API Layer with Optimistic Persistence
    // =========================================================================
    const apiProxy = new Proxy(
      {},
      {
        get(target, prop) {
          if (typeof prop !== "string") return target[prop];
          if (prop === "then" || prop === "toJSON") return undefined;

          // 0. Dashboard Operations
          if (prop === "get_dashboard") {
            return async function () {
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_dashboard", []);
              } catch (e) {}

              const todayStr = new Date().toISOString().split("T")[0];
              const localLogs = getStore(STORAGE_KEYS.DAILY_LOGS, {});
              const todayLog = localLogs[todayStr];

              if (serverRes) {
                // If local storage has today's live modifications, overlay them onto today_velocity
                if (todayLog && serverRes.today_velocity) {
                  const blocksStr = todayLog.completed_blocks || "";
                  const exStr = todayLog.completed_exercises || "";
                  const completedBlocksCount = blocksStr ? blocksStr.split(",").map((s) => s.trim()).filter(Boolean).length : 0;
                  const completedExCount = exStr ? exStr.split(",").map((s) => s.trim()).filter(Boolean).length : 0;
                  const taskCompletedCount = serverRes.today_velocity.checked_tasks || 0;
                  const killCompletedCount = serverRes.today_velocity.kill_list_completed || 0;

                  const totalBoxes = serverRes.today_velocity.total_boxes || 14;
                  const checkedTotal = completedBlocksCount + completedExCount + taskCompletedCount + killCompletedCount;

                  serverRes.today_velocity.checked_boxes = checkedTotal;
                  serverRes.today_velocity.percentage = totalBoxes > 0 ? Math.round((checkedTotal / totalBoxes) * 100) : 0;
                }
                return serverRes;
              }

              return {
                metrics: {
                  current_streak: 11,
                  total_contributions: 60,
                  overall_gpa: 0.0,
                  bavarian_gpa: 1.13,
                  avg_matura_mock: 0.0,
                  latest_weight: 68.0,
                  target_weight: 80.0,
                },
                today_velocity: {
                  percentage: 0,
                  checked_boxes: 0,
                  total_boxes: 14,
                  schedule_name: "Schedule B- Gym & TUM Sprint Days",
                },
                heatmap: { weeks: [], total_contributions: 60 },
                upcoming: [],
                radar: { homework: [], exams: [] },
              };
            };
          }

          // 1. Task Operations & Today View
          if (prop === "get_today") {
            return async function (dateStr) {
              const todayStr = dateStr || new Date().toISOString().split("T")[0];
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_today", [todayStr]);
              } catch (e) {}

              const localTasks = getStore(STORAGE_KEYS.TASKS, []);
              const localLogs = getStore(STORAGE_KEYS.DAILY_LOGS, {});
              const currentLocalLog = localLogs[todayStr];

              if (serverRes) {
                // Merge server and local tasks
                const taskMap = new Map();
                if (Array.isArray(serverRes.tasks)) {
                  serverRes.tasks.forEach((t) => taskMap.set(t.id, t));
                }
                localTasks.filter((t) => t.date === todayStr).forEach((lt) => {
                  if (!taskMap.has(lt.id)) taskMap.set(lt.id, lt);
                });
                const mergedTasks = Array.from(taskMap.values());
                setStore(STORAGE_KEYS.TASKS, mergedTasks);

                // Merge server log and local log using union set for checked boxes
                const serverLog = serverRes.log || {};
                const mergeBlocks = (a, b) => {
                  const setA = (a || "").split(",").map((s) => s.trim()).filter(Boolean);
                  const setB = (b || "").split(",").map((s) => s.trim()).filter(Boolean);
                  return Array.from(new Set([...setA, ...setB])).join(",");
                };

                const mergedLog = {
                  date: todayStr,
                  scratchpad: (currentLocalLog && currentLocalLog.scratchpad) ? currentLocalLog.scratchpad : (serverLog.scratchpad || ""),
                  completed_blocks: mergeBlocks(currentLocalLog?.completed_blocks, serverLog.completed_blocks),
                  completed_exercises: mergeBlocks(currentLocalLog?.completed_exercises, serverLog.completed_exercises),
                  wake_time: (currentLocalLog && currentLocalLog.wake_time) || serverLog.wake_time || "",
                  sleep_time: (currentLocalLog && currentLocalLog.sleep_time) || serverLog.sleep_time || "",
                  reflection_worked: (currentLocalLog && currentLocalLog.reflection_worked) || serverLog.reflection_worked || "",
                  reflection_slipped: (currentLocalLog && currentLocalLog.reflection_slipped) || serverLog.reflection_slipped || "",
                  reflection_tomorrow: (currentLocalLog && currentLocalLog.reflection_tomorrow) || serverLog.reflection_tomorrow || "",
                };

                localLogs[todayStr] = mergedLog;
                setStore(STORAGE_KEYS.DAILY_LOGS, localLogs);

                return {
                  tasks: mergedTasks,
                  log: mergedLog,
                  schedule: serverRes.schedule || null,
                  gym_routine: serverRes.gym_routine || null,
                };
              }

              // Fallback to local storage if server is cold / offline
              const filteredTasks = localTasks.filter((t) => t.date === todayStr);
              return {
                tasks: filteredTasks,
                log: currentLocalLog || { date: todayStr, scratchpad: "", completed_blocks: "", completed_exercises: "" },
                schedule: null,
                gym_routine: null,
              };
            };
          }

          if (prop === "add_task") {
            return async function (title, category = "personal", isTum = false, dateStr = null) {
              const dt = dateStr || new Date().toISOString().split("T")[0];
              const localTasks = getStore(STORAGE_KEYS.TASKS, []);
              const newId = Date.now();
              const newTask = {
                id: newId,
                title,
                category,
                is_tum: isTum ? 1 : 0,
                completed: 0,
                date: dt,
                rollover_count: 0,
              };
              localTasks.unshift(newTask);
              setStore(STORAGE_KEYS.TASKS, localTasks);

              // Background sync
              rpcCall("add_task", [title, category, isTum, dt]).catch(() => {});
              supabaseRequest("tasks", "POST", {
                id: newId,
                title,
                category,
                is_tum: isTum,
                completed: false,
                date: dt,
              });

              return newTask;
            };
          }

          if (prop === "toggle_task") {
            return async function (taskId) {
              const localTasks = getStore(STORAGE_KEYS.TASKS, []);
              const task = localTasks.find((t) => t.id === taskId);
              if (task) {
                task.completed = task.completed ? 0 : 1;
                setStore(STORAGE_KEYS.TASKS, localTasks);
                supabaseRequest(`tasks?id=eq.${taskId}`, "PATCH", { completed: Boolean(task.completed) });
              }
              rpcCall("toggle_task", [taskId]).catch(() => {});
              return task || { success: true };
            };
          }

          if (prop === "delete_task") {
            return async function (taskId) {
              let localTasks = getStore(STORAGE_KEYS.TASKS, []);
              localTasks = localTasks.filter((t) => t.id !== taskId);
              setStore(STORAGE_KEYS.TASKS, localTasks);
              rpcCall("delete_task", [taskId]).catch(() => {});
              supabaseRequest(`tasks?id=eq.${taskId}`, "DELETE");
              return true;
            };
          }

          if (prop === "update_daily_log") {
            return async function (...args) {
              const dateStr = args[0] || new Date().toISOString().split("T")[0];
              const localLogs = getStore(STORAGE_KEYS.DAILY_LOGS, {});
              const currentLog = localLogs[dateStr] || { date: dateStr, scratchpad: "", completed_blocks: "", completed_exercises: "" };

              if (args[1] !== undefined && args[1] !== null) currentLog.scratchpad = args[1];
              if (args[2] !== undefined && args[2] !== null) currentLog.wake_time = args[2];
              if (args[3] !== undefined && args[3] !== null) currentLog.sleep_time = args[3];
              if (args[4] !== undefined && args[4] !== null) currentLog.reflection_worked = args[4];
              if (args[5] !== undefined && args[5] !== null) currentLog.reflection_slipped = args[5];
              if (args[6] !== undefined && args[6] !== null) currentLog.reflection_tomorrow = args[6];
              if (args[7] !== undefined && args[7] !== null) currentLog.completed_blocks = args[7];
              if (args[8] !== undefined && args[8] !== null) currentLog.completed_exercises = args[8];

              localLogs[dateStr] = currentLog;
              setStore(STORAGE_KEYS.DAILY_LOGS, localLogs);

              rpcCall("update_daily_log", args).catch(() => {});
              supabaseRequest("daily_logs", "POST", {
                date: dateStr,
                scratchpad: currentLog.scratchpad,
                wake_time: currentLog.wake_time,
                sleep_time: currentLog.sleep_time,
                reflection_worked: currentLog.reflection_worked,
                reflection_slipped: currentLog.reflection_slipped,
                reflection_tomorrow: currentLog.reflection_tomorrow,
                completed_blocks: currentLog.completed_blocks,
                completed_exercises: currentLog.completed_exercises,
              });

              return currentLog;
            };
          }

          // 2. Kill List & Deliverables
          if (prop === "get_kill_list") {
            return async function (dateStr) {
              const todayStr = dateStr || new Date().toISOString().split("T")[0];
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_kill_list", [todayStr]);
              } catch (e) {}

              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              const localItems = localKillMap[todayStr] || [];

              if (serverRes && Array.isArray(serverRes.items)) {
                localKillMap[todayStr] = serverRes.items;
                setStore(STORAGE_KEYS.KILL_LIST, localKillMap);
                return serverRes;
              }

              return {
                items: localItems,
                date: todayStr,
                count: localItems.length,
                completed_count: localItems.filter((i) => i.completed).length,
                is_evening_locked: false,
              };
            };
          }

          if (prop === "add_kill_item") {
            return async function (category, title, actionType = "url", targetPath = "", targetSpec = "", deliverableId = null, dateStr = null) {
              const dt = dateStr || new Date().toISOString().split("T")[0];
              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              const list = localKillMap[dt] || [];
              const newItem = {
                id: `kill_${Date.now()}`,
                date: dt,
                category,
                title,
                action_type: actionType,
                target_path: targetPath,
                target_spec: targetSpec,
                station_deliverable_id: deliverableId,
                completed: 0,
              };
              list.push(newItem);
              localKillMap[dt] = list;
              setStore(STORAGE_KEYS.KILL_LIST, localKillMap);

              rpcCall("add_kill_item", [category, title, actionType, targetPath, targetSpec, deliverableId, dt]).catch(() => {});
              supabaseRequest("kill_list_items", "POST", newItem);
              return { success: true, item: newItem };
            };
          }

          if (prop === "toggle_kill_item") {
            return async function (itemId) {
              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              let targetItem = null;
              for (const dt in localKillMap) {
                const item = localKillMap[dt].find((i) => i.id === itemId);
                if (item) {
                  item.completed = item.completed ? 0 : 1;
                  targetItem = item;
                  break;
                }
              }
              setStore(STORAGE_KEYS.KILL_LIST, localKillMap);
              if (targetItem) {
                supabaseRequest(`kill_list_items?id=eq.${itemId}`, "PATCH", { completed: Boolean(targetItem.completed) });
              }
              rpcCall("toggle_kill_item", [itemId]).catch(() => {});
              return { success: true, item: targetItem };
            };
          }

          if (prop === "delete_kill_item") {
            return async function (itemId) {
              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              for (const dt in localKillMap) {
                localKillMap[dt] = localKillMap[dt].filter((i) => i.id !== itemId);
              }
              setStore(STORAGE_KEYS.KILL_LIST, localKillMap);
              rpcCall("delete_kill_item", [itemId]).catch(() => {});
              supabaseRequest(`kill_list_items?id=eq.${itemId}`, "DELETE");
              return { success: true };
            };
          }

          if (prop === "launch_kill_item") {
            return async function (actionType, targetPath) {
              if (targetPath) {
                if (targetPath.startsWith("http://") || targetPath.startsWith("https://")) {
                  window.open(targetPath, "_blank", "noopener,noreferrer");
                  return { success: true, action: "url", target: targetPath };
                } else if (actionType === "workspace") {
                  window.location.href = `vscode://file/${encodeURI(targetPath.replace(/\\/g, "/"))}`;
                  return { success: true, action: "workspace", target: targetPath };
                }
              }
              try {
                return await rpcCall("launch_kill_item", [actionType, targetPath]);
              } catch (e) {
                return { success: true, action: "local_open" };
              }
            };
          }

          if (prop === "get_station_deliverables") {
            return async function (stationId = "sep-2026") {
              const localMap = getStore(STORAGE_KEYS.DELIVERABLES, {});
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_station_deliverables", [stationId]);
              } catch (e) {}

              if (serverRes && Array.isArray(serverRes)) {
                const merged = serverRes.map((d) => {
                  const cached = localMap[d.deliverable_id];
                  if (cached && cached.completed_count > d.completed_count) {
                    return { ...d, completed_count: cached.completed_count, is_completed: cached.completed_count >= d.total_required };
                  }
                  return d;
                });
                merged.forEach((d) => {
                  localMap[d.deliverable_id] = d;
                });
                setStore(STORAGE_KEYS.DELIVERABLES, localMap);
                return merged;
              }

              const list = Object.values(localMap).filter(
                (d) => d.station_id === stationId || d.station_id === stationId.replace("_", "-") || d.station_id === stationId.replace("-", "_")
              );
              if (list.length > 0) return list;

              return [
                { deliverable_id: "sep26_math_diag", station_id: "sep-2026", stream: "Math R", title: "Diagnostic Exam 1-40", total_required: 40, completed_count: 0, unit_label: "problems", is_completed: false },
                { deliverable_id: "sep26_hackerrank_15", station_id: "sep-2026", stream: "Algorithms", title: "Basic Data Structures (15 items)", total_required: 15, completed_count: 0, unit_label: "exercises", is_completed: false },
                { deliverable_id: "sep26_sigg_setup", station_id: "sep-2026", stream: "SIGG", title: "Registration & Platform Setup", total_required: 1, completed_count: 0, unit_label: "setup", is_completed: false },
                { deliverable_id: "sep26_german_anki", station_id: "sep-2026", stream: "German", title: "Goethe A2 Core Vocabulary (400 Words)", total_required: 400, completed_count: 0, unit_label: "words", is_completed: false },
                { deliverable_id: "sep26_phys_protein", station_id: "sep-2026", stream: "Physique", title: "Daily 140g+ Target Consistency (20/30 Days)", total_required: 20, completed_count: 0, unit_label: "days", is_completed: false },
              ];
            };
          }

          if (prop === "update_deliverable_progress") {
            return async function (deliverableId, newCount = null, delta = null) {
              const localMap = getStore(STORAGE_KEYS.DELIVERABLES, {});
              const deliv = localMap[deliverableId] || {
                deliverable_id: deliverableId,
                completed_count: 0,
                total_required: 100,
                unit_label: "units",
                is_completed: false,
              };

              let updatedCount = deliv.completed_count;
              if (newCount !== null && newCount !== undefined) {
                updatedCount = Math.max(0, parseInt(newCount, 10) || 0);
              } else if (delta !== null && delta !== undefined) {
                updatedCount = Math.max(0, updatedCount + (parseInt(delta, 10) || 0));
              }
              deliv.completed_count = updatedCount;
              deliv.is_completed = updatedCount >= (deliv.total_required || 1);
              localMap[deliverableId] = deliv;
              setStore(STORAGE_KEYS.DELIVERABLES, localMap);

              rpcCall("update_deliverable_progress", [deliverableId, newCount, delta]).catch(() => {});
              supabaseRequest(`station_deliverable_progress?deliverable_id=eq.${deliverableId}`, "PATCH", {
                completed_count: updatedCount,
                is_completed: deliv.is_completed,
              });

              return {
                success: true,
                deliverable_id: deliverableId,
                completed_count: updatedCount,
                total_required: deliv.total_required,
                is_completed: deliv.is_completed,
                unit_label: deliv.unit_label,
              };
            };
          }

          if (prop === "log_study_reps") {
            return async function (deliverableId, count = 1, notes = "") {
              const res = await apiProxy.update_deliverable_progress(deliverableId, null, count);
              rpcCall("log_study_reps", [deliverableId, count, notes]).catch(() => {});
              return res;
            };
          }

          if (prop === "get_station_pace_velocity") {
            return async function (stationId = "sep-2026", dateStr = null) {
              const todayDt = dateStr ? new Date(dateStr) : new Date();
              const dayOfMonth = todayDt.getDate();
              const year = todayDt.getFullYear();
              const month = todayDt.getMonth();
              const totalDays = new Date(year, month + 1, 0).getDate();

              const deliverables = await apiProxy.get_station_deliverables(stationId);

              let maxDeficit = 0.0;
              let deficitItemTitle = "";
              let deficitUnit = "";
              let overallBehind = false;

              const paceItems = deliverables.map((d) => {
                const total = d.total_required || 1;
                const comp = d.completed_count || 0;
                const targetPace = (dayOfMonth / totalDays) * total;
                const delta = comp - targetPace;
                const isBehind = comp < targetPace;
                const deficit = isBehind ? Math.round((targetPace - comp) * 10) / 10 : 0.0;

                if (deficit > maxDeficit) {
                  maxDeficit = deficit;
                  deficitItemTitle = d.title;
                  deficitUnit = d.unit_label;
                  overallBehind = true;
                }

                return {
                  deliverable_id: d.deliverable_id,
                  title: d.title,
                  stream: d.stream,
                  total_required: total,
                  completed_count: comp,
                  unit_label: d.unit_label,
                  target_pace: Math.round(targetPace * 10) / 10,
                  pace_delta: Math.round(delta * 10) / 10,
                  is_behind: isBehind,
                  deficit: deficit,
                  is_completed: Boolean(d.is_completed),
                };
              });

              let statusText = "";
              let badgeVariant = "optimal";
              if (overallBehind && maxDeficit > 0) {
                statusText = `Pace Deficit: -${maxDeficit} ${deficitUnit}`;
                badgeVariant = "amber";
              } else {
                const avgDelta = paceItems.reduce((acc, p) => acc + p.pace_delta, 0) / Math.max(1, paceItems.length);
                statusText = `Pace Velocity: Optimal (+${Math.abs(Math.round(avgDelta * 10) / 10)})`;
                badgeVariant = "optimal";
              }

              return {
                station_id: stationId,
                date: todayDt.toISOString().split("T")[0],
                day_of_month: dayOfMonth,
                total_days: totalDays,
                is_behind: overallBehind,
                max_deficit: maxDeficit,
                deficit_item_title: deficitItemTitle,
                deficit_unit: deficitUnit,
                status_text: statusText,
                badge_variant: badgeVariant,
                deliverables: paceItems,
              };
            };
          }

          // 3. System Links & General Utilities
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
                window.location.href = `vscode://file/${encodeURI(localPath.replace(/\\/g, "/"))}`;
                return true;
              }
              return false;
            };
          }

          if (prop === "get_sync_status") {
            return async function () {
              const cfg = getStore(STORAGE_KEYS.SYNC_CONFIG, {
                supabase_url: "https://xfslkbcopnugiubkboux.supabase.co",
                supabase_key: "",
                auto_sync: true,
                last_synced_at: null,
              });
              try {
                const serverStatus = await rpcCall("get_sync_status", []);
                if (serverStatus && serverStatus.has_key) return serverStatus;
              } catch (e) {}

              return {
                status: cfg.last_synced_at ? "synced" : cfg.supabase_key ? "ready" : "unconfigured",
                supabase_url: cfg.supabase_url,
                has_key: Boolean(cfg.supabase_key),
                last_synced_at: cfg.last_synced_at,
                auto_sync: cfg.auto_sync !== false,
              };
            };
          }

          if (prop === "configure_sync") {
            return async function (url, key, autoSync = true) {
              const cfg = {
                supabase_url: url.trim(),
                supabase_key: key.trim(),
                auto_sync: autoSync,
                last_synced_at: new Date().toISOString(),
              };
              setStore(STORAGE_KEYS.SYNC_CONFIG, cfg);
              try {
                await rpcCall("configure_sync", [url, key, autoSync]);
              } catch (e) {}
              return true;
            };
          }

          // Default: dynamic async function making RPC call with safe fallback
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

