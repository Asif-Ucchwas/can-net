# Stage 5 Task 20: CAN vs UDP vs TCP Comparison

All measured with identical methodology: same load configs (1/5/15 concurrent
publishers x 10/100 Hz), same 20-trial count, same send-to-receive latency
measurement approach (perf_counter() timestamps).

| Publishers | Rate(Hz) | Transport | Drop% | Throughput(msg/s) | AvgLat(ms) | MaxLat(ms) |
|---|---|---|---|---|---|---|
| 1 | 10 | CAN | 0.00 | 10.4 | 0.2787 | 0.4214 |
| 1 | 10 | UDP | 0.00 | 10.0 | 0.1729 | 0.8136 |
| 1 | 10 | TCP | 0.00 | 10.2 | 0.1555 | 0.5403 |
| 1 | 100 | CAN | 0.00 | 100.4 | 0.2360 | 0.5936 |
| 1 | 100 | UDP | 0.00 | 100.1 | 0.1574 | 0.5566 |
| 1 | 100 | TCP | 0.00 | 100.1 | 0.1517 | 1.6585 |
| 5 | 10 | CAN | 0.00 | 51.6 | 0.2868 | 4.4982 |
| 5 | 10 | UDP | 0.05 | 52.1 | 0.1584 | 1.5321 |
| 5 | 10 | TCP | 0.00 | 52.1 | 0.1625 | 2.7838 |
| 5 | 100 | CAN | 0.00 | 501.8 | 0.2365 | 8.9374 |
| 5 | 100 | UDP | 0.00 | 502.1 | 0.1234 | 1.7183 |
| 5 | 100 | TCP | 0.00 | 502.2 | 0.1573 | 5.3643 |
| 15 | 10 | CAN | 0.03 | 156.6 | 0.4955 | 38.5356 |
| 15 | 10 | UDP | 0.00 | 157.1 | 0.1794 | 3.8973 |
| 15 | 10 | TCP | 0.00 | 157.3 | 0.4405 | 20.4519 |
| 15 | 100 | CAN | 0.89 | 1499.8 | 5.1675 | 284.3219 |
| 15 | 100 | UDP | 0.00 | 1507.1 | 0.2030 | 48.5925 |
| 15 | 100 | TCP | 0.00 | 1507.4 | 0.1561 | 17.8853 |
