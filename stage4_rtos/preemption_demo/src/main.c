#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

#define HIGH_PRIORITY 2
#define LOW_PRIORITY  5

#define STACK_SIZE 1024

K_THREAD_STACK_DEFINE(high_stack, STACK_SIZE);
K_THREAD_STACK_DEFINE(low_stack, STACK_SIZE);
static struct k_thread high_thread_data;
static struct k_thread low_thread_data;

/* k_busy_wait() is Zephyr's own busy-wait primitive - unlike a manual
 * spin loop calling k_uptime_get(), this correctly integrates with
 * native_sim's virtual clock model (a manual spin loop never yields,
 * so native_sim's simulated time never advances and the loop hangs
 * forever - this was discovered the hard way during this task). */
void high_priority_task(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (1) {
        int64_t t = k_uptime_get();
        printk("[HIGH  prio=%d] running at t=%lld ms\n", HIGH_PRIORITY, t);
        k_busy_wait(50 * 1000);  /* 50ms of busy work, in microseconds */
        k_sleep(K_MSEC(500));    /* period: wake every 500ms */
    }
}

void low_priority_task(void *a, void *b, void *c)
{
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (1) {
        int64_t start = k_uptime_get();
        printk("[LOW   prio=%d] STARTING long task at t=%lld ms\n", LOW_PRIORITY, start);
        k_busy_wait(800 * 1000);  /* 800ms busy work - longer than HIGH's
                                   * period, so HIGH should preempt mid-loop */
        int64_t end = k_uptime_get();
        printk("[LOW   prio=%d] FINISHED long task at t=%lld ms (took %lld ms)\n",
               LOW_PRIORITY, end, end - start);
        k_sleep(K_MSEC(100));
    }
}

int main(void)
{
    printk("=== Preemption demo starting ===\n");

    k_thread_create(&high_thread_data, high_stack, STACK_SIZE,
                     high_priority_task, NULL, NULL, NULL,
                     HIGH_PRIORITY, 0, K_NO_WAIT);
    k_thread_name_set(&high_thread_data, "high_prio");

    k_thread_create(&low_thread_data, low_stack, STACK_SIZE,
                     low_priority_task, NULL, NULL, NULL,
                     LOW_PRIORITY, 0, K_NO_WAIT);
    k_thread_name_set(&low_thread_data, "low_prio");

    return 0;
}
