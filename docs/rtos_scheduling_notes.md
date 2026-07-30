# RTOS Scheduling Parameters — Zephyr (Stage 4 Notes)

## Thread Priorities
Zephyr uses **numeric priorities where lower = higher priority** for preemptible
threads (0 is highest). This is the opposite of some other RTOSes (FreeRTOS uses
higher-number = higher-priority), so it's worth double-checking per-RTOS.

In our preemption_demo (Task 15):
- `high_priority_task` = priority **2**
- `low_priority_task` = priority **5**

Zephyr also has a separate range for **cooperative** priorities (negative numbers),
which can only be preempted by an even-higher cooperative thread or an interrupt,
never by another preemptible thread. We used only positive (preemptible)
priorities here, since demonstrating preemption was the explicit goal.

## Stack Sizes
Every Zephyr thread needs a dedicated stack, sized via `K_THREAD_STACK_DEFINE`.
We used **1024 bytes** per thread (`high_stack`, `low_stack`) in preemption_demo,
and a separate **2048-byte** main stack (`CONFIG_MAIN_STACK_SIZE`) in prj.conf.

Sizing considerations:
- Too small -> stack overflow, one of the most common and hardest-to-diagnose
  embedded bugs (corrupts adjacent memory silently on real hardware; Zephyr's
  `CONFIG_THREAD_MONITOR`/stack-sentinel features can help catch this in dev).
- Too large -> wastes RAM, which matters a lot on real microcontrollers (often
  only tens of KB total) even though it's a non-issue on native_sim/QEMU.
- Our 1024B was generous for these simple demo tasks (just printk + busy-wait,
  minimal local variables) - a real embedded task doing more complex work
  (buffers, structs) would need this profiled/measured, not guessed.

## Tick Rate / Timing
Zephyr's kernel timing is driven by `CONFIG_SYS_CLOCK_TICKS_PER_SEC` (defaults
vary by board; native_sim uses a virtual clock model rather than a real
hardware timer - see the note below).

Key timing primitives used across Stage 4:
- `k_sleep(K_MSEC(n))` - voluntarily yields the CPU for n milliseconds; this is
  how our high_priority_task achieves its ~500ms period.
- `k_busy_wait(n)` (n in microseconds) - CPU-bound wait that does NOT yield the
  CPU to the scheduler. Correctly used for simulating real workload/computation
  time, as opposed to `k_sleep()` which represents idle/waiting time.
- `k_uptime_get()` - returns milliseconds since boot, used for all our
  timestamped logging.

**native_sim-specific gotcha (discovered in Task 15):** native_sim's simulated
time only advances at kernel scheduling events (a thread sleeping, blocking, or
otherwise yielding). A manual `while` loop that spins purely on `k_uptime_get()`
comparisons never yields, so the virtual clock never progresses and the loop
hangs forever - this doesn't happen on real hardware, where the clock is a real
independent peripheral ticking regardless of what the CPU is doing. The fix was
using Zephyr's own `k_busy_wait()`, which is aware of and correctly integrates
with native_sim's virtual-time model.

## What We Actually Verified (Task 15 Preemption Evidence)
With HIGH (priority 2, 500ms period) and LOW (priority 5, 800ms busy-wait per
cycle) running concurrently:
- LOW starts its 800ms busy-wait at t=50ms (would finish at t=850ms if
  uninterrupted).
- HIGH's log line appears at t=560ms - inside LOW's window - proving the
  scheduler suspended LOW mid-execution to run the higher-priority HIGH thread.
- LOW still finishes at exactly t=850ms (50+800), confirming it resumed
  correctly afterward rather than being corrupted, restarted, or losing its
  place.
- This pattern was consistent across dozens of cycles over a 37-second run,
  not a one-off coincidence.

## Interview-Ready Summary
"I configured a two-thread Zephyr application with explicit priority levels and
verified genuine preemptive scheduling by timestamping thread execution and
showing the high-priority thread interrupting a long-running low-priority
thread mid-execution, then confirming the low-priority thread resumed correctly
afterward with an unmodified total runtime. I also discovered and worked around
a native_sim-specific virtual-clock limitation where busy-wait loops must use
Zephyr's own `k_busy_wait()` primitive rather than manual polling, since the
simulator's time model only advances at kernel scheduling events."
