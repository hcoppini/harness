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
  Dimensions,
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

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const IS_DESKTOP = Platform.OS === 'web' && SCREEN_WIDTH > 768;

export default function App() {
  const [activeTab, setActiveTab] = useState<'cockpit' | 'today' | 'metro' | 'body'>('cockpit');
  const [todayStr] = useState<string>(() => new Date().toISOString().split('T')[0]);

  // Data State
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [taskCategory, setTaskCategory] = useState<'TUM' | 'CODE' | 'SIGG' | 'GENERAL'>('TUM');
  const [dailyLog, setDailyLog] = useState<DailyLog>({
    date: todayStr,
    scratchpad: '',
    completed_blocks: '',
    completed_exercises: '',
  });
  const [metroStations, setMetroStations] = useState<MetroStation[]>([]);
  const [weightInput, setWeightInput] = useState('');
  const [calSurplus, setCalSurplus] = useState(true);
  const [proteinMet, setProteinMet] = useState(true);
  const [syncStatus, setSyncStatus] = useState<'CONNECTED' | 'OFFLINE READY'>('OFFLINE READY');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [selectedDayInfo, setSelectedDayInfo] = useState<string | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 2000);
  };

  const triggerHaptic = (type: 'light' | 'medium' | 'success' = 'light') => {
    if (Platform.OS !== 'web') {
      if (type === 'success') Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      else if (type === 'medium') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      else Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
  };

  const loadInitialData = async () => {
    const localTasks = await getLocalTasks();
    const localLog = await getLocalDailyLog(todayStr);
    const localMetro = await getLocalMetro();

    setTasks(localTasks);
    setDailyLog(localLog);
    setMetroStations(localMetro);

    if (supabase) {
      setSyncStatus('CONNECTED');
      try {
        const { data: remoteTasks } = await supabase.from('tasks').select('*').order('id', { ascending: false });
        if (remoteTasks && remoteTasks.length > 0) {
          setTasks(remoteTasks);
          saveLocalTasks(remoteTasks);
        }

        const { data: remoteLog } = await supabase.from('daily_logs').select('*').eq('date', todayStr).single();
        if (remoteLog) {
          setDailyLog(remoteLog);
          saveLocalDailyLog(remoteLog);
        }

        const { data: remoteMetro } = await supabase.from('metro_stations').select('*').order('order_idx', { ascending: true });
        if (remoteMetro && remoteMetro.length > 0) {
          setMetroStations(remoteMetro);
          saveLocalMetro(remoteMetro);
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
    triggerHaptic('medium');
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
    showToast('Block updated');
  };

  const toggleExercise = async (idx: number) => {
    triggerHaptic('medium');
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
    triggerHaptic('success');

    const newTask: TaskItem = {
      id: Date.now(),
      title: newTaskTitle.trim(),
      category: taskCategory,
      is_tum: taskCategory === 'TUM',
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
    triggerHaptic('medium');
    const updated = tasks.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t));
    setTasks(updated);
    await saveLocalTasks(updated);

    if (supabase) {
      const task = updated.find((t) => t.id === id);
      if (task) await supabase.from('tasks').update({ completed: task.completed }).eq('id', id);
    }
  };

  const deleteTask = async (id: number) => {
    triggerHaptic('light');
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
    triggerHaptic('success');
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

    const activeSt = updated.find((s) => s.id === stationId);
    if (activeSt && activeSt.status === 'completed') {
      showToast(`Station Completed: ${activeSt.name}! ✓`);
    } else {
      showToast(`Updated ${delivKey}`);
    }

    if (supabase && activeSt) {
      await supabase
        .from('metro_stations')
        .update({
          completed_deliverables: activeSt.completed_deliverables,
          status: activeSt.status,
        })
        .eq('id', stationId);
    }
  };

  // --------------------------------------------------------------------------
  // Calculated Metrics
  // --------------------------------------------------------------------------
  const completedBlocksSet = new Set(
    dailyLog.completed_blocks.split(',').map((s) => s.trim()).filter(Boolean)
  );
  const totalBlocks = DEFAULT_SCHEDULE.blocks.length;
  const completedCount = completedBlocksSet.size;
  const velocityPct = totalBlocks > 0 ? Math.round((completedCount / totalBlocks) * 100) : 0;

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor="#08090c" />

      {/* Centered Device Wrapper for Desktop / Tablet */}
      <View style={styles.viewportContainer}>

        {/* ==================================================================
             TOP LUXURY HEADER
             ================================================================== */}
        <View style={styles.header}>
          <View style={styles.brandRow}>
            {/* 2-Shard Lavender Ice Pick Icon */}
            <View style={styles.icePickIconBox}>
              <View style={styles.shardBlade} />
              <View style={styles.shardHandle} />
            </View>
            <View>
              <Text style={styles.brandTitle}>HARNESS</Text>
              <Text style={styles.brandSubtitle}>EXECUTIVE OS</Text>
            </View>
          </View>

          {/* Sync Badge */}
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

        {/* ==================================================================
             MAIN SCROLLABLE VIEWPORT
             ================================================================== */}
        <ScrollView
          style={styles.contentScroll}
          contentContainerStyle={{ paddingBottom: 110 }}
          showsVerticalScrollIndicator={false}
        >

          {/* ================================================================
               LAYER 0: COCKPIT / DASHBOARD
               ================================================================ */}
          {activeTab === 'cockpit' && (
            <View>
              {/* Top 2x2 Executive Trajectory Grid */}
              <View style={styles.cockpitGrid}>
                {/* Gauge 1: Today's Execution Velocity */}
                <TouchableOpacity
                  style={styles.gaugeCard}
                  onPress={() => setActiveTab('today')}
                  activeOpacity={0.8}
                >
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>TODAY'S VELOCITY</Text>
                    <View style={styles.pillLavender}>
                      <Text style={styles.pillLavenderText}>SCHEDULE A</Text>
                    </View>
                  </View>
                  <Text style={styles.gaugeValueBig}>{velocityPct}%</Text>
                  <View style={styles.progressTrack}>
                    <View style={[styles.progressFill, { width: `${velocityPct}%` }]} />
                  </View>
                  <Text style={styles.gaugeSubtext}>{completedCount}/{totalBlocks} blocks done</Text>
                </TouchableOpacity>

                {/* Gauge 2: TUM Heilbronn Readiness */}
                <TouchableOpacity
                  style={styles.gaugeCard}
                  onPress={() => setActiveTab('metro')}
                  activeOpacity={0.8}
                >
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>TUM ADMISSIONS</Text>
                    <View style={styles.pillGold}>
                      <Text style={styles.pillGoldText}>GERMAN A2</Text>
                    </View>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 4 }}>
                    <Text style={styles.gaugeValueMedium}>GPA 4.85</Text>
                    <Text style={styles.gaugeValueMedium}>92% MOCK</Text>
                  </View>
                  <Text style={[styles.gaugeSubtext, { marginTop: 12 }]} numberOfLines={1}>
                    Active: Pure Syntax Launch
                  </Text>
                </TouchableOpacity>

                {/* Gauge 3: Body / Hypertrophy */}
                <TouchableOpacity
                  style={styles.gaugeCard}
                  onPress={() => setActiveTab('body')}
                  activeOpacity={0.8}
                >
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>PHYSIQUE &amp; MASS</Text>
                    <Text style={styles.monoSubLabel}>80.0 kg Goal</Text>
                  </View>
                  <Text style={styles.gaugeValueBig}>68.5 <Text style={{ fontSize: 13, color: '#9aa0a6' }}>kg</Text></Text>
                  <Text style={styles.gaugeSubtext}>Gym 4/4 • Boxing 3/3</Text>
                </TouchableOpacity>

                {/* Gauge 4: Active Sprint */}
                <View style={styles.gaugeCard}>
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>ACTIVE SPRINT</Text>
                    <View style={styles.pillLavender}>
                      <Text style={styles.pillLavenderText}>SIGG 24</Text>
                    </View>
                  </View>
                  <Text style={styles.gaugeValueMedium} numberOfLines={1}>GPW Scanner</Text>
                  <Text style={[styles.gaugeSubtext, { marginTop: 8 }]} numberOfLines={2}>
                    Next: Backtest intraday momentum spikes
                  </Text>
                </View>
              </View>

              {/* GitHub-Style Execution Heatmap Card */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>Daily Execution Pulse</Text>
                    <Text style={styles.cardSectionSubtitle}>Historical habit density: routines, gym, and tasks</Text>
                  </View>
                  <View style={styles.heatmapLegend}>
                    <Text style={styles.legendText}>Less</Text>
                    <View style={[styles.legendBox, { backgroundColor: '#161b22' }]} />
                    <View style={[styles.legendBox, { backgroundColor: '#0e4429' }]} />
                    <View style={[styles.legendBox, { backgroundColor: '#006d32' }]} />
                    <View style={[styles.legendBox, { backgroundColor: '#26a641' }]} />
                    <View style={[styles.legendBox, { backgroundColor: '#39d353' }]} />
                    <Text style={styles.legendText}>More</Text>
                  </View>
                </View>

                {/* Scrollable 52-Week Green Grid */}
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 12 }}>
                  <View style={{ flexDirection: 'row', gap: 3 }}>
                    {Array.from({ length: 28 }).map((_, wIdx) => (
                      <View key={wIdx} style={{ flexDirection: 'column', gap: 3 }}>
                        {Array.from({ length: 7 }).map((_, dIdx) => {
                          const isRecent = wIdx >= 24;
                          let level = 0;
                          if (isRecent && (dIdx === 1 || dIdx === 3)) level = 4;
                          else if (isRecent && dIdx === 5) level = 3;
                          else if (isRecent && dIdx === 2) level = 2;
                          else if (wIdx >= 20) level = 1;

                          const greenColors = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'];
                          return (
                            <TouchableOpacity
                              key={dIdx}
                              style={[
                                styles.heatCell,
                                { backgroundColor: greenColors[level] },
                                level === 4 && styles.heatCellGlow,
                              ]}
                              onPress={() => {
                                triggerHaptic('light');
                                setSelectedDayInfo(`Week ${wIdx + 1}, Day ${dIdx + 1}: ${level > 0 ? `${level * 2} blocks completed` : 'Rest day'}`);
                              }}
                              activeOpacity={0.7}
                            />
                          );
                        })}
                      </View>
                    ))}
                  </View>
                </ScrollView>
                {selectedDayInfo && (
                  <Text style={styles.dayInfoPill}>{selectedDayInfo}</Text>
                )}
              </View>

              {/* Tomorrow's Strategic Forecast Card */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>Upcoming Tomorrow</Text>
                  <View style={styles.pillLavender}>
                    <Text style={styles.pillLavenderText}>SCHEDULE A</Text>
                  </View>
                </View>
                <View style={styles.forecastBox}>
                  <Text style={styles.forecastTitle}>Liceum + SGH Library TUM Deep Work</Text>
                  <Text style={styles.forecastDetail}>
                    • 14:45 - 17:30: Pure C++/Python Syntax fluency &amp; German B1 Anki
                  </Text>
                  <Text style={styles.forecastDetail}>
                    • 18:00 - 19:30: Upper Hypertrophy Protocol • 140g+ Target Protein
                  </Text>
                </View>
              </View>
            </View>
          )}

          {/* ================================================================
               LAYER 1: TODAY (Routine Blocks & Tasks)
               ================================================================ */}
          {activeTab === 'today' && (
            <View>
              {/* Quick Task Creation Input */}
              <View style={styles.quickTaskBox}>
                <TextInput
                  style={styles.quickTaskInput}
                  placeholder="+ Add one-off task..."
                  placeholderTextColor="#5f6368"
                  value={newTaskTitle}
                  onChangeText={setNewTaskTitle}
                  onSubmitEditing={handleAddTask}
                />
                <View style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
                  <TouchableOpacity
                    style={[styles.catBadge, taskCategory === 'TUM' && styles.catBadgeActive]}
                    onPress={() => setTaskCategory('TUM')}
                  >
                    <Text style={[styles.catBadgeText, taskCategory === 'TUM' && styles.catBadgeTextActive]}>TUM</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.quickAddBtn}
                    onPress={handleAddTask}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.quickAddBtnText}>Add</Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* Daily Schedule Routine Blocks */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>{DEFAULT_SCHEDULE.name}</Text>
                    <Text style={styles.cardSectionSubtitle}>Strict time boxes &amp; exit cutoffs</Text>
                  </View>
                  <Text style={styles.routineCountText}>{completedCount}/{totalBlocks} Done</Text>
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
                      <View style={[styles.checkBtn, isDone && styles.checkBtnChecked]}>
                        {isDone && <Text style={styles.checkBtnIcon}>✓</Text>}
                      </View>
                      <View style={{ flex: 1 }}>
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                          <Text style={styles.routineTimePill}>{b.time}</Text>
                          <Text style={styles.routineCutoffTag}>{b.cutoff}</Text>
                        </View>
                        <Text style={[styles.routineName, isDone && styles.textCrossed]}>
                          {b.focus}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>

              {/* Active Tasks Checklist */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>Active Tasks ({tasks.length})</Text>
                </View>

                {tasks.length === 0 ? (
                  <Text style={styles.emptyNotice}>No active tasks. Tap + above to add one.</Text>
                ) : (
                  tasks.map((t) => (
                    <View key={t.id} style={styles.taskRow}>
                      <TouchableOpacity
                        style={[styles.checkBtn, t.completed && styles.checkBtnChecked]}
                        onPress={() => toggleTask(t.id)}
                      >
                        {t.completed && <Text style={styles.checkBtnIcon}>✓</Text>}
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={{ flex: 1 }}
                        onPress={() => toggleTask(t.id)}
                      >
                        <Text style={[styles.taskTitle, t.completed && styles.textCrossed]}>
                          {t.title}
                        </Text>
                        <Text style={styles.taskCategoryPill}>{t.category}</Text>
                      </TouchableOpacity>
                      <TouchableOpacity onPress={() => deleteTask(t.id)} style={{ padding: 6 }}>
                        <Text style={{ color: '#5f6368', fontSize: 13, fontWeight: '700' }}>✕</Text>
                      </TouchableOpacity>
                    </View>
                  ))
                )}
              </View>

              {/* Daily Scratchpad Buffer */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>Daily Scratchpad Buffer</Text>
                  <Text style={styles.monoSubLabel}>Auto-saved</Text>
                </View>
                <TextInput
                  style={styles.scratchpadArea}
                  placeholder="Transient thoughts, math equations, trade setups..."
                  placeholderTextColor="#5f6368"
                  multiline
                  value={dailyLog.scratchpad}
                  onChangeText={handleScratchpadChange}
                />
              </View>
            </View>
          )}

          {/* ================================================================
               LAYER 2: METRO ROADMAP (Vertical Railway Track)
               ================================================================ */}
          {activeTab === 'metro' && (
            <View>
              {/* Header Banner */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>TUM HEILBRONN METRO LINE</Text>
                    <Text style={styles.cardSectionSubtitle}>Vertical checkpoint spine (2026 - 2028)</Text>
                  </View>
                  <View style={styles.pillGold}>
                    <Text style={styles.pillGoldText}>ADMISSIONS</Text>
                  </View>
                </View>
                <Text style={{ fontSize: 12, color: '#9aa0a6', marginTop: 4 }}>
                  Tap any stream deliverable below to check off requirements. Stations auto-complete once all deliverables are met.
                </Text>
              </View>

              {/* Vertical Spine & Station Tree */}
              <View style={styles.metroVerticalWrapper}>
                {/* Continuous Vertical Rail Track */}
                <View style={styles.metroRailLine} />

                {metroStations.map((st, sIdx) => {
                  const isDone = st.status === 'completed';
                  const delivEntries = Object.entries(st.deliverables || {});
                  const completedDelivs = new Set(st.completed_deliverables || []);
                  const isLast = sIdx === metroStations.length - 1;

                  return (
                    <View key={st.id} style={styles.metroStationRow}>
                      {/* Metro Node Interchange Disc on the Vertical Rail */}
                      <View style={[styles.metroRailNode, isDone && styles.metroRailNodeDone, st.is_major && styles.metroRailNodeMajor]}>
                        {isDone ? (
                          <Text style={styles.metroNodeCheck}>✓</Text>
                        ) : (
                          <View style={styles.metroNodeInnerDot} />
                        )}
                      </View>

                      {/* Station Content Card */}
                      <View style={[styles.metroCard, isDone && styles.metroCardDone, st.is_major && styles.metroCardMajor]}>
                        <View style={styles.cardHeaderRow}>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                            <Text style={[styles.stationMonthTag, st.is_major && { color: '#c5a059' }]}>
                              {st.month_label}
                            </Text>
                            <Text style={styles.stationPhaseTag}>
                              {st.phase.split(':')[0]}
                            </Text>
                          </View>
                          <Text style={[styles.stationStatusBadge, isDone && { color: '#39d353' }]}>
                            {isDone ? 'COMPLETED ✓' : `${completedDelivs.size}/${delivEntries.length} MET`}
                          </Text>
                        </View>

                        <Text style={styles.stationName}>{st.name}</Text>
                        <Text style={styles.stationObjective}>{st.objective}</Text>

                        {/* Deliverables Checklist Box */}
                        <View style={styles.deliverablesLedger}>
                          {delivEntries.map(([streamKey, desc]) => {
                            const isChecked = completedDelivs.has(streamKey);
                            return (
                              <TouchableOpacity
                                key={streamKey}
                                style={[styles.deliverableItem, isChecked && styles.deliverableItemDone]}
                                onPress={() => toggleMetroDeliverable(st.id, streamKey)}
                                activeOpacity={0.7}
                              >
                                <View style={[styles.checkBtnSmall, isChecked && styles.checkBtnSmallChecked]}>
                                  {isChecked && <Text style={styles.checkBtnSmallIcon}>✓</Text>}
                                </View>
                                <View style={{ flex: 1 }}>
                                  <Text style={styles.streamBadgeText}>{streamKey} LINE</Text>
                                  <Text style={[styles.deliverableText, isChecked && styles.textCrossed]}>
                                    {desc}
                                  </Text>
                                </View>
                              </TouchableOpacity>
                            );
                          })}
                        </View>
                      </View>
                    </View>
                  );
                })}
              </View>
            </View>
          )}

          {/* ================================================================
               LAYER 3: GYM & PHYSIQUE
               ================================================================ */}
          {activeTab === 'body' && (
            <View>
              {/* Gym Protocol Routine */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>{DEFAULT_GYM_PROTOCOL.name}</Text>
                    <Text style={styles.cardSectionSubtitle}>{DEFAULT_GYM_PROTOCOL.day} • {DEFAULT_GYM_PROTOCOL.focus}</Text>
                  </View>
                  <View style={styles.pillLavender}>
                    <Text style={styles.pillLavenderText}>UPPER</Text>
                  </View>
                </View>

                {DEFAULT_GYM_PROTOCOL.exercises.map((ex, idx) => {
                  const isDone = new Set(
                    dailyLog.completed_exercises.split(',').map((s) => s.trim()).filter(Boolean)
                  ).has(String(idx));

                  return (
                    <TouchableOpacity
                      key={idx}
                      style={[styles.routineRow, isDone && styles.routineRowDone]}
                      onPress={() => toggleExercise(idx)}
                      activeOpacity={0.7}
                    >
                      <View style={[styles.checkBtn, isDone && styles.checkBtnChecked]}>
                        {isDone && <Text style={styles.checkBtnIcon}>✓</Text>}
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.routineTimePill}>{ex.sets_reps} • {ex.rest}</Text>
                        <Text style={[styles.routineName, isDone && styles.textCrossed]}>
                          {ex.name}
                        </Text>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>

              {/* Weigh-in Card */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>Body Mass &amp; Nutrition</Text>
                  <Text style={styles.monoSubLabel}>Goal: 80.0 kg</Text>
                </View>
                <View style={{ flexDirection: 'row', gap: 8, marginVertical: 10 }}>
                  <TextInput
                    style={[styles.quickTaskInput, { flex: 1 }]}
                    placeholder="Morning Weight (kg)"
                    placeholderTextColor="#5f6368"
                    keyboardType="decimal-pad"
                    value={weightInput}
                    onChangeText={setWeightInput}
                  />
                  <TouchableOpacity
                    style={styles.quickAddBtn}
                    onPress={() => {
                      if (weightInput) {
                        showToast(`Logged: ${weightInput} kg`);
                        setWeightInput('');
                      }
                    }}
                  >
                    <Text style={styles.quickAddBtnText}>Log</Text>
                  </TouchableOpacity>
                </View>
                <View style={{ flexDirection: 'row', gap: 16 }}>
                  <TouchableOpacity
                    style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}
                    onPress={() => setCalSurplus(!calSurplus)}
                  >
                    <View style={[styles.checkBtnSmall, calSurplus && styles.checkBtnSmallChecked]}>
                      {calSurplus && <Text style={styles.checkBtnSmallIcon}>✓</Text>}
                    </View>
                    <Text style={{ color: '#f0f2f5', fontSize: 12 }}>+300 Cal Surplus</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}
                    onPress={() => setProteinMet(!proteinMet)}
                  >
                    <View style={[styles.checkBtnSmall, proteinMet && styles.checkBtnSmallChecked]}>
                      {proteinMet && <Text style={styles.checkBtnSmallIcon}>✓</Text>}
                    </View>
                    <Text style={{ color: '#f0f2f5', fontSize: 12 }}>140g+ Protein Met</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          )}

        </ScrollView>

        {/* ==================================================================
             BOTTOM LUXURY NAVIGATION BAR
             ================================================================== */}
        <View style={styles.bottomNav}>
          <TouchableOpacity
            style={[styles.navItem, activeTab === 'cockpit' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('cockpit');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'cockpit' && styles.navIconActive]}>◈</Text>
            <Text style={[styles.navLabel, activeTab === 'cockpit' && styles.navLabelActive]}>Cockpit</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.navItem, activeTab === 'today' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('today');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'today' && styles.navIconActive]}>◻</Text>
            <Text style={[styles.navLabel, activeTab === 'today' && styles.navLabelActive]}>Today</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.navItem, activeTab === 'metro' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('metro');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'metro' && styles.navIconActive]}>◎</Text>
            <Text style={[styles.navLabel, activeTab === 'metro' && styles.navLabelActive]}>Metro</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.navItem, activeTab === 'body' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('body');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'body' && styles.navIconActive]}>▲</Text>
            <Text style={[styles.navLabel, activeTab === 'body' && styles.navLabelActive]}>Gym</Text>
          </TouchableOpacity>
        </View>

      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#08090c',
    alignItems: 'center', // Centers viewport on desktop
  },
  viewportContainer: {
    flex: 1,
    width: '100%',
    maxWidth: 520, // Strict mobile-oriented width constraint on desktop!
    backgroundColor: '#08090c',
    position: 'relative',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
    backgroundColor: 'rgba(8, 9, 12, 0.96)',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  icePickIconBox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
    shadowColor: '#a78bfa',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  shardBlade: {
    position: 'absolute',
    top: 4,
    width: 13,
    height: 3,
    backgroundColor: '#a78bfa',
    transform: [{ rotate: '-25deg' }],
    borderRadius: 1,
  },
  shardHandle: {
    position: 'absolute',
    bottom: 3,
    width: 3,
    height: 12,
    backgroundColor: '#a78bfa',
    transform: [{ rotate: '15deg' }],
    borderRadius: 1,
  },
  brandTitle: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: '800',
    fontSize: 13,
    color: '#f0f2f5',
    letterSpacing: 1.2,
  },
  brandSubtitle: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#5f6368',
    letterSpacing: 0.8,
  },
  syncBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    backgroundColor: 'rgba(57, 211, 83, 0.08)',
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
    fontSize: 9,
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
    shadowColor: '#000',
    shadowOpacity: 0.6,
    shadowRadius: 10,
  },
  toastText: {
    color: '#f0f2f5',
    fontSize: 11,
    fontWeight: '700',
  },
  contentScroll: {
    flex: 1,
    paddingHorizontal: 14,
    paddingTop: 14,
  },
  cockpitGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 12,
  },
  gaugeCard: {
    flex: 1,
    minWidth: '47%',
    backgroundColor: '#111319',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.07)',
    borderRadius: 8,
    padding: 12,
  },
  gaugeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  gaugeLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    fontWeight: '700',
    color: '#9aa0a6',
    letterSpacing: 0.5,
  },
  gaugeValueBig: {
    fontSize: 24,
    fontWeight: '800',
    color: '#f0f2f5',
    marginVertical: 2,
  },
  gaugeValueMedium: {
    fontSize: 14,
    fontWeight: '700',
    color: '#f0f2f5',
  },
  gaugeSubtext: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#5f6368',
    marginTop: 4,
  },
  progressTrack: {
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 2,
    overflow: 'hidden',
    marginVertical: 4,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#f0f2f5',
    borderRadius: 2,
  },
  pillLavender: {
    backgroundColor: 'rgba(167, 139, 250, 0.12)',
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(167, 139, 250, 0.3)',
  },
  pillLavenderText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    fontWeight: '700',
    color: '#c4b5fd',
  },
  pillGold: {
    backgroundColor: 'rgba(197, 160, 89, 0.12)',
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(197, 160, 89, 0.3)',
  },
  pillGoldText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    fontWeight: '700',
    color: '#c5a059',
  },
  monoSubLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#5f6368',
  },
  card: {
    backgroundColor: '#111319',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.07)',
    borderRadius: 8,
    padding: 14,
    marginBottom: 12,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardSectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#f0f2f5',
  },
  cardSectionSubtitle: {
    fontSize: 10,
    color: '#5f6368',
    marginTop: 2,
  },
  heatmapLegend: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  legendText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    color: '#5f6368',
  },
  legendBox: {
    width: 7,
    height: 7,
    borderRadius: 1.5,
  },
  heatCell: {
    width: 10,
    height: 10,
    borderRadius: 2,
  },
  heatCellGlow: {
    shadowColor: '#39d353',
    shadowOpacity: 0.6,
    shadowRadius: 4,
  },
  dayInfoPill: {
    marginTop: 8,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#c4b5fd',
    textAlign: 'center',
  },
  forecastBox: {
    marginTop: 4,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.05)',
    paddingTop: 8,
  },
  forecastTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#f0f2f5',
    marginBottom: 4,
  },
  forecastDetail: {
    fontSize: 11,
    color: '#9aa0a6',
    lineHeight: 18,
  },
  quickTaskBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#181b24',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 3,
    marginBottom: 12,
  },
  quickTaskInput: {
    flex: 1,
    color: '#f0f2f5',
    fontSize: 12,
    paddingVertical: 6,
  },
  catBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 3,
  },
  catBadgeActive: {
    backgroundColor: 'rgba(167, 139, 250, 0.2)',
  },
  catBadgeText: {
    fontSize: 9,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    color: '#5f6368',
    fontWeight: '700',
  },
  catBadgeTextActive: {
    color: '#c4b5fd',
  },
  quickAddBtn: {
    backgroundColor: '#f0f2f5',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 4,
  },
  quickAddBtnText: {
    color: '#08090c',
    fontSize: 10,
    fontWeight: '800',
  },
  routineCountText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#5f6368',
    fontWeight: '700',
  },
  routineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.04)',
  },
  routineRowDone: {
    opacity: 0.45,
  },
  checkBtn: {
    width: 18,
    height: 18,
    borderRadius: 4,
    borderWidth: 1.5,
    borderColor: '#5f6368',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  checkBtnChecked: {
    backgroundColor: '#f0f2f5',
    borderColor: '#f0f2f5',
  },
  checkBtnIcon: {
    color: '#08090c',
    fontSize: 10,
    fontWeight: '900',
  },
  checkBtnSmall: {
    width: 16,
    height: 16,
    borderRadius: 3,
    borderWidth: 1.5,
    borderColor: '#5f6368',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  checkBtnSmallChecked: {
    backgroundColor: '#f0f2f5',
    borderColor: '#f0f2f5',
  },
  checkBtnSmallIcon: {
    color: '#08090c',
    fontSize: 9,
    fontWeight: '900',
  },
  routineTimePill: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#5f6368',
    fontWeight: '600',
  },
  routineCutoffTag: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    color: '#c4b5fd',
    backgroundColor: 'rgba(167, 139, 250, 0.1)',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 2,
  },
  routineName: {
    fontSize: 12,
    fontWeight: '600',
    color: '#f0f2f5',
    marginTop: 2,
  },
  taskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 7,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.04)',
  },
  taskTitle: {
    fontSize: 12,
    fontWeight: '500',
    color: '#f0f2f5',
  },
  taskCategoryPill: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    color: '#5f6368',
    marginTop: 2,
  },
  textCrossed: {
    color: '#5f6368',
    textDecorationLine: 'line-through',
  },
  emptyNotice: {
    fontSize: 11,
    color: '#5f6368',
    paddingVertical: 8,
  },
  scratchpadArea: {
    color: '#f0f2f5',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 11,
    minHeight: 70,
    textAlignVertical: 'top',
    paddingTop: 4,
  },
  metroVerticalWrapper: {
    position: 'relative',
    paddingLeft: 18,
  },
  metroRailLine: {
    position: 'absolute',
    left: 8,
    top: 14,
    bottom: 20,
    width: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  metroStationRow: {
    position: 'relative',
    marginBottom: 14,
  },
  metroRailNode: {
    position: 'absolute',
    left: -18,
    top: 14,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: '#08090c',
    borderWidth: 2,
    borderColor: '#5f6368',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  metroRailNodeDone: {
    backgroundColor: '#f0f2f5',
    borderColor: '#f0f2f5',
    shadowColor: '#ffffff',
    shadowOpacity: 0.6,
    shadowRadius: 6,
  },
  metroRailNodeMajor: {
    borderColor: '#c5a059',
  },
  metroNodeInnerDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#5f6368',
  },
  metroNodeCheck: {
    fontSize: 9,
    fontWeight: '900',
    color: '#08090c',
  },
  metroCard: {
    backgroundColor: '#111319',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.07)',
    borderRadius: 8,
    padding: 12,
  },
  metroCardDone: {
    borderColor: 'rgba(57, 211, 83, 0.25)',
  },
  metroCardMajor: {
    borderColor: 'rgba(197, 160, 89, 0.35)',
  },
  stationMonthTag: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    fontWeight: '800',
    color: '#f0f2f5',
  },
  stationPhaseTag: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    color: '#5f6368',
  },
  stationStatusBadge: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#5f6368',
    fontWeight: '700',
  },
  stationName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#f0f2f5',
    marginTop: 4,
  },
  stationObjective: {
    fontSize: 11,
    color: '#9aa0a6',
    marginTop: 2,
    marginBottom: 8,
    lineHeight: 16,
  },
  deliverablesLedger: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.05)',
    paddingTop: 6,
  },
  deliverableItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 5,
  },
  deliverableItemDone: {
    opacity: 0.5,
  },
  streamBadgeText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 8,
    fontWeight: '700',
    color: '#5f6368',
    letterSpacing: 0.5,
  },
  deliverableText: {
    fontSize: 11,
    color: '#f0f2f5',
    lineHeight: 15,
  },
  bottomNav: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    backgroundColor: 'rgba(10, 12, 16, 0.98)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
    paddingVertical: 8,
    paddingBottom: Platform.OS === 'ios' ? 22 : 8,
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    gap: 2,
  },
  navItemActive: {},
  navIcon: {
    fontSize: 15,
    color: '#5f6368',
  },
  navIconActive: {
    color: '#f0f2f5',
  },
  navLabel: {
    fontSize: 9,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    color: '#5f6368',
    fontWeight: '600',
  },
  navLabelActive: {
    color: '#f0f2f5',
  },
});
