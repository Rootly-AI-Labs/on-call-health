# Reporting a Vulnerability

If you discover a security issue with the project, please contact us at [support@rootly.com](mailto:support@rootly.com).

## React Server Components advisory coverage

The frontend requires Next.js 16.4.5 or later in the 16.x release line and React/React DOM 19.3.1 or later in the 19.x release line. Commit `frontend/bun.lock` with dependency updates and use `bun install --frozen-lockfile` for reproducible installation.

- [GHSA-xqc2-xf4c-x3h3](https://github.com/react/react/security/advisories/GHSA-xqc2-xf4c-x3h3) is the October 2026 unauthenticated React Server Components RCE advisory. **No CVE has been assigned as of November 10, 2026.** Its React 19.3 fix is 19.3.1.
- Next.js bundles its own React Server Components implementation. The corresponding [GHSA-673q-mjm6-r5xr](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr) affects Next.js 16.0.0 through 16.4.0 and is fixed in 16.4.1. Updating only the top-level `react` package does not patch Next.js's bundled implementation.
- The older [CVE-2025-55182](https://react.dev/blog/2025/12/03/critical-security-vulnerability-in-react-server-components) is a separate RSC RCE vulnerability. The frontend's required versions also include that fix.

Next.js 16.4.5 additionally includes the [November 2026 security fixes](https://github.com/vercel/next.js/releases/tag/v16.4.5). These version requirements describe repository dependencies; deployed instances must be rebuilt and redeployed to receive dependency fixes.
