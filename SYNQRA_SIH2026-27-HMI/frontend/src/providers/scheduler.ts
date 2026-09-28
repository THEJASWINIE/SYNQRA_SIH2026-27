/**
 * Scheduler abstraction — M3.
 *
 * The provider never calls `setTimeout` directly. Two reasons:
 *
 *   1. Determinism. Tests drive a manual scheduler and advance it step by step, so no
 *      test ever waits on real wall-clock time (mock-scenarios skill §Deterministic
 *      Playback).
 *   2. Teardown. Every handle is tracked in one place, so `disconnect()` can guarantee
 *      that no timer survives it.
 *
 * The native timer mechanism appears ONLY in `realScheduler` below.
 */

export type CancelHandle = () => void;

export interface Scheduler {
  /** Run `callback` after `delayMs`. Returns a cancel function. */
  schedule(delayMs: number, callback: () => void): CancelHandle;
  /** Cancel everything outstanding. Called on teardown. */
  cancelAll(): void;
}

/** Production scheduler. The only place a native timer is created. */
export function realScheduler(): Scheduler {
  const handles = new Set<ReturnType<typeof setTimeout>>();

  return {
    schedule(delayMs, callback) {
      const handle = setTimeout(() => {
        handles.delete(handle);
        callback();
      }, delayMs);
      handles.add(handle);
      return () => {
        clearTimeout(handle);
        handles.delete(handle);
      };
    },
    cancelAll() {
      for (const handle of handles) clearTimeout(handle);
      handles.clear();
    },
  };
}

interface PendingTask {
  id: number;
  dueAtMs: number;
  callback: () => void;
  cancelled: boolean;
}

export interface ManualScheduler extends Scheduler {
  /** Advance virtual time by `ms`, running everything that falls due, in order. */
  advance(ms: number): void;
  /** Run every outstanding task regardless of due time, in due order. */
  runAll(): void;
  /** Number of tasks still outstanding — used to prove teardown cancelled everything. */
  pendingCount(): number;
  /** Current virtual time, in milliseconds since scheduler creation. */
  nowMs(): number;
}

/**
 * Deterministic scheduler for tests.
 *
 * Virtual time only. Tasks due at the same instant run in scheduling order, so a scenario
 * replayed twice produces an identical emission sequence.
 */
export function manualScheduler(startMs = 0): ManualScheduler {
  let now = startMs;
  let nextId = 0;
  let tasks: PendingTask[] = [];

  function runDue(upToMs: number): void {
    // Re-read each pass: a callback may schedule further work.
    for (;;) {
      const due = tasks
        .filter((t) => !t.cancelled && t.dueAtMs <= upToMs)
        .sort((a, b) => a.dueAtMs - b.dueAtMs || a.id - b.id);
      const next = due[0];
      if (!next) break;
      next.cancelled = true;
      tasks = tasks.filter((t) => t !== next);
      now = Math.max(now, next.dueAtMs);
      next.callback();
    }
    now = Math.max(now, upToMs);
  }

  return {
    schedule(delayMs, callback) {
      const task: PendingTask = {
        id: nextId++,
        dueAtMs: now + delayMs,
        callback,
        cancelled: false,
      };
      tasks.push(task);
      return () => {
        task.cancelled = true;
        tasks = tasks.filter((t) => t !== task);
      };
    },
    cancelAll() {
      for (const task of tasks) task.cancelled = true;
      tasks = [];
    },
    advance(ms) {
      runDue(now + ms);
    },
    runAll() {
      const furthest = tasks.reduce((max, t) => Math.max(max, t.dueAtMs), now);
      runDue(furthest);
    },
    pendingCount() {
      return tasks.filter((t) => !t.cancelled).length;
    },
    nowMs() {
      return now;
    },
  };
}
