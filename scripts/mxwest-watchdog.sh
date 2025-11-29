#!/bin/bash
#
# MXWest VPN Link Watchdog - AUTO-HEALING VERSION
# Monitors connectivity to 10.30.0.1 via Rome (192.168.3.99)
# Automatically restarts WireGuard on Rome if link is down
#
# Author: glassdome
# Created: November 2025
#

# Configuration
MXWEST_HOST="10.30.0.1"
GATEWAY_HOST="192.168.3.99"
ROME_USER="nomad"
ROME_KEY="/home/nomad/.ssh/rome_key"
MXWEST_USER="ubuntu"
MXWEST_KEY="/home/nomad/.ssh/mxwest_key"
LOG_FILE="/var/log/mxwest-watchdog.log"
MAILQ_LOG="/var/log/mxwest-mailq.log"
STATE_FILE="/tmp/mxwest-link-state"
PING_COUNT=3
PING_TIMEOUT=5
MAX_RESTART_ATTEMPTS=3
RESTART_COOLDOWN_FILE="/tmp/mxwest-restart-cooldown"
RESTART_COOLDOWN_SECONDS=300  # 5 minute cooldown between restart attempts

log_msg() {
    local level="$1"
    local msg="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

send_alert() {
    local status="$1"
    local message="$2"
    
    # Desktop notification (if available)
    if command -v notify-send &> /dev/null; then
        if [ "$status" == "DOWN" ]; then
            notify-send -u critical "🔴 MXWest VPN DOWN" "$message"
        elif [ "$status" == "RECOVERED" ]; then
            notify-send -u normal "🟢 MXWest VPN RECOVERED" "$message"
        else
            notify-send -u normal "🟢 MXWest VPN UP" "$message"
        fi
    fi
    
    # Wall message to all terminals
    echo "*** MXWEST LINK $status: $message ***" | wall 2>/dev/null || true
}

check_connectivity() {
    local host="$1"
    if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$host" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

get_last_state() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "UNKNOWN"
    fi
}

set_state() {
    echo "$1" > "$STATE_FILE"
}

can_attempt_restart() {
    # Check if we're in cooldown period
    if [ -f "$RESTART_COOLDOWN_FILE" ]; then
        local last_restart=$(cat "$RESTART_COOLDOWN_FILE")
        local now=$(date +%s)
        local elapsed=$((now - last_restart))
        if [ $elapsed -lt $RESTART_COOLDOWN_SECONDS ]; then
            local remaining=$((RESTART_COOLDOWN_SECONDS - elapsed))
            log_msg "INFO" "In restart cooldown period (${remaining}s remaining)"
            return 1
        fi
    fi
    return 0
}

set_restart_cooldown() {
    date +%s > "$RESTART_COOLDOWN_FILE"
}

check_mxwest_mailq() {
    # Check mail queue on mxwest when link is restored or during issues
    log_msg "INFO" "Checking mail queue on mxwest..."
    
    local mailq_output
    mailq_output=$(ssh -i "$MXWEST_KEY" -o ConnectTimeout=10 -o BatchMode=yes \
        "${MXWEST_USER}@${MXWEST_HOST}" \
        "mailq 2>/dev/null || postqueue -p 2>/dev/null" 2>&1)
    local ssh_exit=$?
    
    if [ $ssh_exit -eq 0 ]; then
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$timestamp] Mail queue check:" >> "$MAILQ_LOG"
        echo "$mailq_output" >> "$MAILQ_LOG"
        echo "---" >> "$MAILQ_LOG"
        
        # Check if queue has messages
        if echo "$mailq_output" | grep -q "Mail queue is empty"; then
            log_msg "INFO" "✓ Mail queue is empty - all good"
        elif echo "$mailq_output" | grep -q "is empty"; then
            log_msg "INFO" "✓ Mail queue is empty - all good"
        else
            # Count queued messages
            local queue_count=$(echo "$mailq_output" | grep -c "^[A-F0-9]" || echo "0")
            if [ "$queue_count" -gt 0 ]; then
                log_msg "WARNING" "⚠ Mail queue has $queue_count message(s) waiting"
                # Try to flush the queue
                log_msg "ACTION" "Attempting to flush mail queue..."
                ssh -i "$MXWEST_KEY" -o ConnectTimeout=10 -o BatchMode=yes \
                    "${MXWEST_USER}@${MXWEST_HOST}" \
                    "sudo postqueue -f 2>/dev/null" 2>&1
                log_msg "INFO" "Mail queue flush command sent"
            else
                log_msg "INFO" "Mail queue status: $(echo "$mailq_output" | head -1)"
            fi
        fi
    else
        log_msg "ERROR" "Could not check mail queue on mxwest: $mailq_output"
    fi
}

