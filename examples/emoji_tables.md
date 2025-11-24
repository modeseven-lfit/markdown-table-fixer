<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Emoji Table Examples

This document contains examples of markdown tables with various emoji
characters to test proper width calculation and formatting.

## Common Status Indicators

| Feature        | Status | Priority | Notes                |
| -------------- | ------ | -------- | -------------------- |
| Authentication | ✅      | High     | Completed            |
| Authorization  | ❌      | High     | Not started          |
| Database       | ☑️     | Medium   | In progress          |
| API Gateway    | ⚠️     | High     | Needs review         |
| Unit Tests     | ✓      | Medium   | Partial coverage     |
| E2E Tests      | ✗      | Low      | Blocked by API       |
| Documentation  | 📝      | Medium   | Draft complete       |
| Deployment     | 🚀      | High     | Ready for production |

## Bug Tracking

<!-- markdownlint-disable MD013 -->

| ID   | Severity   | Status      | Description                    | Assignee  |
| ---- | ---------- | ----------- | ------------------------------ | --------- |
| #101 | 🔴 Critical | ❌ Open      | Database connection timeout    | 👤 Alice   |
| #102 | 🟡 Medium   | ☑️ Progress | UI rendering issue on mobile   | 👤 Bob     |
| #103 | 🟢 Low      | ✅ Fixed     | Typo in documentation          | 👤 Charlie |
| #104 | 🔴 Critical | ⚠️ Review   | Security vulnerability in auth | 👤 David   |
| #105 | 🟡 Medium   | ❌ Open      | Performance degradation        | 👤 Eve     |
| #106 | 🟢 Low      | ✅ Fixed     | Minor CSS alignment issue      | 👤 Frank   |

<!-- markdownlint-enable MD013 -->

## CI/CD Pipeline Status

| Stage       | Status    | Duration | Last Run         | Action  |
| ----------- | --------- | -------- | ---------------- | ------- |
| Lint        | ✅ Pass    | 2m 15s   | 2025-01-15 10:30 | 🔄 Retry |
| Build       | ✅ Pass    | 8m 42s   | 2025-01-15 10:32 | ▶️ Run  |
| Test        | ❌ Failed  | 15m 30s  | 2025-01-15 10:40 | 🔄 Retry |
| Security    | ⚠️ Warn   | 5m 10s   | 2025-01-15 10:55 | 👁️ View |
| Deploy Dev  | ⏸️ Paused | -        | -                | ▶️ Run  |
| Deploy Prod | 🚀 Ready   | -        | -                | 🛑 Stop  |

## Feature Flags

| Feature            | Enabled | Environment | Rollout | Impact   |
| ------------------ | ------- | ----------- | ------- | -------- |
| Dark Mode          | ✅       | Production  | 100%    | 🟢 Low    |
| New Dashboard      | ☑️      | Staging     | 50%     | 🟡 Medium |
| AI Suggestions     | ❌       | Dev         | 0%      | 🔴 High   |
| Real-time Updates  | ⚠️      | Beta        | 25%     | 🟡 Medium |
| Advanced Analytics | ✅       | Production  | 100%    | 🟢 Low    |
| Two-Factor Auth    | ✅       | Production  | 100%    | 🔴 High   |

## Performance Metrics

| Metric          | Value    | Target  | Status | Trend |
| --------------- | -------- | ------- | ------ | ----- |
| Response Time   | 120ms    | < 200ms | ✅      | ⬇️    |
| Error Rate      | 0.05%    | < 0.1%  | ✅      | ⬇️    |
| CPU Usage       | 65%      | < 80%   | ✅      | ➡️    |
| Memory Usage    | 85%      | < 90%   | ⚠️     | ⬆️    |
| Disk I/O        | 450 MB/s | < 1GB/s | ✅      | ➡️    |
| Network Latency | 45ms     | < 50ms  | ✅      | ⬇️    |

## Unicode and Special Characters

| Symbol | Name              | Category  | Width | Usage Example           |
| ------ | ----------------- | --------- | ----- | ----------------------- |
| ✅      | Check Mark        | Success   | 1     | Task completed          |
| ❌      | Cross Mark        | Error     | 1     | Operation failed        |
| ⚠️     | Warning Sign      | Alert     | 2     | Deprecated feature      |
| ☑️     | Ballot Box Check  | Status    | 2     | Partially complete      |
| ✓      | Check Mark        | Confirmed | 1     | Verified result         |
| ✗      | X Mark            | Rejected  | 1     | Invalid input           |
| 🔴      | Red Circle        | Critical  | 2     | Production outage       |
| 🟢      | Green Circle      | Healthy   | 2     | All systems operational |
| 🟡      | Yellow Circle     | Warning   | 2     | High resource usage     |
| 🔵      | Blue Circle       | Info      | 2     | New feature available   |
| ⭐      | Star              | Important | 1     | Featured item           |
| 🚀      | Rocket            | Launch    | 2     | Deployment ready        |
| 🐛      | Bug               | Issue     | 2     | Known defect            |
| 📝      | Memo              | Docs      | 2     | Documentation needed    |
| 👤      | Person Silhouette | User      | 2     | User account            |
| 🔄      | Counterclockwise  | Refresh   | 2     | Retry operation         |
| ⏸️     | Pause Button      | Paused    | 2     | Temporarily stopped     |
| ▶️     | Play Button       | Start     | 2     | Begin execution         |
| 🛑      | Stop Sign         | Stop      | 2     | Halt operation          |
| 👁️     | Eye               | View      | 2     | Inspect details         |
| ⬇️     | Down Arrow        | Decrease  | 2     | Trend decreasing        |
| ⬆️     | Up Arrow          | Increase  | 2     | Trend increasing        |
| ➡️     | Right Arrow       | Stable    | 2     | No change               |

## Combined Emoji and Text

| Action                 | Status      | Owner     | Priority   |
| ---------------------- | ----------- | --------- | ---------- |
| ✅ Merge PR #123        | Done        | 👤 Alice   | 🔴 Critical |
| ❌ Fix security issue   | Blocked     | 👤 Bob     | 🔴 Critical |
| ⚠️ Update dependencies | In Review   | 👤 Charlie | 🟡 Medium   |
| 📝 Write documentation  | In Progress | 👤 David   | 🟢 Low      |
| 🚀 Deploy to production | Ready       | 👤 Eve     | 🔴 Critical |
| 🐛 Debug memory leak    | Assigned    | 👤 Frank   | 🟡 Medium   |

## Complex Width Test

| ID  | Symbol Combo | Description                | Expected Width |
| --- | ------------ | -------------------------- | -------------- |
| 1   | ✅✅✅          | Three single-width checks  | 3              |
| 2   | 🔴🟡🟢          | Three double-width circles | 6              |
| 3   | ✅ + 🚀        | Mixed width with text      | Varies         |
| 4   | 👤 👤 👤        | Three user icons           | 6              |
| 5   | ⚠️⚠️         | Two warning signs          | 4              |
| 6   | ✓ ✗ ☑️       | Mixed check symbols        | 4              |
