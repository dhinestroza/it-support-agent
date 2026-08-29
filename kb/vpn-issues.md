# VPN connection issues

## When this applies
Use this guide when an employee reports they cannot connect to the
company VPN, or the connection drops repeatedly.

## Common fixes, in order
1. Confirm the employee is using the current VPN client version — go to
   Settings > About in the VPN app. If it's more than 2 versions behind,
   have them update from `https://vpn.internal.company.com/download`.
2. Restart the VPN client (not just reconnect — fully quit and reopen).
3. Check the employee's local internet connection works without VPN
   first (open any website). If their internet itself is down, this
   isn't a VPN issue.
4. Confirm the employee's VPN credentials haven't expired — VPN
   certificates renew automatically every 90 days but occasionally fail;
   a re-issued certificate fixes this.

## Information needed before resolving
To give a specific answer, we need: which operating system, the exact
error message shown (if any), and whether this started suddenly or the
VPN never worked for this employee. A report that just says "VPN doesn't
work" without any of this is not enough to answer — ask for it.

## When to escalate
Escalate if the fixes above don't work, if multiple employees report the
same issue at the same time (possible infrastructure outage), or if the
employee needs a new VPN certificate issued manually.
