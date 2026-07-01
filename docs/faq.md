# FAQ

**Q: Is this HIPAA-certified? Can I use it for our audit?**

No, and don't. This kit gives you a starting-point HIPAA
configuration gate with concrete CFR citations, but a real HIPAA audit
requires signed BAA execution with Microsoft, a documented risk
analysis, a compliance officer sign-off, and vendor-specific
attestations that no automated tool can generate. Use this kit to
catch **basic** misconfigurations before the auditor arrives, not to
replace the auditor.

---

**Q: Why 8 HIPAA checks specifically? What about {other check}?**

The 8 checks were picked because they're the ones that most often
fail on a fresh healthcare M365 tenant AND have a concrete
tenant-level config the kit can read. Checks that require inspecting
individual document contents (e.g. "no PHI in email subject lines")
are handled at the DLP-policy layer once that policy is turned on —
they'd need a separate scan, not a config check.

Add your own checks by editing `hipaa_gate.py`. See
[customization.md](customization.md).

---

**Q: Does the wave planner handle 500-user or 5,000-user migrations?**

Yes, but the pilot cap of 10 stays fixed (pilot exists to derisk the
next 4,990 users, not to migrate them). Wave 1 will always be the
largest single department; wave 2 will be everything else. For
5,000 users you'd likely want to split wave 2 further by geography or
office location — that's a 20-line change to `plan_migration()`.

---

**Q: The post-cutover audit finds 3 stuck users on the mock. Is that a
   problem in production?**

3 stuck users out of 50 is 6%, which is within the typical
"post-cutover activation lag" window (some users are on vacation, some
haven't gotten the memo). Follow up by wave day 5; if any user still
hasn't signed in by day 10, that's a rollback signal for that user.
The mock's stuck users have `last_signin` 140 days ago (leave / rotated
staff), which is why the demo surfaces them.

---

**Q: Why is the mock tenant deliberately misconfigured?**

Because the entire point of the HIPAA gate is to *catch*
misconfigurations. A fully-hardened mock tenant would let every check
pass, which would demonstrate nothing. See `test_hardened_tenant_clears`
in `tests/test_hipaa_gate.py` for what a passing gate looks like.

---

**Q: Can I run this against a Google Workspace or on-prem Exchange
source?**

Not directly. The Backend surface is designed around the target M365
tenant (where the HIPAA gate applies). For sourcing FROM Google
Workspace or on-prem Exchange, use Microsoft's own SharePoint
Migration Tool + a source-tenant Exchange Hybrid config; this kit
gates the *destination* tenant.

---

**Q: Do you offer this as a delivered engagement?**

Yes. See my Upwork profile at
[upwork.com/freelancers/derekgallardo](https://www.upwork.com/freelancers/~derekgallardo)
or email derekgallardo01@gmail.com. Typical pilot migration
engagement: 6-8 weeks, USD 4,500 - 6,000 fixed for the pilot phase,
plus USD 400/mo retainer for post-cutover audits.
