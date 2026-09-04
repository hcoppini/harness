import AsyncStorage from '@react-native-async-storage/async-storage';
import { supabase } from './supabase';

export interface TaskItem {
  id: number;
  title: string;
  category: string;
  is_tum: boolean;
  completed: boolean;
  date: string;
}

export interface DailyLog {
  date: string;
  scratchpad: string;
  completed_blocks: string; // Comma-separated indices
  completed_exercises: string;
}

export interface MetroStation {
  id: string;
  name: string;
  phase: string;
  month_label: string;
  year_month: string;
  is_major: boolean;
  status: string; // "active" | "completed" | "upcoming"
  objective: string;
  deliverables: Record<string, string>;
  completed_deliverables: string[];
}

export const DEFAULT_SCHEDULE = {
  name: "Class 3 Liceum + SGH Deep Work (Schedule A)",
  type: "A",
  blocks: [
    { time: "05:45 - 06:15", focus: "Morning Launch & Commute", cutoff: "05:45 Wake" },
    { time: "06:15 - 14:15", focus: "Class 3 Liceum (Maths / CS / English)", cutoff: "14:15 School End" },
    { time: "14:45 - 17:30", focus: "SGH Library: TUM Deep Work (Pure Code / German B1)", cutoff: "17:30 Strict Exit" },
    { time: "18:00 - 19:30", focus: "Boxing Training / Gym Lift", cutoff: "19:30 Workout Done" },
    { time: "19:45 - 20:30", focus: "High-Protein Nutrition & Shower", cutoff: "140g+ Protein" },
    { time: "20:30 - 21:15", focus: "Execution Audit & Tomorrow Prep", cutoff: "21:15 Screen Dim" },
    { time: "21:30", focus: "Lights Out / Deep Sleep (8h)", cutoff: "21:30 Bed" },
  ]
};

export const DEFAULT_GYM_PROTOCOL = {
  name: "Upper Hypertrophy & Density Protocol",
  day: "Tuesday / Thursday",
  focus: "Hypertrophy (Target: 80.0 kg)",
  exercises: [
    { name: "Incline Barbell Bench Press", sets_reps: "4 sets x 6-8 reps", rest: "2-3 min rest" },
    { name: "Weighted Pull-Ups / Lat Pulldown", sets_reps: "4 sets x 8-10 reps", rest: "2 min rest" },
    { name: "Overhead Dumbbell Shoulder Press", sets_reps: "3 sets x 8-10 reps", rest: "90s rest" },
    { name: "Chest-Supported Dumbbell Row", sets_reps: "3 sets x 10-12 reps", rest: "90s rest" },
    { name: "Dumbbell Lateral Raises (Heavy Partials)", sets_reps: "4 sets x 12-15 reps", rest: "60s rest" },
    { name: "Incline Dumbbell Bicep Curls", sets_reps: "3 sets x 10-12 reps", rest: "60s rest" },
    { name: "Overhead Rope Tricep Extensions", sets_reps: "3 sets x 12-15 reps", rest: "60s rest" },
  ]
};

