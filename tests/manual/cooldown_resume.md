# early resume + late notification

1. Build prompt with mode: both, delay: 600, delay_type: background, if_drift: ignore.
2. Run pass 1; verify background timer spawned (`ps aux | grep sleep`).
3. Immediately: `/multi-review --resume-pair <pair-id>`.
4. Verify:
   - Pass 2 starts immediately (status transition + TaskStop).
   - No duplicate notify-send fires when timer expires.
5. Confirm pending dir cleaned up after pass 2.
