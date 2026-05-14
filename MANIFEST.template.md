# Deployed routines (template)

Copy this file to `MANIFEST.local.md` after deploying and fill in your trigger
IDs. `MANIFEST.local.md` is gitignored so your trigger IDs stay out of the
public repo.

| Routine | Cron | Repo | Base | Trigger ID |
|---|---|---|---|---|
| dmarcheck multi-sweep | 0 13 * * * | your-org/dmarcheck | main | trig_... |
| dmarcheck single issue | 0 14 * * * | your-org/dmarcheck | main | trig_... |
| donthype-me multi-sweep | 0 15 * * * | your-org/donthype-me | dev | trig_... |
| donthype-me single issue | 0 16 * * * | your-org/donthype-me | dev | trig_... |
| loomwiki multi-sweep | 0 17 * * * | your-org/loomwiki | main | trig_... |
| loomwiki single issue | 0 18 * * * | your-org/loomwiki | main | trig_... |
| govpeer multi-sweep | 0 19 * * * | your-org/govpeer | main | trig_... |
| govpeer single issue | 0 20 * * * | your-org/govpeer | main | trig_... |