export const DEFAULT_METRO_STATIONS: MetroStation[] = [
  {
    id: "sep-2026",
    name: "Pure Syntax & Liceum Launch",
    phase: "PHASE 1: THE ACCELERATION",
    month_label: "SEP 2026",
    year_month: "2026-09",
    is_major: true,
    status: "active",
    objective: "Establish 100% autonomous C++/Python syntax fluency and lock in GPA baseline.",
    deliverables: {
      "Academics": "Liceum 3rd year syllabus mastery; 100% on first math/CS tests.",
      "Code": "Implement LeetCode 75 Core DS/Algo from scratch without AI code completion.",
      "German": "Complete Goethe A2 grammar review; 50 new Anki cards daily.",
      "Physical": "Hit 70.0 kg baseline; log all 3 weekly boxing & 4 gym sessions."
    },
    completed_deliverables: []
  },
  {
    id: "oct-2026",
    name: "SIGG GPW Express Launch",
    phase: "PHASE 1: THE ACCELERATION",
    month_label: "OCT 2026",
    year_month: "2026-10",
    is_major: false,
    status: "upcoming",
    objective: "Deploy automated GPW scanner and enter Polish stock tournament.",
    deliverables: {
      "SIGG": "Deploy automated volume spike scanner on GPW Warsaw Exchange.",
      "Code": "Build robust backtesting engine for GPW intraday strategies.",
      "German": "Transition into B1 Mittelstufe listening & reading drills."
    },
    completed_deliverables: []
  },
  {
    id: "may-2027",
    name: "Class 3 Finals & German B1 Certified",
    phase: "PHASE 2: THE FORGE",
    month_label: "MAY 2027",
    year_month: "2027-05",
    is_major: true,
    status: "upcoming",
    objective: "Lock in Class 3 GPA > 4.5 and pass Goethe-Zertifikat B1 exam.",
    deliverables: {
      "Academics": "Final Year 3 report card: Maths (5/6), IT (5/6), English (6/6).",
      "German": "Pass official Goethe-Zertifikat B1 examination.",
      "Physical": "Reach 74.0 kg body mass at < 15% body fat."
    },
    completed_deliverables: []
  },
  {
    id: "may-2028",
    name: "The Matura Crucible",
    phase: "PHASE 4: THE THRESHOLD",
    month_label: "MAY 2028",
    year_month: "2028-05",
    is_major: true,
    status: "upcoming",
    objective: "Dominate Matura Rozszerzona: Maths > 90%, CS > 90%, Bilingual English > 95%.",
    deliverables: {
      "Matura Maths": "Score 90%+ on Matura Rozszerzona Matematyka.",
      "Matura CS": "Score 90%+ on Matura Rozszerzona Informatyka.",
      "Matura English": "Score 95%+ on Matura Dwujęzyczna Angielski."
    },
    completed_deliverables: []
  },
  {
    id: "jul-2028",
    name: "TUM Heilbronn Admission Gate",
    phase: "PHASE 5: THE SUMMIT",
    month_label: "JUL 2028",
    year_month: "2028-07",
    is_major: true,
    status: "upcoming",
    objective: "Direct Admission to B.Sc. Management and Data Science at TUM Campus Heilbronn.",
    deliverables: {
      "TUM Application": "Submit authenticated Matura credentials and German B2 certificate.",
      "Admissions Score": "Achieve direct admission threshold score (> 70 points).",
      "Arrival": "Move to Heilbronn, Germany."
    },
    completed_deliverables: []
  }
];

export async function getLocalTasks(): Promise<TaskItem[]> {
  try {
    const raw = await AsyncStorage.getItem('@harness_tasks');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function saveLocalTasks(tasks: TaskItem[]) {
  await AsyncStorage.setItem('@harness_tasks', JSON.stringify(tasks));
}

export async function getLocalDailyLog(dateStr: string): Promise<DailyLog> {
  try {
    const raw = await AsyncStorage.getItem(`@harness_log_${dateStr}`);
    return raw ? JSON.parse(raw) : { date: dateStr, scratchpad: '', completed_blocks: '', completed_exercises: '' };
  } catch {
    return { date: dateStr, scratchpad: '', completed_blocks: '', completed_exercises: '' };
  }
}

export async function saveLocalDailyLog(log: DailyLog) {
  await AsyncStorage.setItem(`@harness_log_${log.date}`, JSON.stringify(log));
}

export async function getLocalMetro(): Promise<MetroStation[]> {
  try {
    const raw = await AsyncStorage.getItem('@harness_metro');
    return raw ? JSON.parse(raw) : DEFAULT_METRO_STATIONS;
  } catch {
    return DEFAULT_METRO_STATIONS;
  }
}

export async function saveLocalMetro(stations: MetroStation[]) {
  await AsyncStorage.setItem('@harness_metro', JSON.stringify(stations));
}
