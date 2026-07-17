---
name: libremax-tls-interception-ca
description: LibreMax network does TLS interception; Node tools need NODE_EXTRA_CA_CERTS pointing at the corporate CA bundle
metadata:
  node_type: memory
  type: project
  originSessionId: 2facbb1c-5059-4c5e-9e9c-9062906b3752
---

The LibreMax corporate network runs a transparent TLS-inspection appliance (no HTTP(S)_PROXY env var set) that re-signs HTTPS with an internal root CA: `CN=Libremax Internal CA` (thumbprint `AB1C471CDECE4829ECDFDC69A364DC4F0232DCC1`, valid to 2035-12-06). Windows trusts it, but Node.js ships its own CA list and ignores the Windows store, so Node-based tools fail with `SELF_SIGNED_CERT_IN_CHAIN` (e.g. Claude Code couldn't reach platform.claude.com).

**Why:** Node < 22 has no `--use-system-ca`; the fix is `NODE_EXTRA_CA_CERTS` pointing at a PEM bundle that includes the corporate root.

**How to apply:** A CA bundle exported from the Windows trust store (Root + CA, 81 certs incl. the Libremax CA) lives at `C:\Users\hzeng\.claude\corp-ca-bundle.pem`, and `NODE_EXTRA_CA_CERTS` is set to it at User scope. If any Node tool (Claude Code, npm, etc.) hits a cert error: confirm the var is set and the bundle still contains `Libremax Internal CA`. To regenerate, re-export `Cert:\LocalMachine\Root` + `Cert:\CurrentUser\Root` + `Cert:\LocalMachine\CA` to PEM (UTF-8 no BOM). A newly opened terminal is required for the persisted var to take effect.
