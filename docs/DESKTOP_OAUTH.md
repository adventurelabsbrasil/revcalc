# Desktop OAuth and managed installation (v0.9.15)

## Architecture

The Windows client uses the existing Tkinter UI, InstalledAppFlow, shared
auth_core helpers and calculation pipeline. It opens the system browser, sends
an authorization-code request with a new PKCE S256 challenge/state per attempt,
and listens on 127.0.0.1 at an OS-assigned port for up to 180 seconds. oauthlib
verifies state and sends the corresponding verifier to Google's token endpoint.
After validating scopes and the authenticated Drive identity/domain, tokens are
saved to Windows Credential Manager through WinVaultKeyring. An insecure keyring
backend causes an error; there is no plaintext token fallback.

Login, identity verification and refresh call Google directly. No RevCalc API,
Vercel, Supabase or token broker is required for desktop operation. Google Drive
and Internet access remain necessary. The web app retains its own confidential
Web OAuth client, cookies and server token store; no web secret is distributed.

## Administrator: provision once, distribute a ready kit

1. Confirm the Google Cloud project used for this deployment. Do not change the
   running web client's ID, secret, consent audience or redirects as part of a
   desktop rollout. A separate project is possible but has its own consent setup.
2. Configure Google Auth Platform with the application's identity and intended
   audience. Internal only permits accounts in the owning Workspace organization;
   a developer and a client in separate organizations must not assume Internal
   permits both. External testing requires explicit test users and may have
   short-lived refresh tokens. External production with the broad Drive scope
   can require Google's verification and organization administrator approval.
3. Create an OAuth client of type **Desktop app**. Client ID is an identifier,
   not a confidential credential. PKCE plus loopback is the desktop flow.
4. Enable Drive API and confirm the test user's permissions on required folders.
   Do not add Sheets scopes unless the deployed features actually need them.
5. Copy `cliente-kit/revcalc-desktop.example.json` to `revcalc-desktop.json` next
   to the installer and fill the tenant values. The example is intentionally
   invalid until placeholders are replaced. Use the real approved domain list,
   not a wildcard. The new BACEN folder field can be omitted when unused.
6. Distribute the configured kit through an authenticated administrator channel.
   Include Install-RevCalc.ps1, RevCalc-Installation.ps1 and Atualizar-RevCalc.ps1.
   Publish the matching version tag before using the downloading installer.
   For pre-release testing use `-ArchivePath` with an administrator-supplied
   local source ZIP containing `revcalc-0.9.15/`; no public tag is needed then.

The profile holds only desktop client ID, domains and Drive references. It must
never contain client_secret, tokens, session keys or infrastructure credentials;
unknown fields are rejected. Tenant metadata belongs in the private deployment
kit and is gitignored. For executable deployments the validated profile may be
bundled by pyinstaller.spec or delivered adjacent to RevCalc.exe.

Do not use a Web client with loopback, or distribute its secret to make it work.
This implementation uses an empty compatibility field for google-auth (which
requires a non-None client_secret for refresh/deserialization); users do not
provide a secret. Token exchange explicitly sends the client ID in the request
body. A controlled real login AND refresh must confirm that the registered
Desktop client supports this before release. If it does not, stop rollout and
review the registration/library rather than silently copying the web secret.

## Configuration and trust

Precedence for operational settings: environment, legacy .env, deployment profile,
existing development defaults. Dedicated GOOGLE_OAUTH_DESKTOP_CLIENT_ID or the
profile's desktop ID takes precedence over legacy GOOGLE_OAUTH_CLIENT_ID and
does not reuse GOOGLE_OAUTH_CLIENT_SECRET. Without a dedicated profile/ID, legacy
Desktop registrations keep working with their existing secret when present.

The installer stores the profile under
`%LOCALAPPDATA%\AdventureLabs\RevCalc\config\revcalc-desktop.json` and preserves it
on reinstall. A supplied replacement never silently overrides an existing profile.
An administrator can deliberately update this file with a new approved profile;
changing client IDs requires new consent, not rewriting IDs inside existing tokens.
REVCALC_PROFILE_PATH selects an explicit profile and fails closed if unreadable.

The domain policy is evaluated at startup, on login and on restored sessions.
Email identity comes from Google's authenticated Drive about endpoint, not browser
input or the saved last-email marker. Exact domain matching rejects malformed
addresses and lookalike/subdomains. Restored credentials must match the saved
account identity and include Drive scopes. A domain is not a per-user ACL: actual
file access/write authorization remains with Drive. Tenant administrators must
approve the domain list and folder sharing; being logged in does not imply access
to every case folder. API permission errors must not broaden scopes or sharing.

The profile is local policy, not tamper-proof enforcement on a machine controlled
by its user. Central revocation is through Google/Drive permissions. Immediate
centrally refreshed application policy would require a separate remote check and
change the independence guarantee. A future downloaded provisioning manifest
must be authenticated (preferably signed with a pinned verification key), cached
locally, versioned and validated; no runtime provisioning endpoint is introduced.

## Migration, reinstall and rollback

Existing keyring names stay unchanged: service `calculadora-revisao`, account
`oauth-tokens-{email}`, marker `ultimo-email`. Token JSON with the original
client/secret is preserved; missing secret is read as the public-client empty
compatibility value. Corrupt, revoked or unauthorized credentials require login
and are not deleted automatically. Logout still removes local keyring entries.

Each installation creates a distinct directory under `versions\<version>-<id>`.
The venv/editable package is built at its final path. Python/pip and configuration
imports must pass before `active.json` is replaced atomically. The stable launcher
reads that pointer and the persistent config. Previous directories and arbitrary
user files are retained, including on same-version reinstall. Unknown files are
preserved in the previous installation, not copied into the new application code.

The installer can discover the latest standard legacy version directory with a
.env or receive `-ExistingRoot`. Its .env is preserved byte-for-byte and copied
into persistent config, never to a predictable TEMP backup. REVCALC_ENV_PATH is
used by the launcher to read this canonical legacy file. No Credential Manager
entries are exported. A failed candidate remains inactive for diagnosis; cleanup
is an explicit administrator action. Rollback: with the app closed, restore
previous-active.json to active.json; no token/config changes are necessary.

Scripts and generated launcher use UTF-8 BOM for Windows PowerShell 5.1. Python
reads .env/JSON as utf-8-sig. All external process exit codes are checked; unique
temporary download folders contain only code and are removed after validating
their absolute path lies below TEMP.

## Validation and release gate

Automated tests cover real loopback sockets, PKCE/state with a fake Google token
endpoint, timeout cleanup, denied login, granted scopes, both token formats and
real google-auth refresh code with fake responses. Keyring is entirely mocked.
Web callback tests check signed state/verifier and retain server token storage.
Windows PowerShell 5.1 tests simulate installation processes in a temporary
fixture and verify migration, repeat install, profile preservation and failed
activation/rollback. CI runs these on Windows as well as the existing Linux tests.

Before publishing, test on a separate Windows installation with an approved test
account: first login, restart, forced token expiry/refresh, denied domain, Drive
folder access, same-version reinstall and update. Keep calculation testing in a
test folder. No automated test contacts real Google OAuth, changes production,
reads real keyring entries or writes real customer data. Actual consent and Google
registration compatibility remain a release gate, not inferred from mocked tests.

References: [Google native OAuth](https://developers.google.com/identity/protocols/oauth2/native-app),
[RFC 8252](https://www.rfc-editor.org/rfc/rfc8252),
[PowerShell encoding](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding).
