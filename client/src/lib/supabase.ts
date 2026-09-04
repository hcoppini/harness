import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';

// Default Supabase config (Can be set via env or dynamically in Settings)
export const DEFAULT_SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || '';
export const DEFAULT_SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || '';

export let supabase: any = null;

export function initSupabase(url: string, key: string) {
  if (url && key) {
    supabase = createClient(url, key, {
      auth: {
        storage: AsyncStorage,
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
    });
  }
}

// Initialize on startup if env variables exist
if (DEFAULT_SUPABASE_URL && DEFAULT_SUPABASE_ANON_KEY) {
  initSupabase(DEFAULT_SUPABASE_URL, DEFAULT_SUPABASE_ANON_KEY);
}
