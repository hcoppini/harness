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
  TaskItem,
  DailyLog,
  MetroStation,
} from './src/lib/storage';
import { supabase } from './src/lib/supabase';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface SchoolObligation {
  id: string;
  type: 'exam' | 'homework';
  subject: string;
  topic: string;
  date: string;
  daysLeft: number;
}

export default function App() {
  // Navigation: 0 Cockpit, 1 Daily, 2 Study, 3 TUM '28
  const [activeTab, setActiveTab] = useState<'cockpit' | 'daily' | 'study' | 'tum'>('cockpit');
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
  const [syncStatus, setSyncStatus] = useState<'LIVE' | 'OFFLINE'>('OFFLINE');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [selectedHeatmapDay, setSelectedHeatmapDay] = useState<string | null>(null);

  // School Obligations (Vulcan / Local)
  const [obligations] = useState<SchoolObligation[]>([
    { id: 'ex-1', type: 'exam', subject: 'Matematyka R', topic: 'Rachunek różniczkowy i pochodne', date: '2026-09-24', daysLeft: 4 },
    { id: 'ex-2', type: 'exam', subject: 'Informatyka', topic: 'Struktury danych & algorytmy grafowe', date: '2026-10-02', daysLeft: 12 },
    { id: 'hw-1', type: 'homework', subject: 'Język Niemiecki', topic: 'Esej przygotowawczy B2 (Umwelt)', date: '2026-09-22', daysLeft: 2 },
  ]);

  useEffect(() => {
    loadInitialData();
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 2200);
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
      setSyncStatus('LIVE');
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
  // Routine & Tasks Handlers
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

  // Upcoming School Exams Count
  const upcomingExams = obligations.filter((o) => o.type === 'exam');
  const upcomingHW = obligations.filter((o) => o.type === 'homework');
  const nearestExam = upcomingExams.length > 0 ? upcomingExams[0] : null;

  // --------------------------------------------------------------------------
  // Forward Inverted Heatmap Generator (Sep 1 Onwards)
  // Logic: 100% completed day = Pitch Black (#000000).
  // Incomplete / future days = Brighter (#525252, #a3a3a3, #d4d4d4, #f5f5f5)
  // --------------------------------------------------------------------------
  const renderForwardInvertedHeatmap = () => {
    // Generate 16 forward weeks starting from Sep 1, 2026
    const startDate = new Date(2026, 8, 1); // 2026-09-01
    const weeksCount = 16;
    const weeks: { date: Date; dateStr: string; level: number; label: string }[][] = [];

    let curDate = new Date(startDate);
    // Align to Monday of that week
    const dayOfWeek = (curDate.getDay() + 6) % 7;
    curDate.setDate(curDate.getDate() - dayOfWeek);

    for (let w = 0; w < weeksCount; w++) {
      const weekDays = [];
      for (let d = 0; d < 7; d++) {
        const dStr = curDate.toISOString().split('T')[0];
        const isSepPast = curDate < new Date();
        const isToday = dStr === todayStr;

        // Inverted density calculation:
        // Level 4 (darkest black #000000): 100% done
        // Level 3 (#404040): 75% done
        // Level 2 (#737373): 50% done
        // Level 1 (#d4d4d4): 25% done
        // Level 0 (#f5f5f5): upcoming or unchecked
        let level = 0;
        let desc = 'Upcoming horizon day';

        if (isToday) {
          if (velocityPct >= 90) level = 4;
          else if (velocityPct >= 60) level = 3;
          else if (velocityPct >= 30) level = 2;
          else if (velocityPct > 0) level = 1;
          else level = 0;
          desc = `Today (${dStr}): ${velocityPct}% velocity (${completedCount}/${totalBlocks} blocks done)`;
        } else if (isSepPast) {
          // Simulated past Sep days
          const pseudo = (curDate.getDate() * 7 + w * 3) % 5;
          level = pseudo;
          desc = `${dStr}: ${level === 4 ? '100% done (Full execution)' : `${level * 25}% completed`}`;
        }

        weekDays.push({
          date: new Date(curDate),
          dateStr: dStr,
          level,
          label: desc,
        });

        curDate.setDate(curDate.getDate() + 1);
      }
      weeks.push(weekDays);
    }

    // Inverted colors: Super dark black for completed, brighter for unchecked
    const invertedShades = ['#f5f5f5', '#d4d4d4', '#737373', '#404040', '#000000'];

    return (
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View>
            <Text style={styles.cardSectionTitle}>Execution Horizon Pulse</Text>
            <Text style={styles.cardSectionSubtitle}>Forward inverted heatmap from Sep 1 onwards</Text>
          </View>
          <View style={styles.heatmapLegend}>
            <Text style={styles.legendText}>Incomplete</Text>
            <View style={[styles.legendBox, { backgroundColor: '#f5f5f5' }]} />
            <View style={[styles.legendBox, { backgroundColor: '#d4d4d4' }]} />
            <View style={[styles.legendBox, { backgroundColor: '#737373' }]} />
            <View style={[styles.legendBox, { backgroundColor: '#404040' }]} />
            <View style={[styles.legendBox, { backgroundColor: '#000000' }]} />
            <Text style={styles.legendText}>Done</Text>
          </View>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 14 }}>
          <View style={{ flexDirection: 'row', gap: 4, paddingBottom: 6 }}>
            {weeks.map((week, wIdx) => (
              <View key={wIdx} style={{ flexDirection: 'column', gap: 4 }}>
                {week.map((day, dIdx) => (
                  <TouchableOpacity
                    key={dIdx}
                    style={[
                      styles.heatCell,
                      { backgroundColor: invertedShades[day.level] },
                      day.level === 4 && styles.heatCellDone,
                      day.dateStr === todayStr && styles.heatCellToday,
                    ]}
                    onPress={() => {
                      triggerHaptic('light');
                      setSelectedHeatmapDay(day.label);
                    }}
                    activeOpacity={0.7}
                  />
                ))}
              </View>
            ))}
          </View>
        </ScrollView>

        {selectedHeatmapDay && (
          <View style={styles.dayInfoPill}>
            <Text style={styles.dayInfoText}>{selectedHeatmapDay}</Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />

      {/* Main Container */}
      <View style={styles.viewportContainer}>

        {/* ==================================================================
             TOP MINIMALIST MONOCHROME HEADER
             ================================================================== */}
        <View style={styles.header}>
          <View style={styles.brandRow}>
            {/* Minimalist Monochrome Mark */}
            <View style={styles.brandMark}>
              <View style={styles.brandMarkInner} />
            </View>
            <View>
              <Text style={styles.brandTitle}>HARNESS</Text>
              <Text style={styles.brandSubtitle}>
                {activeTab === 'cockpit' && '0 COCKPIT'}
                {activeTab === 'daily' && '1 DAILY'}
                {activeTab === 'study' && '2 STUDY'}
                {activeTab === 'tum' && "3 TUM '28"}
              </Text>
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
               LAYER 0: COCKPIT / LANDING PAGE
               ================================================================ */}
          {activeTab === 'cockpit' && (
            <View>
              {/* 3 Executive KPI Cards */}
              <View style={styles.cockpitGrid}>
                {/* Gauge 1: Today's Execution Velocity */}
                <TouchableOpacity
                  style={styles.gaugeCard}
                  onPress={() => setActiveTab('daily')}
                  activeOpacity={0.8}
                >
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>TODAY'S VELOCITY</Text>
                    <View style={styles.pillBlack}>
                      <Text style={styles.pillBlackText}>SCHEDULE A</Text>
                    </View>
                  </View>
                  <Text style={styles.gaugeValueBig}>{velocityPct}%</Text>
                  <View style={styles.progressTrack}>
                    <View style={[styles.progressFill, { width: `${velocityPct}%` }]} />
                  </View>
                  <Text style={styles.gaugeSubtext}>{completedCount}/{totalBlocks} blocks completed</Text>
                </TouchableOpacity>

                {/* Gauge 2: Academic Balance Status */}
                <TouchableOpacity
                  style={styles.gaugeCard}
                  onPress={() => setActiveTab('study')}
                  activeOpacity={0.8}
                >
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>ACADEMIC BALANCE</Text>
                    <View style={styles.pillOutline}>
                      <Text style={styles.pillOutlineText}>CRUISE</Text>
                    </View>
                  </View>
                  <View style={{ marginTop: 6 }}>
                    <Text style={styles.gaugeValueMedium}>
                      {nearestExam ? `${nearestExam.daysLeft}d: ${nearestExam.subject}` : 'Clean Horizon'}
                    </Text>
                    <Text style={styles.gaugeSubtext}>
                      {upcomingExams.length} Tests • {upcomingHW.length} Homework
                    </Text>
                  </View>
                  <Text style={[styles.gaugeSubtext, { marginTop: 10 }]} numberOfLines={1}>
                    Academic pressure calibrated. SGH blocks active.
                  </Text>
                </TouchableOpacity>

                {/* Gauge 3: TUM '28 Admissions Readiness */}
                <TouchableOpacity
                  style={styles.gaugeCard}
                  onPress={() => setActiveTab('tum')}
                  activeOpacity={0.8}
                >
                  <View style={styles.gaugeHeader}>
                    <Text style={styles.gaugeLabel}>TUM '28 READINESS</Text>
                    <View style={styles.pillBlack}>
                      <Text style={styles.pillBlackText}>GERMAN C1</Text>
                    </View>
                  </View>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 4 }}>
                    <Text style={styles.gaugeValueMedium}>GPA 4.85</Text>
                    <Text style={styles.gaugeValueMedium}>92% MOCK</Text>
                  </View>
                  <Text style={[styles.gaugeSubtext, { marginTop: 10 }]}>
                    Direct Admission Track (&gt;70 pts)
                  </Text>
                </TouchableOpacity>
              </View>

              {/* Forward Inverted Heatmap */}
              {renderForwardInvertedHeatmap()}

              {/* SGH / Matura Kill List Quick Horizon */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>Active Priority Horizon</Text>
                    <Text style={styles.cardSectionSubtitle}>Daily high-conviction deliverables</Text>
                  </View>
                  <TouchableOpacity onPress={() => setActiveTab('daily')}>
                    <Text style={styles.cardActionLink}>Open Daily &rarr;</Text>
                  </TouchableOpacity>
                </View>

                <View style={{ marginTop: 10, gap: 8 }}>
                  <View style={styles.horizonItem}>
                    <View style={styles.horizonBullet} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.horizonTitle}>Solve 3 CKE Math R Derivative Integrals</Text>
                      <Text style={styles.horizonMeta}>Math R • Class 3 Syllabus</Text>
                    </View>
                  </View>
                  <View style={styles.horizonItem}>
                    <View style={styles.horizonBullet} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.horizonTitle}>German C1 Mittelstufe Audio Drill (Goethe)</Text>
                      <Text style={styles.horizonMeta}>German C1 • 45 min deep immersion</Text>
                    </View>
                  </View>
                  <View style={styles.horizonItem}>
                    <View style={styles.horizonBullet} />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.horizonTitle}>Pure Syntax: LeetCode Graph Traversal</Text>
                      <Text style={styles.horizonMeta}>TUM Code • C++ Autonomous</Text>
                    </View>
                  </View>
                </View>
              </View>
            </View>
          )}

          {/* ================================================================
               LAYER 1: DAILY PLAN & VARYING STUDY BLOCKS
               ================================================================ */}
          {activeTab === 'daily' && (
            <View>
              {/* Daily Schedule Blocks */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>{DEFAULT_SCHEDULE.name}</Text>
                    <Text style={styles.cardSectionSubtitle}>Tap checkbox to toggle block completion</Text>
                  </View>
                  <View style={styles.pillBlack}>
                    <Text style={styles.pillBlackText}>ROUTINE</Text>
                  </View>
                </View>

                <View style={{ marginTop: 12, gap: 8 }}>
                  {DEFAULT_SCHEDULE.blocks.map((block, idx) => {
                    const isDone = completedBlocksSet.has(String(idx));
                    return (
                      <TouchableOpacity
                        key={idx}
                        style={[styles.routineRow, isDone && styles.routineRowDone]}
                        onPress={() => toggleBlock(idx)}
                        activeOpacity={0.7}
                      >
                        {/* Tactile Visible Checkbox */}
                        <View style={[styles.tactileBox, isDone && styles.tactileBoxChecked]}>
                          {isDone && <Text style={styles.tactileCheckmark}>✓</Text>}
                        </View>
                        <View style={{ flex: 1 }}>
                          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Text style={styles.routineTimePill}>{block.time}</Text>
                            <Text style={styles.routineCutoff}>{block.cutoff}</Text>
                          </View>
                          <Text style={[styles.routineName, isDone && styles.textCrossed]}>
                            {block.focus}
                          </Text>
                        </View>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </View>

              {/* Dynamic Tasks List */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>Today's Execution Tasks</Text>
                  <Text style={styles.monoSubLabel}>{tasks.filter((t) => t.completed).length}/{tasks.length} Done</Text>
                </View>

                {/* Add Task Input */}
                <View style={{ flexDirection: 'row', gap: 8, marginVertical: 12 }}>
                  <TextInput
                    style={[styles.taskInput, { flex: 1 }]}
                    placeholder="New action item..."
                    placeholderTextColor="#9ca3af"
                    value={newTaskTitle}
                    onChangeText={setNewTaskTitle}
                    onSubmitEditing={handleAddTask}
                  />
                  <TouchableOpacity style={styles.btnBlack} onPress={handleAddTask}>
                    <Text style={styles.btnBlackText}>Add</Text>
                  </TouchableOpacity>
                </View>

                {/* Tasks List */}
                <View style={{ gap: 8 }}>
                  {tasks.map((task) => (
                    <View key={task.id} style={[styles.taskRow, task.completed && styles.taskRowDone]}>
                      <TouchableOpacity
                        style={[styles.tactileBox, task.completed && styles.tactileBoxChecked]}
                        onPress={() => toggleTask(task.id)}
                        activeOpacity={0.7}
                      >
                        {task.completed && <Text style={styles.tactileCheckmark}>✓</Text>}
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={{ flex: 1 }}
                        onPress={() => toggleTask(task.id)}
                        activeOpacity={0.7}
                      >
                        <Text style={[styles.taskTitle, task.completed && styles.textCrossed]}>
                          {task.title}
                        </Text>
                        <Text style={styles.taskCategory}>{task.category}</Text>
                      </TouchableOpacity>
                      <TouchableOpacity onPress={() => deleteTask(task.id)} style={styles.btnDelete}>
                        <Text style={styles.btnDeleteText}>✕</Text>
                      </TouchableOpacity>
                    </View>
                  ))}
                  {tasks.length === 0 && (
                    <Text style={styles.emptyNotice}>No extra tasks added yet.</Text>
                  )}
                </View>
              </View>

              {/* Scratchpad Card */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>Daily Scratchpad</Text>
                  <Text style={styles.monoSubLabel}>Auto-persisted</Text>
                </View>
                <TextInput
                  style={styles.scratchpadInput}
                  multiline
                  placeholder="Capture quick reflections, ideas, or study observations..."
                  placeholderTextColor="#9ca3af"
                  value={dailyLog.scratchpad}
                  onChangeText={handleScratchpadChange}
                />
              </View>
            </View>
          )}

          {/* ================================================================
               LAYER 2: STUDY & ACADEMIC OBLIGATIONS
               ================================================================ */}
          {activeTab === 'study' && (
            <View>
              {/* Academic Horizon & School Tests */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>School Exams &amp; Obligations</Text>
                    <Text style={styles.cardSectionSubtitle}>Synchronized from Vulcan Ledger</Text>
                  </View>
                  <View style={styles.pillBlack}>
                    <Text style={styles.pillBlackText}>VULCAN LIVE</Text>
                  </View>
                </View>

                <View style={{ marginTop: 12, gap: 10 }}>
                  {obligations.map((item) => (
                    <View key={item.id} style={styles.obligationCard}>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                        <View style={item.type === 'exam' ? styles.pillBlack : styles.pillOutline}>
                          <Text style={item.type === 'exam' ? styles.pillBlackText : styles.pillOutlineText}>
                            {item.type.toUpperCase()}
                          </Text>
                        </View>
                        <Text style={styles.obligationDaysLeft}>
                          {item.daysLeft === 0 ? 'TODAY' : `${item.daysLeft} days left`}
                        </Text>
                      </View>
                      <Text style={styles.obligationSubject}>{item.subject}</Text>
                      <Text style={styles.obligationTopic}>{item.topic}</Text>
                      <Text style={styles.obligationDate}>Date: {item.date}</Text>
                    </View>
                  ))}
                </View>
              </View>

              {/* SGH / Matura Deep Work Protocol */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>United Study Protocol</Text>
                    <Text style={styles.cardSectionSubtitle}>SGH Library Afternoon Focus</Text>
                  </View>
                  <View style={styles.pillOutline}>
                    <Text style={styles.pillOutlineText}>MATURA ROZSZ.</Text>
                  </View>
                </View>

                <View style={{ marginTop: 12, gap: 8 }}>
                  <View style={styles.studyProtocolRow}>
                    <View style={styles.tactileBox}>
                      <Text style={styles.tactileCheckmark}>1</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.studyStepTitle}>Math R Diagnostic Problem Set</Text>
                      <Text style={styles.studyStepDesc}>Solve 5 CKE Arkusze tasks with full justification.</Text>
                    </View>
                  </View>

                  <View style={styles.studyProtocolRow}>
                    <View style={styles.tactileBox}>
                      <Text style={styles.tactileCheckmark}>2</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.studyStepTitle}>German C1 Audio &amp; Grammar Immersion</Text>
                      <Text style={styles.studyStepDesc}>Goethe-Zertifikat listening drills &amp; active recall.</Text>
                    </View>
                  </View>

                  <View style={styles.studyProtocolRow}>
                    <View style={styles.tactileBox}>
                      <Text style={styles.tactileCheckmark}>3</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.studyStepTitle}>Autonomous Code Construction</Text>
                      <Text style={styles.studyStepDesc}>Build and test algorithms without code generators.</Text>
                    </View>
                  </View>
                </View>
              </View>
            </View>
          )}

          {/* ================================================================
               LAYER 3: TUM '28 & METRO ROADMAP WITH EXAM DOTS
               ================================================================ */}
          {activeTab === 'tum' && (
            <View>
              {/* German C1 Pathway */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardSectionTitle}>German C1 Progression</Text>
                  <Text style={styles.monoSubLabel}>Active: B2.1</Text>
                </View>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 10 }}>
                  <View style={{ flexDirection: 'row', gap: 6 }}>
                    <View style={styles.ladderPillDone}><Text style={styles.ladderPillDoneText}>A1 ✓</Text></View>
                    <View style={styles.ladderPillDone}><Text style={styles.ladderPillDoneText}>A2 ✓</Text></View>
                    <View style={styles.ladderPillDone}><Text style={styles.ladderPillDoneText}>B1 ✓</Text></View>
                    <View style={styles.ladderPillActive}><Text style={styles.ladderPillActiveText}>B2.1 Active</Text></View>
                    <View style={styles.ladderPill}><Text style={styles.ladderPillText}>B2.2</Text></View>
                    <View style={styles.ladderPill}><Text style={styles.ladderPillText}>C1 Exam</Text></View>
                  </View>
                </ScrollView>
              </View>

              {/* Bavarian Aptitude Calculator Card */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>TUM Aptitude Simulator</Text>
                    <Text style={styles.cardSectionSubtitle}>Campus Heilbronn MDS Formula</Text>
                  </View>
                  <View style={styles.pillBlack}>
                    <Text style={styles.pillBlackText}>88.5 PTS SAFE</Text>
                  </View>
                </View>
                <View style={styles.scoreRow}>
                  <View style={styles.scoreCol}>
                    <Text style={styles.scoreLabel}>POLISH GPA</Text>
                    <Text style={styles.scoreValue}>5.50</Text>
                  </View>
                  <View style={styles.scoreCol}>
                    <Text style={styles.scoreLabel}>BAVARIAN</Text>
                    <Text style={styles.scoreValue}>1.25</Text>
                  </View>
                  <View style={styles.scoreCol}>
                    <Text style={styles.scoreLabel}>VERDICT</Text>
                    <Text style={styles.scoreValue}>DIRECT</Text>
                  </View>
                </View>
              </View>

              {/* Metro Stations with School Exam Dots */}
              <View style={styles.card}>
                <View style={styles.cardHeaderRow}>
                  <View>
                    <Text style={styles.cardSectionTitle}>TUM Metro Spine (2026 - 2028)</Text>
                    <Text style={styles.cardSectionSubtitle}>Checkpoints with school exam dots on rail</Text>
                  </View>
                  <View style={styles.pillBlack}>
                    <Text style={styles.pillBlackText}>ROADMAP</Text>
                  </View>
                </View>

                {/* Vertical Rail Spine with Exam Dots */}
                <View style={styles.metroVerticalWrapper}>
                  {/* Continuous Rail Line */}
                  <View style={styles.metroRailLine} />

                  {metroStations.map((st, sIdx) => {
                    const isDone = st.status === 'completed';
                    const delivEntries = Object.entries(st.deliverables || {});
                    const completedDelivs = new Set(st.completed_deliverables || []);

                    // Associated exam dot for the station month if active
                    const matchingExam = obligations.find((o) => o.type === 'exam' && sIdx === 0);

                    return (
                      <View key={st.id} style={styles.metroStationRow}>
                        {/* Interchange Node on Rail */}
                        <View style={[styles.metroRailNode, isDone && styles.metroRailNodeDone]}>
                          {isDone ? (
                            <Text style={styles.metroNodeCheck}>✓</Text>
                          ) : (
                            <View style={styles.metroNodeInnerDot} />
                          )}
                        </View>

                        {/* Station Card */}
                        <View style={[styles.metroCard, isDone && styles.metroCardDone]}>
                          <View style={styles.cardHeaderRow}>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                              <Text style={styles.stationMonthTag}>{st.month_label}</Text>
                              <Text style={styles.stationPhaseTag}>{st.phase.split(':')[0]}</Text>
                            </View>
                            <Text style={[styles.stationStatusBadge, isDone && { color: '#000000', fontWeight: '700' }]}>
                              {isDone ? 'COMPLETED ✓' : `${completedDelivs.size}/${delivEntries.length} MET`}
                            </Text>
                          </View>

                          <Text style={styles.stationName}>{st.name}</Text>
                          <Text style={styles.stationObjective}>{st.objective}</Text>

                          {/* School Test Dot Intercept on Metro Rail */}
                          {matchingExam && sIdx === 0 && (
                            <View style={styles.examDotBanner}>
                              <View style={styles.examDotIcon} />
                              <Text style={styles.examDotText}>
                                School Exam Milestone: {matchingExam.subject} ({matchingExam.date})
                              </Text>
                            </View>
                          )}

                          {/* Deliverables Checklist */}
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
                                  {/* Tactile Checkbox */}
                                  <View style={[styles.tactileBoxSmall, isChecked && styles.tactileBoxChecked]}>
                                    {isChecked && <Text style={styles.tactileCheckmarkSmall}>✓</Text>}
                                  </View>
                                  <View style={{ flex: 1 }}>
                                    <Text style={styles.streamBadgeText}>{streamKey.toUpperCase()} LINE</Text>
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
            </View>
          )}

        </ScrollView>

        {/* ==================================================================
             BOTTOM 4-TAB MONOCHROME NAVIGATION DOCK
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
            <Text style={[styles.navLabel, activeTab === 'cockpit' && styles.navLabelActive]}>0 Cockpit</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.navItem, activeTab === 'daily' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('daily');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'daily' && styles.navIconActive]}>◻</Text>
            <Text style={[styles.navLabel, activeTab === 'daily' && styles.navLabelActive]}>1 Daily</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.navItem, activeTab === 'study' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('study');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'study' && styles.navIconActive]}>▤</Text>
            <Text style={[styles.navLabel, activeTab === 'study' && styles.navLabelActive]}>2 Study</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.navItem, activeTab === 'tum' && styles.navItemActive]}
            onPress={() => {
              triggerHaptic('light');
              setActiveTab('tum');
            }}
          >
            <Text style={[styles.navIcon, activeTab === 'tum' && styles.navIconActive]}>◎</Text>
            <Text style={[styles.navLabel, activeTab === 'tum' && styles.navLabelActive]}>3 TUM '28</Text>
          </TouchableOpacity>
        </View>

      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#ffffff',
    alignItems: 'center',
  },
  viewportContainer: {
    flex: 1,
    width: '100%',
    maxWidth: 520,
    backgroundColor: '#fafafa',
  },

  /* Monochrome Minimal Header */
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
    backgroundColor: '#ffffff',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  brandMark: {
    width: 22,
    height: 22,
    borderRadius: 4,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  brandMarkInner: {
    width: 6,
    height: 6,
    borderRadius: 1,
    backgroundColor: '#ffffff',
  },
  brandTitle: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontWeight: '800',
    fontSize: 13,
    color: '#000000',
    letterSpacing: 1.5,
  },
  brandSubtitle: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#737373',
    letterSpacing: 0.8,
  },
  syncBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    backgroundColor: '#f5f5f5',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  syncDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#000000',
  },
  syncText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#000000',
    fontWeight: '700',
  },

  toast: {
    position: 'absolute',
    top: 60,
    alignSelf: 'center',
    backgroundColor: '#000000',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    zIndex: 100,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 8,
  },
  toastText: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '700',
  },

  contentScroll: {
    flex: 1,
    paddingHorizontal: 14,
    paddingTop: 14,
  },

  /* Cards */
  card: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
    elevation: 1,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  cardSectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#000000',
    letterSpacing: -0.2,
  },
  cardSectionSubtitle: {
    fontSize: 11,
    color: '#737373',
    marginTop: 2,
  },
  cardActionLink: {
    fontSize: 11,
    fontWeight: '600',
    color: '#000000',
  },

  /* Cockpit Grid */
  cockpitGrid: {
    gap: 10,
    marginBottom: 12,
  },
  gaugeCard: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 10,
    padding: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
    elevation: 1,
  },
  gaugeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  gaugeLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    fontWeight: '700',
    color: '#737373',
    letterSpacing: 0.6,
  },
  gaugeValueBig: {
    fontSize: 26,
    fontWeight: '800',
    color: '#000000',
    marginVertical: 4,
  },
  gaugeValueMedium: {
    fontSize: 17,
    fontWeight: '700',
    color: '#000000',
  },
  gaugeSubtext: {
    fontSize: 11,
    color: '#737373',
    marginTop: 4,
  },
  progressTrack: {
    height: 5,
    backgroundColor: '#e5e7eb',
    borderRadius: 3,
    overflow: 'hidden',
    marginVertical: 4,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#000000',
  },

  /* Monochrome Pills */
  pillBlack: {
    backgroundColor: '#000000',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  pillBlackText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: 0.5,
  },
  pillOutline: {
    borderWidth: 1,
    borderColor: '#000000',
    paddingHorizontal: 7,
    paddingVertical: 1,
    borderRadius: 10,
    backgroundColor: '#ffffff',
  },
  pillOutlineText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    fontWeight: '700',
    color: '#000000',
  },
  monoSubLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    color: '#737373',
  },

  /* Heatmap */
  heatmapLegend: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  legendText: {
    fontSize: 9,
    color: '#737373',
    marginHorizontal: 2,
  },
  legendBox: {
    width: 9,
    height: 9,
    borderRadius: 2,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  heatCell: {
    width: 14,
    height: 14,
    borderRadius: 2,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  heatCellDone: {
    borderColor: '#000000',
  },
  heatCellToday: {
    borderWidth: 1.5,
    borderColor: '#000000',
  },
  dayInfoPill: {
    marginTop: 10,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: '#f5f5f5',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  dayInfoText: {
    fontSize: 11,
    color: '#000000',
    fontWeight: '600',
  },

  /* Horizon List */
  horizonItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#f5f5f5',
  },
  horizonBullet: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#000000',
  },
  horizonTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#000000',
  },
  horizonMeta: {
    fontSize: 10,
    color: '#737373',
    marginTop: 1,
  },

  /* Tactile Checkboxes (Visible contrast) */
  tactileBox: {
    width: 22,
    height: 22,
    borderRadius: 4,
    borderWidth: 1.5,
    borderColor: '#000000',
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  tactileBoxChecked: {
    backgroundColor: '#000000',
  },
  tactileCheckmark: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 14,
  },
  tactileBoxSmall: {
    width: 18,
    height: 18,
    borderRadius: 3,
    borderWidth: 1.5,
    borderColor: '#000000',
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  tactileCheckmarkSmall: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '800',
    lineHeight: 12,
  },

  /* Routine & Daily Schedule */
  routineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 9,
    paddingHorizontal: 10,
    borderRadius: 8,
    backgroundColor: '#fafafa',
    borderWidth: 1,
    borderColor: '#f0f0f0',
  },
  routineRowDone: {
    backgroundColor: '#f5f5f5',
    opacity: 0.7,
  },
  routineTimePill: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    fontWeight: '700',
    color: '#000000',
  },
  routineCutoff: {
    fontSize: 10,
    color: '#737373',
  },
  routineName: {
    fontSize: 12,
    fontWeight: '600',
    color: '#000000',
    marginTop: 2,
  },
  textCrossed: {
    textDecorationLine: 'line-through',
    color: '#9ca3af',
  },

  /* Tasks */
  taskInput: {
    height: 38,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 6,
    paddingHorizontal: 12,
    fontSize: 12,
    color: '#000000',
  },
  btnBlack: {
    height: 38,
    backgroundColor: '#000000',
    paddingHorizontal: 14,
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnBlackText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '700',
  },
  taskRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  taskRowDone: {
    backgroundColor: '#fafafa',
    opacity: 0.6,
  },
  taskTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: '#000000',
  },
  taskCategory: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#737373',
    marginTop: 1,
  },
  btnDelete: {
    padding: 6,
  },
  btnDeleteText: {
    color: '#9ca3af',
    fontSize: 12,
  },
  emptyNotice: {
    fontSize: 12,
    color: '#9ca3af',
    textAlign: 'center',
    marginVertical: 8,
  },

  /* Scratchpad */
  scratchpadInput: {
    height: 90,
    backgroundColor: '#fafafa',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 6,
    padding: 10,
    fontSize: 12,
    color: '#000000',
    textAlignVertical: 'top',
    marginTop: 8,
  },

  /* Obligations & Study */
  obligationCard: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    gap: 4,
  },
  obligationDaysLeft: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    fontWeight: '700',
    color: '#000000',
  },
  obligationSubject: {
    fontSize: 14,
    fontWeight: '700',
    color: '#000000',
    marginTop: 2,
  },
  obligationTopic: {
    fontSize: 12,
    color: '#404040',
  },
  obligationDate: {
    fontSize: 10,
    color: '#737373',
    marginTop: 2,
  },
  studyProtocolRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderRadius: 6,
    backgroundColor: '#fafafa',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  studyStepTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#000000',
  },
  studyStepDesc: {
    fontSize: 11,
    color: '#737373',
    marginTop: 1,
  },

  /* German Ladder */
  ladderPill: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    backgroundColor: '#ffffff',
  },
  ladderPillText: {
    fontSize: 11,
    color: '#737373',
  },
  ladderPillDone: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#000000',
    backgroundColor: '#f5f5f5',
  },
  ladderPillDoneText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#000000',
  },
  ladderPillActive: {
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 12,
    backgroundColor: '#000000',
  },
  ladderPillActiveText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#ffffff',
  },

  /* Bavarian Simulator */
  scoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    marginTop: 6,
  },
  scoreCol: {
    alignItems: 'center',
  },
  scoreLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#737373',
  },
  scoreValue: {
    fontSize: 16,
    fontWeight: '800',
    color: '#000000',
    marginTop: 3,
  },

  /* Metro Vertical Roadmap with School Test Dots */
  metroVerticalWrapper: {
    position: 'relative',
    marginTop: 14,
    paddingLeft: 22,
  },
  metroRailLine: {
    position: 'absolute',
    left: 8,
    top: 10,
    bottom: 20,
    width: 2,
    backgroundColor: '#000000',
  },
  metroStationRow: {
    position: 'relative',
    marginBottom: 16,
  },
  metroRailNode: {
    position: 'absolute',
    left: -22,
    top: 14,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: '#ffffff',
    borderWidth: 2,
    borderColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 2,
  },
  metroRailNodeDone: {
    backgroundColor: '#000000',
  },
  metroNodeInnerDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#000000',
  },
  metroNodeCheck: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '800',
  },
  metroCard: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    padding: 12,
  },
  metroCardDone: {
    borderColor: '#d1d5db',
    backgroundColor: '#fafafa',
  },
  stationMonthTag: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    fontWeight: '800',
    color: '#000000',
  },
  stationPhaseTag: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    color: '#737373',
  },
  stationStatusBadge: {
    fontSize: 10,
    fontWeight: '600',
    color: '#737373',
  },
  stationName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#000000',
    marginTop: 4,
  },
  stationObjective: {
    fontSize: 11,
    color: '#6b7280',
    marginTop: 2,
    lineHeight: 15,
  },

  /* School Exam Dot on Rail */
  examDotBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
    paddingVertical: 5,
    paddingHorizontal: 8,
    borderRadius: 6,
    backgroundColor: '#f5f5f5',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  examDotIcon: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#000000',
  },
  examDotText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#000000',
  },

  /* Deliverables Ledger */
  deliverablesLedger: {
    marginTop: 10,
    gap: 6,
  },
  deliverableItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    paddingVertical: 6,
    paddingHorizontal: 8,
    borderRadius: 6,
    backgroundColor: '#fafafa',
    borderWidth: 1,
    borderColor: '#f0f0f0',
  },
  deliverableItemDone: {
    backgroundColor: '#f5f5f5',
    opacity: 0.65,
  },
  streamBadgeText: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 9,
    fontWeight: '700',
    color: '#000000',
  },
  deliverableText: {
    fontSize: 11,
    color: '#374151',
    marginTop: 1,
  },

  /* Bottom Navigation Dock (4 Tabs) */
  bottomNav: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    height: 60,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    backgroundColor: '#ffffff',
    paddingBottom: Platform.OS === 'ios' ? 4 : 0,
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 6,
  },
  navItemActive: {
    opacity: 1,
  },
  navIcon: {
    fontSize: 15,
    color: '#9ca3af',
  },
  navIconActive: {
    color: '#000000',
    fontWeight: '800',
  },
  navLabel: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    fontSize: 10,
    fontWeight: '500',
    color: '#9ca3af',
    marginTop: 2,
  },
  navLabelActive: {
    color: '#000000',
    fontWeight: '800',
  },
});