restart_wireguard_on_rome() {
    log_msg "ACTION" "Attempting to restart WireGuard on Rome..."
    
    # First check if we can reach Rome
    if ! check_connectivity "$GATEWAY_HOST"; then
        log_msg "ERROR" "Cannot reach Rome (192.168.3.99) - cannot restart WireGuard"
        return 1
    fi
    
    # SSH to Rome and restart WireGuard
    local ssh_output
    ssh_output=$(ssh -i "$ROME_KEY" -o ConnectTimeout=10 -o BatchMode=yes \
        "${ROME_USER}@${GATEWAY_HOST}" \
        "sudo systemctl restart wg-quick@wg0 && sleep 3 && sudo wg show wg0 | head -5" 2>&1)
    local ssh_exit=$?
    
        if [ $ssh_exit -eq 0 ]; then
            log_msg "ACTION" "WireGuard restart command sent to Rome"
            log_msg "DEBUG" "WireGuard status: $(echo "$ssh_output" | tr '\n' ' ')"
            
            # Wait for tunnel to establish
            sleep 5
            
            # Verify connectivity restored
            if check_connectivity "$MXWEST_HOST"; then
                log_msg "SUCCESS" "✓ WireGuard restarted - MXWest link RESTORED!"
                send_alert "RECOVERED" "Auto-healed! WireGuard restarted on Rome, link restored."
                set_state "UP"
                
                # Check mail queue after recovery
                check_mxwest_mailq
                
                return 0
            else
                log_msg "WARNING" "WireGuard restarted but MXWest still unreachable"
                return 1
            fi
    else
        log_msg "ERROR" "Failed to restart WireGuard via SSH: $ssh_output"
        return 1
    fi
}

main() {
    local last_state=$(get_last_state)
    local gateway_up=false
    local mxwest_up=false
    local current_state="DOWN"
    local details=""
    
    # Check gateway first
    if check_connectivity "$GATEWAY_HOST"; then
        gateway_up=true
        
        # Check mxwest through the VPN
        if check_connectivity "$MXWEST_HOST"; then
            mxwest_up=true
            current_state="UP"
        fi
    fi
    
    # Build status details
    if [ "$gateway_up" = true ] && [ "$mxwest_up" = true ]; then
        details="Gateway: ✓ | MXWest: ✓ | Link healthy"
    elif [ "$gateway_up" = true ] && [ "$mxwest_up" = false ]; then
        details="Gateway: ✓ | MXWest: ✗ | VPN tunnel may be down"
    else
        details="Gateway: ✗ | MXWest: ✗ | Gateway unreachable"
    fi
    
    # State transition detection and auto-healing
    if [ "$current_state" != "$last_state" ]; then
        if [ "$current_state" == "DOWN" ]; then
            log_msg "CRITICAL" "Link DOWN - $details"
            send_alert "DOWN" "$details"
            set_state "DOWN"
            
            # AUTO-HEAL: Try to restart WireGuard if gateway is up but VPN is down
            if [ "$gateway_up" = true ] && [ "$mxwest_up" = false ]; then
                if can_attempt_restart; then
                    set_restart_cooldown
                    log_msg "ACTION" "Attempting auto-heal..."
                    if restart_wireguard_on_rome; then
                        current_state="UP"
                    fi
                fi
            fi
            
        elif [ "$last_state" != "UNKNOWN" ]; then
            log_msg "INFO" "Link RECOVERED - $details"
            send_alert "UP" "Link restored"
            set_state "UP"
            
            # Check mail queue after recovery
            check_mxwest_mailq
        else
            log_msg "INFO" "Initial state: $current_state - $details"
            set_state "$current_state"
        fi
    else
        # Link still down - retry healing if we haven't recently
        if [ "$current_state" == "DOWN" ] && [ "$gateway_up" = true ]; then
            if can_attempt_restart; then
                set_restart_cooldown
                log_msg "ACTION" "Link still down - retrying auto-heal..."
                if restart_wireguard_on_rome; then
                    current_state="UP"
                fi
            fi
        fi
    fi
    
    # Always log current status (verbose mode)
    if [ "$1" == "-v" ]; then
        log_msg "DEBUG" "$details"
    fi
    
    # Return status for scripting
    if [ "$current_state" == "UP" ]; then
        return 0
    else
        return 1
    fi
}

# Create log file if needed
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/mxwest-watchdog.log"

main "$@"
