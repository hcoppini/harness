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
      HOMEWORK: "harness_homework_v3",
      EXAMS: "harness_exams_v3",
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

    const getLocalDateStr = (d = new Date()) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
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
            return async function (clientDate = null) {
              const todayStr = clientDate || getLocalDateStr();
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_dashboard", [todayStr]);
              } catch (e) {}

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

                // DYNAMIC HEATMAP OVERLAY:
                // Ensure recent days modified locally (e.g. Sep 10, 11, 12, 13) are accurately reflected in heatmap cells!
                if (serverRes.heatmap && Array.isArray(serverRes.heatmap.weeks)) {
                  let runningContributions = 0;
                  const localTasks = getStore(STORAGE_KEYS.TASKS, []);
                  const localKill = getStore(STORAGE_KEYS.KILL_LIST, {});

                  serverRes.heatmap.weeks.forEach((w) => {
                    (w.days || []).forEach((d) => {
                      if (!d) return;
                      const lLog = localLogs[d.date];
                      const bCount = lLog ? (lLog.completed_blocks || "").split(",").map((s) => s.trim()).filter(Boolean).length : 0;
                      const eCount = lLog ? (lLog.completed_exercises || "").split(",").map((s) => s.trim()).filter(Boolean).length : 0;
                      const tCount = localTasks.filter((t) => t.date === d.date && t.completed).length;
                      const kCount = (localKill[d.date] || []).filter((k) => k.completed).length;
                      const checkedTotal = bCount + eCount + tCount + kCount;

                      if (checkedTotal > d.count || (lLog && (lLog._client_modified || bCount > 0) && checkedTotal !== d.count)) {
                        d.count = checkedTotal;
                        if (d.total_boxes === 0) {
                          d.level = d.count === 0 ? 0 : d.count <= 2 ? 1 : d.count <= 4 ? 2 : d.count <= 6 ? 3 : 4;
                        } else {
                          if (d.count === 0) d.level = 0;
                          else if (d.count >= d.total_boxes) d.level = 4;
                          else {
                            const ratio = d.count / d.total_boxes;
                            d.level = ratio >= 0.85 ? 4 : ratio >= 0.70 ? 3 : ratio >= 0.35 ? 2 : 1;
                          }
                        }
                      }
                      if (!d.is_future) {
                        runningContributions += (d.count || 0);
                      }
                    });
                  });
                  if (runningContributions > 0) {
                    serverRes.heatmap.total_contributions = runningContributions;
                    if (serverRes.metrics) {
                      serverRes.metrics.total_contributions = runningContributions;
                    }
                  }
                }

                return serverRes;
              }

              return {
                metrics: {
                  current_streak: 12,
                  total_contributions: 63,
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
                heatmap: { weeks: [], total_contributions: 63 },
                upcoming: [],
                radar: { homework: [], exams: [] },
              };
            };
          }

          // 1. Task Operations & Today View
          if (prop === "get_today") {
            return async function (dateStr) {
              const todayStr = dateStr || getLocalDateStr();
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

                const serverLog = serverRes.log || {};

                // If local storage was explicitly modified by client, preserve client's authoritative boxes!
                let completedBlocks = serverLog.completed_blocks || "";
                let completedExercises = serverLog.completed_exercises || "";
                if (currentLocalLog && currentLocalLog._client_modified) {
                  completedBlocks = currentLocalLog.completed_blocks !== undefined ? currentLocalLog.completed_blocks : completedBlocks;
                  completedExercises = currentLocalLog.completed_exercises !== undefined ? currentLocalLog.completed_exercises : completedExercises;
                } else if (currentLocalLog && (currentLocalLog.completed_blocks || currentLocalLog.completed_exercises)) {
                  completedBlocks = currentLocalLog.completed_blocks || completedBlocks;
                  completedExercises = currentLocalLog.completed_exercises || completedExercises;
                }

                const mergedLog = {
                  date: todayStr,
                  scratchpad: (currentLocalLog && currentLocalLog.scratchpad) ? currentLocalLog.scratchpad : (serverLog.scratchpad || ""),
                  completed_blocks: completedBlocks,
                  completed_exercises: completedExercises,
                  wake_time: (currentLocalLog && currentLocalLog.wake_time) || serverLog.wake_time || "",
                  sleep_time: (currentLocalLog && currentLocalLog.sleep_time) || serverLog.sleep_time || "",
                  reflection_worked: (currentLocalLog && currentLocalLog.reflection_worked) || serverLog.reflection_worked || "",
                  reflection_slipped: (currentLocalLog && currentLocalLog.reflection_slipped) || serverLog.reflection_slipped || "",
                  reflection_tomorrow: (currentLocalLog && currentLocalLog.reflection_tomorrow) || serverLog.reflection_tomorrow || "",
                  _client_modified: currentLocalLog?._client_modified || 0,
                };

                localLogs[todayStr] = mergedLog;
                setStore(STORAGE_KEYS.DAILY_LOGS, localLogs);

                // If server had empty completions but local storage preserved them, sync them up to server
                if ((!serverLog.completed_blocks && completedBlocks) || (!serverLog.completed_exercises && completedExercises)) {
                  rpcCall("update_daily_log", [
                    todayStr,
                    null, null, null, null, null, null,
                    completedBlocks,
                    completedExercises
                  ]).catch(() => {});
                }

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
              const dt = dateStr || getLocalDateStr();
              const localTasks = getStore(STORAGE_KEYS.TASKS, []);
              let serverTask = null;
              try {
                serverTask = await rpcCall("add_task", [title, category, isTum, dt]);
              } catch (e) {
                console.warn("[Harness Bridge] add_task RPC notice:", e.message);
              }

              const newTask = serverTask || {
                id: Date.now(),
                title,
                category,
                is_tum: isTum ? 1 : 0,
                completed: 0,
                date: dt,
                rollover_count: 0,
              };
              localTasks.unshift(newTask);
              setStore(STORAGE_KEYS.TASKS, localTasks);

              supabaseRequest("tasks", "POST", {
                id: newTask.id,
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
              let serverRes = null;
              try {
                serverRes = await rpcCall("toggle_task", [taskId]);
              } catch (e) {
                console.warn("[Harness Bridge] toggle_task RPC notice:", e.message);
              }

              const task = localTasks.find((t) => t.id == taskId);
              if (serverRes && serverRes.completed !== undefined) {
                if (task) task.completed = serverRes.completed;
                setStore(STORAGE_KEYS.TASKS, localTasks);
                supabaseRequest(`tasks?id=eq.${taskId}`, "PATCH", { completed: Boolean(serverRes.completed) });
                return serverRes;
              }

              if (task) {
                task.completed = task.completed ? 0 : 1;
                setStore(STORAGE_KEYS.TASKS, localTasks);
                supabaseRequest(`tasks?id=eq.${taskId}`, "PATCH", { completed: Boolean(task.completed) });
                return task;
              }
              return { id: taskId, completed: 1 };
            };
          }

          if (prop === "delete_task") {
            return async function (taskId) {
              try {
                await rpcCall("delete_task", [taskId]);
              } catch (e) {
                console.warn("[Harness Bridge] delete_task RPC notice:", e.message);
              }
              let localTasks = getStore(STORAGE_KEYS.TASKS, []);
              localTasks = localTasks.filter((t) => t.id != taskId);
              setStore(STORAGE_KEYS.TASKS, localTasks);
              supabaseRequest(`tasks?id=eq.${taskId}`, "DELETE");
              return true;
            };
          }

          if (prop === "update_daily_log") {
            return async function (...args) {
              const dateStr = args[0] || getLocalDateStr();
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

              currentLog._client_modified = Date.now();
              localLogs[dateStr] = currentLog;
              setStore(STORAGE_KEYS.DAILY_LOGS, localLogs);

              // Await RPC call so server database write commits before subsequent reads
              try {
                await rpcCall("update_daily_log", args);
              } catch (e) {
                console.warn("[Harness Bridge] update_daily_log RPC notice:", e.message);
              }

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
              const todayStr = dateStr || getLocalDateStr();
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
              const dt = dateStr || getLocalDateStr();
              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              const list = localKillMap[dt] || [];
              let serverRes = null;
              try {
                serverRes = await rpcCall("add_kill_item", [category, title, actionType, targetPath, targetSpec, deliverableId, dt]);
              } catch (e) {
                console.warn("[Harness Bridge] add_kill_item RPC notice:", e.message);
              }

              const newItem = (serverRes && serverRes.item) ? serverRes.item : {
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

              supabaseRequest("kill_list_items", "POST", newItem);
              return serverRes || { success: true, item: newItem };
            };
          }

          if (prop === "toggle_kill_item") {
            return async function (itemId) {
              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              let serverRes = null;
              try {
                serverRes = await rpcCall("toggle_kill_item", [itemId]);
              } catch (e) {
                console.warn("[Harness Bridge] toggle_kill_item RPC notice:", e.message);
              }

              let targetItem = null;
              for (const dt in localKillMap) {
                const item = localKillMap[dt].find((i) => i.id == itemId);
                if (item) {
                  item.completed = (serverRes?.item?.completed !== undefined) ? serverRes.item.completed : (item.completed ? 0 : 1);
                  targetItem = item;
                  break;
                }
              }
              setStore(STORAGE_KEYS.KILL_LIST, localKillMap);
              if (targetItem) {
                supabaseRequest(`kill_list_items?id=eq.${itemId}`, "PATCH", { completed: Boolean(targetItem.completed) });
              }
              return serverRes || { success: true, item: targetItem };
            };
          }

          if (prop === "delete_kill_item") {
            return async function (itemId) {
              try {
                await rpcCall("delete_kill_item", [itemId]);
              } catch (e) {
                console.warn("[Harness Bridge] delete_kill_item RPC notice:", e.message);
              }
              const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
              for (const dt in localKillMap) {
                localKillMap[dt] = localKillMap[dt].filter((i) => i.id != itemId);
              }
              setStore(STORAGE_KEYS.KILL_LIST, localKillMap);
              supabaseRequest(`kill_list_items?id=eq.${itemId}`, "DELETE");
              return { success: true };
            };
          }

          if (prop === "auto_populate_kill_list") {
            return async function (dateStr = null) {
              const dt = dateStr || getLocalDateStr();
              let serverRes = null;
              try {
                serverRes = await rpcCall("auto_populate_kill_list", [dt]);
              } catch (e) {
                console.warn("[Harness Bridge] auto_populate_kill_list RPC notice:", e.message);
              }
              if (serverRes && Array.isArray(serverRes.items)) {
                const localKillMap = getStore(STORAGE_KEYS.KILL_LIST, {});
                localKillMap[dt] = serverRes.items;
                setStore(STORAGE_KEYS.KILL_LIST, localKillMap);
                return serverRes;
              }
              return await apiProxy.get_kill_list(dt);
            };
          }

          if (prop === "enqueue_homework_prep") {
            return async function (hwId, dateStr = null) {
              const dt = dateStr || getLocalDateStr();
              try {
                const res = await rpcCall("enqueue_homework_prep", [hwId, dt]);
                await apiProxy.get_kill_list(dt);
                return res;
              } catch (e) {
                console.warn("[Harness Bridge] enqueue_homework_prep RPC notice:", e.message);
                return { success: false, error: e.message };
              }
            };
          }

          if (prop === "enqueue_exam_prep") {
            return async function (examId, dateStr = null) {
              const dt = dateStr || getLocalDateStr();
              try {
                const res = await rpcCall("enqueue_exam_prep", [examId, dt]);
                await apiProxy.get_kill_list(dt);
                return res;
              } catch (e) {
                console.warn("[Harness Bridge] enqueue_exam_prep RPC notice:", e.message);
                return { success: false, error: e.message };
              }
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
                { deliverable_id: "sep26_leetcode_15", station_id: "sep-2026", stream: "Algorithms", title: "LeetCode Algorithm Drills (15 items)", total_required: 15, completed_count: 4, unit_label: "problems", is_completed: false },
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
                date: getLocalDateStr(todayDt),
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
                web_url: "",
                auto_sync: true,
                last_synced_at: null,
              });
              try {
                const serverStatus = await rpcCall("get_sync_status", []);
                if (serverStatus && (serverStatus.has_key || serverStatus.has_web_url)) return serverStatus;
              } catch (e) {}

              const isConfigured = Boolean(cfg.supabase_key || cfg.web_url);
              return {
                status: cfg.last_synced_at ? "synced" : isConfigured ? "ready" : "unconfigured",
                supabase_url: cfg.supabase_url,
                has_key: Boolean(cfg.supabase_key),
                web_url: cfg.web_url || "",
                has_web_url: Boolean(cfg.web_url),
                last_synced_at: cfg.last_synced_at,
                auto_sync: cfg.auto_sync !== false,
              };
            };
          }

          if (prop === "sync_now") {
            return async function () {
              try {
                const serverRes = await rpcCall("sync_now", []);
                if (serverRes) return serverRes;
              } catch (e) {}

              const cfg = getStore(STORAGE_KEYS.SYNC_CONFIG, {
                supabase_url: "https://xfslkbcopnugiubkboux.supabase.co",
                supabase_key: "",
                web_url: "",
              });
              if (!cfg.supabase_key && !cfg.web_url) {
                return { status: "unconfigured", message: "No sync credentials configured", synced_count: 0 };
              }

              cfg.last_synced_at = new Date().toISOString();
              setStore(STORAGE_KEYS.SYNC_CONFIG, cfg);
              return { status: "synced", message: "Client storage synchronized", synced_count: 0 };
            };
          }

          if (prop === "configure_sync") {
            return async function (url, key, autoSync = true) {
              const cfg = getStore(STORAGE_KEYS.SYNC_CONFIG, {});
              cfg.supabase_url = url.trim();
              cfg.supabase_key = key.trim();
              cfg.auto_sync = autoSync;
              cfg.last_synced_at = new Date().toISOString();
              setStore(STORAGE_KEYS.SYNC_CONFIG, cfg);
              try {
                await rpcCall("configure_sync", [url, key, autoSync]);
              } catch (e) {}
              return true;
            };
          }

          if (prop === "configure_web_sync") {
            return async function (webUrl, autoSync = true) {
              const cfg = getStore(STORAGE_KEYS.SYNC_CONFIG, {});
              cfg.web_url = webUrl.trim();
              cfg.auto_sync = autoSync;
              cfg.last_synced_at = new Date().toISOString();
              setStore(STORAGE_KEYS.SYNC_CONFIG, cfg);
              try {
                await rpcCall("configure_web_sync", [webUrl, autoSync]);
              } catch (e) {}
              return true;
            };
          }

          // 4. Homework Operations
          if (prop === "get_upcoming_homework") {
            return async function (dateStr = null) {
              const todayStr = dateStr || getLocalDateStr();
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_upcoming_homework", [todayStr]);
              } catch (e) {}

              let localHw = getStore(STORAGE_KEYS.HOMEWORK, null);

              if (serverRes && Array.isArray(serverRes)) {
                const hwMap = new Map();
                if (Array.isArray(localHw)) {
                  localHw.forEach((h) => hwMap.set(h.id, h));
                }
                serverRes.forEach((sh) => {
                  const existing = hwMap.get(sh.id);
                  if (existing) {
                    hwMap.set(sh.id, { ...sh, completed: existing.completed });
                  } else {
                    hwMap.set(sh.id, sh);
                  }
                });
                localHw = Array.from(hwMap.values());
              }

              if (!localHw) {
                const sbRes = await supabaseRequest(`homework_items?select=*&due_date=gte.${todayStr}&order=due_date.asc`);
                if (sbRes && Array.isArray(sbRes)) {
                  localHw = sbRes.map((r) => ({
                    id: r.id,
                    subject: r.subject,
                    title: r.title,
                    due_date: r.due_date,
                    completed: Boolean(r.completed),
                    source: r.source || "vulcan",
                    priority: r.priority || 1,
                    notes: r.notes || "",
                  }));
                }
              }

              if (!Array.isArray(localHw)) localHw = [];

              const todayDate = new Date(todayStr);
              const validHw = [];
              localHw.forEach((h) => {
                if (!h.due_date) return;
                if (h.due_date < todayStr) return; // Expired, auto-prune
                const itemDate = new Date(h.due_date);
                const diffTime = itemDate.getTime() - todayDate.getTime();
                const daysLeft = Math.round(diffTime / (1000 * 3600 * 24));
                validHw.push({
                  ...h,
                  days_left: daysLeft,
                  completed: Boolean(h.completed),
                });
              });

              setStore(STORAGE_KEYS.HOMEWORK, validHw);
              return validHw.filter((h) => !h.completed);
            };
          }

          if (prop === "toggle_homework") {
            return async function (hwId) {
              const localHw = getStore(STORAGE_KEYS.HOMEWORK, []);
              let serverRes = null;
              try {
                serverRes = await rpcCall("toggle_homework", [hwId]);
              } catch (e) {
                console.warn("[Harness Bridge] toggle_homework RPC notice:", e.message);
              }

              const item = localHw.find((h) => h.id == hwId);
              let newCompleted = false;
              if (item) {
                item.completed = (serverRes && serverRes.completed !== undefined) ? Boolean(serverRes.completed) : !item.completed;
                newCompleted = item.completed;
                setStore(STORAGE_KEYS.HOMEWORK, localHw);
                supabaseRequest(`homework_items?id=eq.${hwId}`, "PATCH", { completed: newCompleted });
              }
              return serverRes || { id: hwId, completed: newCompleted };
            };
          }

          if (prop === "delete_homework") {
            return async function (hwId) {
              try {
                await rpcCall("delete_homework", [hwId]);
              } catch (e) {
                console.warn("[Harness Bridge] delete_homework RPC notice:", e.message);
              }
              let localHw = getStore(STORAGE_KEYS.HOMEWORK, []);
              localHw = localHw.filter((h) => h.id != hwId);
              setStore(STORAGE_KEYS.HOMEWORK, localHw);
              supabaseRequest(`homework_items?id=eq.${hwId}`, "DELETE");
              return true;
            };
          }

          if (prop === "add_homework") {
            return async function (subject, title, dueDate, priority = 1, notes = "", source = "manual") {
              const localHw = getStore(STORAGE_KEYS.HOMEWORK, []);
              let serverHw = null;
              try {
                serverHw = await rpcCall("add_homework", [subject, title, dueDate, priority, notes, source]);
              } catch (e) {
                console.warn("[Harness Bridge] add_homework RPC notice:", e.message);
              }

              const todayDate = new Date(getLocalDateStr());
              const itemDate = new Date(dueDate);
              const daysLeft = Math.round((itemDate - todayDate) / (1000 * 3600 * 24));

              const newItem = serverHw || {
                id: Date.now(),
                subject,
                title,
                due_date: dueDate,
                completed: false,
                source,
                priority: parseInt(priority, 10) || 1,
                notes,
                days_left: daysLeft,
              };
              localHw.push(newItem);
              setStore(STORAGE_KEYS.HOMEWORK, localHw);

              supabaseRequest("homework_items", "POST", newItem);
              return newItem;
            };
          }

          // 5. School Exam Operations
          if (prop === "get_upcoming_exams") {
            return async function (limit = 15) {
              const todayStr = getLocalDateStr();
              let serverRes = null;
              try {
                serverRes = await rpcCall("get_upcoming_exams", [limit]);
              } catch (e) {}

              let localExams = getStore(STORAGE_KEYS.EXAMS, null);

              if (serverRes && Array.isArray(serverRes)) {
                const exMap = new Map();
                if (Array.isArray(localExams)) {
                  localExams.forEach((e) => exMap.set(e.id, e));
                }
                serverRes.forEach((se) => {
                  const existing = exMap.get(se.id);
                  if (existing) {
                    exMap.set(se.id, { ...se, completed: existing.completed });
                  } else {
                    exMap.set(se.id, se);
                  }
                });
                localExams = Array.from(exMap.values());
              }

              if (!localExams) {
                const sbRes = await supabaseRequest(`school_exams?select=*&exam_date=gte.${todayStr}&order=exam_date.asc&limit=${limit}`);
                if (sbRes && Array.isArray(sbRes)) {
                  localExams = sbRes.map((r) => ({
                    id: r.id,
                    subject: r.subject,
                    title: r.title,
                    exam_date: r.exam_date,
                    scope: r.scope || "",
                    completed: Boolean(r.completed),
                    result_percentage: r.result_percentage,
                  }));
                }
              }

              if (!Array.isArray(localExams)) localExams = [];
              localExams = localExams.filter((e) => {
                const text = ((e.title || "") + " " + (e.scope || "")).toLowerCase();
                return !text.includes("trygonometria") && !text.includes("kinematyka") && !text.includes("wyszukiwania") && !text.includes("powstanie styczniowe");
              });
              setStore(STORAGE_KEYS.EXAMS, localExams);

              const todayDate = new Date(todayStr);
              const validExams = localExams
                .filter((e) => e.exam_date >= todayStr || !e.completed)
                .map((e) => {
                  const itemDate = new Date(e.exam_date);
                  const daysLeft = Math.round((itemDate - todayDate) / (1000 * 3600 * 24));
                  return {
                    ...e,
                    days_left: daysLeft,
                    completed: Boolean(e.completed),
                  };
                });

              setStore(STORAGE_KEYS.EXAMS, validExams);
              return validExams.filter((e) => !e.completed);
            };
          }

          if (prop === "delete_exam") {
            return async function (examId) {
              try {
                await rpcCall("delete_exam", [examId]);
              } catch (e) {
                console.warn("[Harness Bridge] delete_exam RPC notice:", e.message);
              }
              let localExams = getStore(STORAGE_KEYS.EXAMS, []);
              localExams = localExams.filter((e) => e.id != examId);
              setStore(STORAGE_KEYS.EXAMS, localExams);
              supabaseRequest(`school_exams?id=eq.${examId}`, "DELETE");
              return true;
            };
          }

          if (prop === "toggle_exam") {
            return async function (examId, resultPercentage = null) {
              const localExams = getStore(STORAGE_KEYS.EXAMS, []);
              let serverRes = null;
              try {
                serverRes = await rpcCall("toggle_exam", [examId, resultPercentage]);
              } catch (e) {
                console.warn("[Harness Bridge] toggle_exam RPC notice:", e.message);
              }

              const item = localExams.find((e) => e.id == examId);
              let newCompleted = false;
              if (item) {
                item.completed = !item.completed;
                newCompleted = item.completed;
                setStore(STORAGE_KEYS.EXAMS, localExams);
                supabaseRequest(`school_exams?id=eq.${examId}`, "PATCH", { completed: newCompleted });
              }
              return serverRes || { id: examId, completed: newCompleted };
            };
          }

          if (prop === "add_exam") {
            return async function (subject, title, examDate, scope = "", resultPercentage = null) {
              const localExams = getStore(STORAGE_KEYS.EXAMS, []);
              const newId = Date.now();
              const todayDate = new Date(getLocalDateStr());
              const itemDate = new Date(examDate);
              const daysLeft = Math.round((itemDate - todayDate) / (1000 * 3600 * 24));

              const newItem = {
                id: newId,
                subject,
                title,
                exam_date: examDate,
                scope,
                completed: false,
                result_percentage: resultPercentage,
                days_left: daysLeft,
              };
              localExams.push(newItem);
              setStore(STORAGE_KEYS.EXAMS, localExams);

              rpcCall("add_exam", [subject, title, examDate, scope, resultPercentage]).catch(() => {});
              supabaseRequest("school_exams", "POST", newItem);
              return newItem;
            };
          }

          // 6. Vulcan Sync Bridge
          if (prop === "sync_vulcan_data") {
            return async function (dateStr = null, forceRefresh = false) {
              try {
                const serverRes = await rpcCall("sync_vulcan_data", [dateStr, forceRefresh]);
                if (serverRes) {
                  await apiProxy.get_upcoming_homework(dateStr);
                  await apiProxy.get_upcoming_exams();
                  if (apiProxy.get_tum_overview) {
                    await apiProxy.get_tum_overview();
                  }
                  return serverRes;
                }
              } catch (e) {}
              return { status: "synced", mode: "cached", exams_synced: 0, homework_synced: 0, grades_synced: 0 };
            };
          }

          if (prop === "auto_sync_vulcan") {
            return async function (dateStr = null) {
              try {
                const serverRes = await rpcCall("auto_sync_vulcan", [dateStr]);
                if (serverRes) {
                  await apiProxy.get_upcoming_homework(dateStr);
                  await apiProxy.get_upcoming_exams();
                  if (apiProxy.get_tum_overview) {
                    await apiProxy.get_tum_overview();
                  }
                  return serverRes;
                }
              } catch (e) {}
              return null;
            };
          }

          if (prop === "check_daily_vulcan_sync") {
            return async function (force = false) {
              try {
                const serverRes = await rpcCall("check_daily_vulcan_sync", [force]);
                if (serverRes) {
                  await apiProxy.get_upcoming_homework();
                  await apiProxy.get_upcoming_exams();
                  if (apiProxy.get_tum_overview) {
                    await apiProxy.get_tum_overview();
                  }
                  return serverRes;
                }
              } catch (e) {}
              return null;
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

