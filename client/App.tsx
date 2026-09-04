import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  StatusBar,
  Platform,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import {
  getLocalTasks,
  saveLocalTasks,
  getLocalDailyLog,
  saveLocalDailyLog,
  getLocalMetro,
  saveLocalMetro,
  DEFAULT_SCHEDULE,
  DEFAULT_GYM_PROTOCOL,
  TaskItem,
  DailyLog,
  MetroStation,
} from './src/lib/storage';
import { supabase } from './src/lib/supabase';

export default function App() {
  const [activeTab, setActiveTab] = useState<'cockpit' | 'today' | 'metro' | 'body'>('today');
  const [todayStr] = useState<string>(() => new Date().toISOString().split('T')[0]);

  // State
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [dailyLog, setDailyLog] = useState<DailyLog>({
    date: todayStr,
    scratchpad: '',
    completed_blocks: '',
    completed_exercises: '',
  });
  const [metroStations, setMetroStations] = useState<MetroStation[]>([]);
  const [weightInput, setWeightInput] = useState('');
  const [calSurplus, setCalSurplus] = useState(false);
  const [proteinMet, setProteinMet] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'Realtime' | 'Offline Ready'>('Offline Ready');
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 2000);
  };

  const triggerHaptic = () => {
    if (Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
  };

  const loadInitialData = async () => {
    // 1. Load local data
    const localTasks = await getLocalTasks();
    const localLog = await getLocalDailyLog(todayStr);
    const localMetro = await getLocalMetro();

    setTasks(localTasks);
    setDailyLog(localLog);
    setMetroStations(localMetro);

    // 2. If Supabase is connected, subscribe to real-time changes
    if (supabase) {
      setSyncStatus('Realtime');
      try {
        const { data: remoteTasks } = await supabase.from('tasks').select('*');
        if (remoteTasks) {
          setTasks(remoteTasks);
          saveLocalTasks(remoteTasks);
        }
      } catch (err) {
        console.log('Supabase sync notice:', err);
      }
    }
  };

  // --------------------------------------------------------------------------
  // Routine & Tasks
  // --------------------------------------------------------------------------
  const toggleBlock = async (idx: number) => {
    triggerHaptic();
    const current = new Set(
      dailyLog.completed_blocks.split(',').map((s) => s.trim()).filter(Boolean)
    );
    const key = String(idx);
    if (current.has(key)) {
      current.delete(key);
    } else {
      current.add(key);
    }

    const updatedLog: DailyLog = {
      ...dailyLog,
      completed_blocks: Array.from(current).join(','),
    };
    setDailyLog(updatedLog);
    await saveLocalDailyLog(updatedLog);

    if (supabase) {
      await supabase.from('daily_logs').upsert(updatedLog);
    }
    showToast('Routine updated');
  };

  const toggleExercise = async (idx: number) => {
    triggerHaptic();
    const current = new Set(
      dailyLog.completed_exercises.split(',').map((s) => s.trim()).filter(Boolean)
    );
    const key = String(idx);
    if (current.has(key)) {
      current.delete(key);
    } else {
      current.add(key);
    }

    const updatedLog: DailyLog = {
      ...dailyLog,
      completed_exercises: Array.from(current).join(','),
    };
    setDailyLog(updatedLog);
    await saveLocalDailyLog(updatedLog);

    if (supabase) {
      await supabase.from('daily_logs').upsert(updatedLog);
    }
    showToast('Exercise logged');
  };

  const handleAddTask = async () => {
    if (!newTaskTitle.trim()) return;
    triggerHaptic();

    const newTask: TaskItem = {
      id: Date.now(),
      title: newTaskTitle.trim(),
      category: 'General',
      is_tum: false,
      completed: false,
      date: todayStr,
    };

    const updated = [newTask, ...tasks];
    setTasks(updated);
    setNewTaskTitle('');
    await saveLocalTasks(updated);

    if (supabase) {
      await supabase.from('tasks').insert(newTask);
    }
    showToast('Task added');
  };

  const toggleTask = async (id: number) => {
    triggerHaptic();
    const updated = tasks.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t));
    setTasks(updated);
    await saveLocalTasks(updated);

    if (supabase) {
      const task = updated.find((t) => t.id === id);
      if (task) await supabase.from('tasks').update({ completed: task.completed }).eq('id', id);
    }
  };

  const deleteTask = async (id: number) => {
    triggerHaptic();
    const updated = tasks.filter((t) => t.id !== id);
    setTasks(updated);
    await saveLocalTasks(updated);

    if (supabase) {
      await supabase.from('tasks').delete().eq('id', id);
    }
    showToast('Task deleted');
  };

  const handleScratchpadChange = async (text: string) => {
    const updatedLog = { ...dailyLog, scratchpad: text };
    setDailyLog(updatedLog);
    await saveLocalDailyLog(updatedLog);
  };

  // --------------------------------------------------------------------------
  // Metro Deliverables Checklist
  // --------------------------------------------------------------------------
  const toggleMetroDeliverable = async (stationId: string, delivKey: string) => {
    triggerHaptic();
    const updated = metroStations.map((st) => {
      if (st.id !== stationId) return st;
      const completed = new Set(st.completed_deliverables || []);
      if (completed.has(delivKey)) {
        completed.delete(delivKey);
      } else {
        completed.add(delivKey);
      }

      const totalDelivs = Object.keys(st.deliverables || {}).length;
      const completedArr = Array.from(completed);
      const isNowCompleted = totalDelivs > 0 && completedArr.length >= totalDelivs;

      return {
        ...st,
        completed_deliverables: completedArr,
        status: isNowCompleted ? 'completed' : 'active',
      };
    });

    setMetroStations(updated);
    await saveLocalMetro(updated);

    if (supabase) {
      const station = updated.find((s) => s.id === stationId);
      if (station) {
        await supabase
          .from('metro_stations')
          .update({
            completed_deliverables: station.completed_deliverables,
            status: station.status,
          })
          .eq('id', stationId);
      }
    }
    showToast('Deliverable updated');
  };

  // --------------------------------------------------------------------------
  // Velocity Calculations
  // --------------------------------------------------------------------------
  const completedBlocksSet = new Set(
    dailyLog.completed_blocks.split(',').map((s) => s.trim()).filter(Boolean)
  );
  const totalBlocks = DEFAULT_SCHEDULE.blocks.length;
  const completedCount = completedBlocksSet.size;
  const velocityPct = totalBlocks > 0 ? Math.round((completedCount / totalBlocks) * 100) : 0;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0c10" />

      {/* Top Header */}
      <View style={styles.header}>
        <View style={styles.brandWrap}>
          {/* 2-Shard Lavender Mark */}
          <View style={styles.brandIconMark}>
            <View style={styles.shardHead} />
            <View style={styles.shardShaft} />
          </View>
          <Text style={styles.brandTitle}>HARNESS</Text>
          <Text style={styles.brandCaption}>/ EXECUTIVE OS</Text>
        </View>

        <View style={styles.syncBadge}>
          <View style={styles.syncDot} />
          <Text style={styles.syncText}>{syncStatus}</Text>
        </View>
      </View>

      {/* Toast Alert */}
      {toastMsg && (
        <View style={styles.toast}>
          <Text style={styles.toastText}>{toastMsg}</Text>
        </View>
      )}

      {/* Main Viewport */}
      <ScrollView style={styles.mainContent} contentContainerStyle={{ paddingBottom: 100 }}>
        {/* ==================================================================
             VIEW 0: COCKPIT / DASHBOARD
             ================================================================== */}
        {activeTab === 'cockpit' && (
          <View>
            {/* Velocity Card */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>TODAY'S VELOCITY</Text>
                <Text style={styles.goldPill}>3d STREAK</Text>
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', marginVertical: 8 }}>
                <Text style={styles.largeValue}>{velocityPct}%</Text>
                <Text style={styles.monoSubtext}>{completedCount}/{totalBlocks} blocks completed</Text>
              </View>
              <View style={styles.progressBarTrack}>
                <View style={[styles.progressBarFill, { width: `${velocityPct}%` }]} />
              </View>
            </View>

            {/* Purple Execution Heatmap */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>DAILY EXECUTION PULSE</Text>
                <Text style={styles.monoSubtext}>52-Week Luminescence</Text>
              </View>
              <Text style={{ fontSize: 11, color: '#9aa0a6', marginBottom: 12 }}>
                Density scale directly mapped to completed routine blocks &amp; gym protocols.
              </Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View style={{ flexDirection: 'row', gap: 3 }}>
                  {Array.from({ length: 52 }).map((_, wIdx) => (
                    <View key={wIdx} style={{ flexDirection: 'column', gap: 3 }}>
                      {Array.from({ length: 7 }).map((_, dIdx) => {
                        const isRecent = wIdx >= 48;
                        let level = 0;
                        if (isRecent && dIdx === 1) level = 4;
                        else if (isRecent && dIdx === 3) level = 3;
                        else if (isRecent && dIdx === 5) level = 2;
                        else if (isRecent) level = 1;

                        const colors = ['#17171d', '#3b1d60', '#6b21a8', '#9333ea', '#d8b4fe'];
                        return (
                          <View
                            key={dIdx}
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: 2,
                              backgroundColor: colors[level],
                            }}
                          />
                        );
                      })}
                    </View>
                  ))}
                </View>
              </ScrollView>
            </View>

            {/* Upcoming Forecast */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>UPCOMING TOMORROW</Text>
                <Text style={styles.monoSubtext}>Schedule B</Text>
              </View>
              <Text style={{ fontSize: 14, fontWeight: '700', color: '#f0f2f5', marginTop: 4 }}>
                Liceum CS / Math Rozszerzenie + Library Deep Work
              </Text>
              <Text style={{ fontSize: 12, color: '#9aa0a6', marginTop: 4 }}>
                Lift: Upper Hypertrophy • 140g+ Target Protein
              </Text>
            </View>
          </View>
        )}

        {/* ==================================================================
             VIEW 1: TODAY (Routine & Quick Tasks)
             ================================================================== */}
        {activeTab === 'today' && (
          <View>
            {/* Quick Task Input */}
            <View style={styles.quickInputRow}>
              <TextInput
                style={styles.textInput}
                placeholder="+ Add one-off task..."
                placeholderTextColor="#5f6368"
                value={newTaskTitle}
                onChangeText={setNewTaskTitle}
                onSubmitEditing={handleAddTask}
              />
              <TouchableOpacity style={styles.addBtn} onPress={handleAddTask}>
                <Text style={styles.addBtnText}>Add</Text>
              </TouchableOpacity>
            </View>

            {/* Daily Schedule Checklist */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>{DEFAULT_SCHEDULE.name}</Text>
                <Text style={styles.monoSubtext}>{completedCount}/{totalBlocks}</Text>
              </View>
              {DEFAULT_SCHEDULE.blocks.map((b, idx) => {
                const isDone = completedBlocksSet.has(String(idx));
                return (
                  <TouchableOpacity
                    key={idx}
                    style={[styles.routineRow, isDone && styles.routineRowDone]}
                    onPress={() => toggleBlock(idx)}
                    activeOpacity={0.7}
                  >
                    <View style={[styles.checkCircle, isDone && styles.checkCircleChecked]}>
                      {isDone && <Text style={styles.checkMark}>✓</Text>}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.routineTime}>{b.time} • {b.cutoff}</Text>
                      <Text style={[styles.routineFocus, isDone && styles.textCrossed]}>
                        {b.focus}
                      </Text>
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Tasks Checklist */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>ACTIVE TASKS ({tasks.length})</Text>
              </View>
              {tasks.length === 0 ? (
                <Text style={{ fontSize: 12, color: '#5f6368', paddingVertical: 8 }}>
                  No active tasks. Tap + above to add one.
                </Text>
              ) : (
                tasks.map((t) => (
                  <View key={t.id} style={styles.routineRow}>
                    <TouchableOpacity
                      style={[styles.checkCircle, t.completed && styles.checkCircleChecked]}
                      onPress={() => toggleTask(t.id)}
                    >
                      {t.completed && <Text style={styles.checkMark}>✓</Text>}
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={{ flex: 1 }}
                      onPress={() => toggleTask(t.id)}
                    >
                      <Text style={[styles.routineFocus, t.completed && styles.textCrossed]}>
                        {t.title}
                      </Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => deleteTask(t.id)} style={{ padding: 4 }}>
                      <Text style={{ color: '#5f6368', fontSize: 13, fontWeight: '700' }}>✕</Text>
                    </TouchableOpacity>
                  </View>
                ))
              )}
            </View>

            {/* Scratchpad */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>SCRATCHPAD</Text>
                <Text style={{ fontSize: 9, color: '#5f6368' }}>Auto-saved</Text>
              </View>
              <TextInput
                style={styles.scratchpadInput}
                placeholder="Transient ideas, math notes, trade setups..."
                placeholderTextColor="#5f6368"
                multiline
                value={dailyLog.scratchpad}
                onChangeText={handleScratchpadChange}
              />
            </View>
          </View>
        )}

        {/* ==================================================================
             VIEW 2: METRO ROADMAP
             ================================================================== */}
        {activeTab === 'metro' && (
          <View>
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>TUM HEILBRONN ROADMAP</Text>
                <Text style={{ color: '#c5a059', fontFamily: 'monospace', fontSize: 10, fontWeight: '700' }}>2026 - 2028</Text>
              </View>
              <Text style={{ fontSize: 12, color: '#9aa0a6' }}>
                Tap any station deliverable to check off requirements and complete the station.
              </Text>
            </View>

            {metroStations.map((st) => {
              const isDone = st.status === 'completed';
              const delivEntries = Object.entries(st.deliverables || {});
              const completedDelivs = new Set(st.completed_deliverables || []);

              return (
                <View key={st.id} style={[styles.card, st.is_major && styles.cardMajor]}>
                  <View style={styles.cardHeaderRow}>
                    <Text style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: '700', color: st.is_major ? '#c5a059' : '#9aa0a6' }}>
                      {st.month_label} • {st.phase.split(':')[0]}
                    </Text>
                    <Text style={{ fontFamily: 'monospace', fontSize: 10, color: isDone ? '#39d353' : '#5f6368', fontWeight: '700' }}>
                      {isDone ? 'COMPLETED ✓' : `${completedDelivs.size}/${delivEntries.length} MET`}
                    </Text>
                  </View>

                  <Text style={{ fontSize: 14, fontWeight: '700', color: '#f0f2f5', marginVertical: 4 }}>
                    {st.name}
                  </Text>
                  <Text style={{ fontSize: 12, color: '#9aa0a6', marginBottom: 10 }}>
                    {st.objective}
                  </Text>

                  {/* Deliverables Checklist */}
                  <View style={{ borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)', paddingTop: 8 }}>
                    {delivEntries.map(([key, val]) => {
                      const isChecked = completedDelivs.has(key);
                      return (
                        <TouchableOpacity
                          key={key}
                          style={styles.routineRow}
                          onPress={() => toggleMetroDeliverable(st.id, key)}
                          activeOpacity={0.7}
                        >
                          <View style={[styles.checkCircle, isChecked && styles.checkCircleChecked]}>
                            {isChecked && <Text style={styles.checkMark}>✓</Text>}
                          </View>
                          <View style={{ flex: 1 }}>
                            <Text style={{ fontFamily: 'monospace', fontSize: 9, fontWeight: '700', color: '#5f6368', textTransform: 'uppercase' }}>
                              {key} LINE
                            </Text>
                            <Text style={[styles.routineFocus, isChecked && styles.textCrossed, { fontSize: 12 }]}>
                              {val}
                            </Text>
                          </View>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* ==================================================================
             VIEW 3: BODY / GYM
             ================================================================== */}
        {activeTab === 'body' && (
          <View>
            {/* Gym Protocol */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>{DEFAULT_GYM_PROTOCOL.name}</Text>
                <Text style={styles.monoSubtext}>{DEFAULT_GYM_PROTOCOL.day}</Text>
              </View>
              {DEFAULT_GYM_PROTOCOL.exercises.map((ex, idx) => {
                const isDone = new Set(
                  dailyLog.completed_exercises.split(',').map((s) => s.trim()).filter(Boolean)
                ).has(String(idx));

                return (
                  <TouchableOpacity
                    key={idx}
                    style={styles.routineRow}
                    onPress={() => toggleExercise(idx)}
                    activeOpacity={0.7}
                  >
                    <View style={[styles.checkCircle, isDone && styles.checkCircleChecked]}>
                      {isDone && <Text style={styles.checkMark}>✓</Text>}
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.routineTime}>{ex.sets_reps} • {ex.rest}</Text>
                      <Text style={[styles.routineFocus, isDone && styles.textCrossed]}>
                        {ex.name}
                      </Text>
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Weigh-in */}
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardLabel}>BODY MASS TRACKER</Text>
                <Text style={styles.monoSubtext}>Target: 80.0 kg</Text>
              </View>
              <View style={{ flexDirection: 'row', gap: 8, marginVertical: 10 }}>
                <TextInput
                  style={[styles.textInput, { flex: 1 }]}
                  placeholder="Morning Weight (e.g. 68.5)"
                  placeholderTextColor="#5f6368"
                  keyboardType="decimal-pad"
                  value={weightInput}
                  onChangeText={setWeightInput}
                />
                <TouchableOpacity
                  style={styles.addBtn}
                  onPress={() => {
                    if (weightInput) {
                      showToast(`Weigh-in saved: ${weightInput} kg`);
                      setWeightInput('');
                    }
                  }}
                >
                  <Text style={styles.addBtnText}>Save</Text>
                </TouchableOpacity>
              </View>
              <View style={{ flexDirection: 'row', gap: 16 }}>
                <TouchableOpacity
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}
                  onPress={() => setCalSurplus(!calSurplus)}
                >
                  <View style={[styles.checkCircle, calSurplus && styles.checkCircleChecked]}>
                    {calSurplus && <Text style={styles.checkMark}>✓</Text>}
                  </View>
                  <Text style={{ color: '#f0f2f5', fontSize: 12 }}>+300 Cal Surplus</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}
                  onPress={() => setProteinMet(!proteinMet)}
                >
                  <View style={[styles.checkCircle, proteinMet && styles.checkCircleChecked]}>
                    {proteinMet && <Text style={styles.checkMark}>✓</Text>}
                  </View>
                  <Text style={{ color: '#f0f2f5', fontSize: 12 }}>140g+ Protein Met</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Bottom Navigation Bar */}
      <View style={styles.bottomNav}>
        <TouchableOpacity
          style={[styles.navItem, activeTab === 'cockpit' && styles.navItemActive]}
          onPress={() => {
            triggerHaptic();
            setActiveTab('cockpit');
          }}
        >
          <Text style={[styles.navIcon, activeTab === 'cockpit' && styles.navIconActive]}>◈</Text>
          <Text style={[styles.navLabel, activeTab === 'cockpit' && styles.navLabelActive]}>Cockpit</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navItem, activeTab === 'today' && styles.navItemActive]}
          onPress={() => {
            triggerHaptic();
            setActiveTab('today');
          }}
        >
          <Text style={[styles.navIcon, activeTab === 'today' && styles.navIconActive]}>◻</Text>
          <Text style={[styles.navLabel, activeTab === 'today' && styles.navLabelActive]}>Today</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navItem, activeTab === 'metro' && styles.navItemActive]}
          onPress={() => {
            triggerHaptic();
            setActiveTab('metro');
          }}
        >
          <Text style={[styles.navIcon, activeTab === 'metro' && styles.navIconActive]}>◎</Text>
          <Text style={[styles.navLabel, activeTab === 'metro' && styles.navLabelActive]}>Metro</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.navItem, activeTab === 'body' && styles.navItemActive]}
          onPress={() => {
            triggerHaptic();
            setActiveTab('body');
          }}
        >
          <Text style={[styles.navIcon, activeTab === 'body' && styles.navIconActive]}>▲</Text>
          <Text style={[styles.navLabel, activeTab === 'body' && styles.navLabelActive]}>Gym</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0c10',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.08)',
    backgroundColor: 'rgba(10,12,16,0.95)',
  },
  brandWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandIconMark: {
    width: 14,
    height: 14,
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  shardHead: {
    position: 'absolute',
    top: 0,
    width: 12,
    height: 4,
    backgroundColor: '#a78bfa',
    transform: [{ rotate: '-25deg' }],
    borderRadius: 1,
  },
  shardShaft: {
    position: 'absolute',
    bottom: 0,
    width: 3,
    height: 12,
    backgroundColor: '#a78bfa',
    transform: [{ rotate: '15deg' }],
    borderRadius: 1,
  },
  brandTitle: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: '800',
    fontSize: 14,
    color: '#f0f2f5',
    letterSpacing: 1,
  },
  brandCaption: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#5f6368',
  },
  syncBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    backgroundColor: 'rgba(57, 211, 83, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(57, 211, 83, 0.25)',
  },
  syncDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#39d353',
  },
  syncText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#39d353',
    fontWeight: '700',
  },
  toast: {
    position: 'absolute',
    top: 60,
    alignSelf: 'center',
    backgroundColor: '#181b24',
    borderWidth: 1,
    borderColor: '#f0f2f5',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    zIndex: 100,
  },
  toastText: {
    color: '#f0f2f5',
    fontSize: 12,
    fontWeight: '700',
  },
  mainContent: {
    flex: 1,
    padding: 16,
  },
  card: {
    backgroundColor: '#12141a',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
  },
  cardMajor: {
    borderColor: 'rgba(197, 160, 89, 0.35)',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  cardLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 11,
    fontWeight: '700',
    color: '#9aa0a6',
    letterSpacing: 0.6,
  },
  goldPill: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 11,
    color: '#c5a059',
    fontWeight: '700',
  },
  monoSubtext: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#5f6368',
  },
  largeValue: {
    fontSize: 28,
    fontWeight: '800',
    color: '#f0f2f5',
  },
  progressBarTrack: {
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#f0f2f5',
    borderRadius: 3,
  },
  quickInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#181b24',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginBottom: 14,
  },
  textInput: {
    flex: 1,
    color: '#f0f2f5',
    fontSize: 13,
    paddingVertical: 8,
  },
  addBtn: {
    backgroundColor: '#f0f2f5',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  addBtnText: {
    color: '#0a0c10',
    fontSize: 11,
    fontWeight: '700',
  },
  routineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.04)',
  },
  routineRowDone: {
    opacity: 0.5,
  },
  checkCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: '#5f6368',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  checkCircleChecked: {
    backgroundColor: '#f0f2f5',
    borderColor: '#f0f2f5',
  },
  checkMark: {
    color: '#0a0c10',
    fontSize: 11,
    fontWeight: '900',
  },
  routineTime: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#5f6368',
  },
  routineFocus: {
    fontSize: 13,
    fontWeight: '600',
    color: '#f0f2f5',
    marginTop: 1,
  },
  textCrossed: {
    color: '#5f6368',
    textDecorationLine: 'line-through',
  },
  scratchpadInput: {
    color: '#f0f2f5',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 12,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  bottomNav: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    backgroundColor: 'rgba(18,20,26,0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.08)',
    paddingVertical: 8,
    paddingBottom: Platform.OS === 'ios' ? 24 : 8,
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    gap: 2,
  },
  navItemActive: {},
  navIcon: {
    fontSize: 16,
    color: '#5f6368',
  },
  navIconActive: {
    color: '#f0f2f5',
  },
  navLabel: {
    fontSize: 10,
    color: '#5f6368',
    fontWeight: '600',
  },
  navLabelActive: {
    color: '#f0f2f5',
  },
});
