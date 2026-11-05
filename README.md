# Job Radar V10: website first

This is a NEW repository package, not an update to V9. No JOBS.md, AI, user tokens, email passwords, issue notifications, or repository write permission. No private CV data is included.

## Upload in the browser
1. Create a NEW public GitHub repository, e.g. job-radar-v10. Keep default branch main.
2. Drag collector.py, index.html, jobs.json and README.md into Upload files. Commit.
3. Add file > Create new file. Name it .github/workflows/update.yml. Paste the contents of the supplied update.yml, then commit. Uploading update.yml to the root does NOT activate automation.
4. Settings > Pages > Source: GitHub Actions. Do NOT choose Deploy from a branch.
5. Actions > Update website > Run workflow. Wait for build and deploy to finish.
6. Settings > Pages > Visit site. Bookmark THAT address, not the repository file view. You do not need to construct the URL.

## How it works
A permanent index.html dashboard reads jobs.json. A Python collector checks four configured RSS/Atom endpoints concurrently every six hours and generates fresh data. Each source failure is visible. If a source fails, its previous results are retained when the previous published jobs.json is reachable. On a first run with all sources failing, the website explicitly shows no live results and the errors. It does NOT fabricate jobs.

The scheduled runs are best-effort, not guaranteed every six hours. GitHub may delay schedules or disable inactive public-repository schedules. Public GitHub Pages is supported on GitHub Free; use no paid add-ons. No email delivery is promised or configured.

## Ranking
Six tracks: Construction, Infrastructure, WASH, Contracts, Facilities, Architecture. Each configured phrase scores 24 in the title or 8 in the description, once per phrase. The strongest track wins. Technical score must reach 16 before employer/location bonuses apply. Title exclusions reject common digital, intern, driver, finance and communications roles. This is a discovery ranking, NOT eligibility verification. Internal-only wording is screened, but nuanced restrictions and deadlines still require human review.

## Failure recovery
- Page 404: check Pages Source and deploy log; this cannot be fixed by changing scoring weights.
- Dashboard loads but all feeds unavailable: collection problem, not website problem. See the exact source errors. The configured endpoints are not guaranteed current or accessible from GitHub.
- Test step fails: inspect the actual assertion; no broken build is published.
- Deployment fails: the prior deployed website remains; read the run summary for collection health.
- A green run does not prove current vacancies exist. Inspect source health and dates.

## Tests and limits
Run python3 collector.py test. These are synthetic unit/regression tests, not live vacancy verification. The old 60/60 claims are not carried forward. Browser logic uses textContent, validates HTTP(S) links, and has explicit missing-data states. No browser end-to-end or real GitHub deployment is claimed tested here.

## Workflow to paste
```yaml
name: Update website
on:
  push:
    branches: [main]
  workflow_dispatch:
  schedule:
    - cron: '23 */6 * * *'
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: job-radar-pages
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v6
      - name: Test collector
        run: python3 collector.py test
      - name: Prepare visible dashboard
        run: |
          mkdir -p site
          cp index.html jobs.json site/
      - name: Collect public feeds
        run: python3 collector.py
        env:
          PREVIOUS_DATA_URL: https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/jobs.json
      - uses: actions/upload-pages-artifact@v5
        with:
          path: site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.publish.outputs.page_url }}
    steps:
      - name: Publish website
        id: publish
        uses: actions/deploy-pages@v5
```
