# Permission Test

Version: 1.0.0-rc.1

## Roles

- Administrator: system configuration and security controls.
- Operator: daily operational tasks.
- Reviewer: review and approval tasks.
- Viewer: read-only access.

## Expected Restrictions

Viewer must not modify data.

Reviewer may review content but must not configure system security.

Operator may execute daily tasks but must not change security-critical settings.

Administrator may configure the system.

## Result

Documentation and role model reviewed.

## Release Note

Internal production auth UI is not complete in v1.0. Production deployment must enforce access through Cloudflare Access, VPN, or a secure reverse proxy before exposing the console.

## Release Impact

This is documented as a known limitation, not a code blocker for local/private RC usage.

