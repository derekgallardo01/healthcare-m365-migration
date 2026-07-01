# Security

## Reporting a vulnerability

If you find a security issue in this project, please email
derekgallardo01@gmail.com with the details. I aim to respond within 3
business days.

## Scope

This kit ships with:
- A deterministic **mock** healthcare tenant. No live Graph
  authentication happens by default.
- A documented Graph swap point. Credentials for a real tenant are
  read from `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
  environment variables only. Nothing is written to disk.

## Sensitive data considerations

- The mock tenant's document paths, user names, and mailbox sizes are
  fictional. No real PHI is present.
- The HIPAA gate reports include configuration values but never
  document contents.
- Post-cutover audit output is safe to include in email + Slack;
  document paths are the only potentially sensitive field.

## Dependencies

The default runtime uses stdlib only. `msgraph-sdk` and `msal` are
optional extras for the production Graph path. Dependabot alerts are
enabled on the repo.
