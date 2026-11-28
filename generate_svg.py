import os
import json
import base64
import datetime
import urllib.request

# GitHub configuration
USERNAME = "reabphirom002"
TOKEN = os.environ.get("GH_TOKEN", "")

# Send GraphQL request to GitHub API
def graphql_request(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "reabphirom002-profile-engine"
        }
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

# GraphQL query for public and private repositories
QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    starredRepositories { totalCount }
    repositories(
      first: 100
      ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        name
        isPrivate
        isFork
        stargazerCount
        forkCount
        defaultBranchRef {
          target {
            ... on Commit {
              history { totalCount }
            }
          }
        }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      pullRequestReviewContributions { totalCount }
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
          }
        }
      }
    }
  }
}
"""

data = graphql_request(QUERY, {"login": USERNAME})
u = data["data"]["user"]
c = u["contributionsCollection"]
cal = c["contributionCalendar"]
repos = u["repositories"]["nodes"]

# Load local avatar.png as Base64
avatar_data_uri = ""
if os.path.exists("avatar.png"):
    with open("avatar.png", "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        avatar_data_uri = f"data:image/png;base64,{b64}"

# Calculate account uptime
created_dt = datetime.datetime.strptime(u["createdAt"], "%Y-%m-%dT%H:%M:%SZ")
now_dt = datetime.datetime.utcnow()
diff_days = (now_dt - created_dt).days
years, rem_days = divmod(diff_days, 365)
months, days = divmod(rem_days, 30)
uptime_str = f"{years} years, {months} months, {days} days"

# Aggregate commits, stars, forks, and languages
lang_totals = {}
total_stars_received = 0
total_forks = 0
all_repo_commits = 0
private_repo_commits = 0

top_repo_name = "phirom-ecosystem"
top_repo_stars = 0
best_score = -1

for r in repos:
    stars = r["stargazerCount"]
    forks = r["forkCount"]
    total_stars_received += stars
    total_forks += forks

    branch = r.get("defaultBranchRef")
    c_count = branch["target"]["history"]["totalCount"] if (branch and branch.get("target")) else 0
    all_repo_commits += c_count

    if r["isPrivate"]:
        private_repo_commits += c_count

    score = (stars * 1000) + c_count
    if score > best_score:
        best_score = score
        top_repo_name = r["name"]
        top_repo_stars = stars

    if not r["isFork"]:
        for edge in r["languages"]["edges"]:
            lname = edge["node"]["name"]
            lsize = edge["size"]
            lang_totals[lname] = lang_totals.get(lname, 0) + lsize

# Calculate top 3 languages by byte size
total_bytes = sum(lang_totals.values())
if total_bytes > 0:
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    languages_str = ", ".join([f"{k} {round((v / total_bytes) * 100)}%" for k, v in sorted_langs])
else:
    languages_str = "JavaScript 61%, HTML 13%, CSS 7%"

# Finalize GitHub metrics
repos_count = u["repositories"]["totalCount"]
followers_count = u["followers"]["totalCount"]
stars_count = max(total_stars_received, u["starredRepositories"]["totalCount"])

api_commits = c["totalCommitContributions"] + c["restrictedContributionsCount"]
commits_count = max(all_repo_commits, api_commits)

prs_count = c["totalPullRequestContributions"]
issues_count = c["totalIssueContributions"]
contributed_count = max(c["totalRepositoryContributions"], repos_count)
reviews_count = c["pullRequestReviewContributions"]["totalCount"]

private_count = max(private_repo_commits, c["restrictedContributionsCount"])
contributions_12m = max(cal["totalContributions"], commits_count)
top_repo_str = f"{top_repo_name} ({top_repo_stars} ★)"

# Text alignment helpers
def row_single(key, val, width=52):
    k_str = f". {key}: "
    dots = "." * max(2, width - len(k_str) - len(str(val)) - 1)
    return f'<tspan class="key">. {key}:</tspan><tspan class="dot"> {dots} </tspan><tspan class="val">{val}</tspan>'

def row_num(key, val, width=52):
    k_str = f". {key}: "
    dots = "." * max(2, width - len(k_str) - len(str(val)) - 1)
    return f'<tspan class="key">. {key}:</tspan><tspan class="dot"> {dots} </tspan><tspan class="num">{val}</tspan>'

def row_pair(k1, v1, k2, v2):
    d1 = "." * max(2, 23 - len(f". {k1}: ") - len(str(v1)))
    d2 = "." * max(2, 24 - len(f". {k2}: ") - len(str(v2)))
    return (
        f'<tspan class="key">. {k1}:</tspan><tspan class="dot"> {d1} </tspan><tspan class="num">{v1}</tspan>'
        f'<tspan class="dot"> | </tspan>'
        f'<tspan class="key">. {k2}:</tspan><tspan class="dot"> {d2} </tspan><tspan class="num">{v2}</tspan>'
    )

# Build activity bars for the last 24 weeks
weeks = cal["weeks"][-24:]
max_week = max([sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks] + [1])
bars_svg = ""
for idx, w in enumerate(weeks):
    cnt = sum(d["contributionCount"] for d in w["contributionDays"])
    if cnt > 0:
        h = max(4, int((cnt / max_week) * 18))
        x = 670 + idx * 11
        y = 536 - h
        bars_svg += f'<rect x="{x}" y="{y}" width="9" height="{h}" rx="1.5" fill="#2ea043"/>'

# Render SVG template
svg_output = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="550" viewBox="0 0 960 550">
  <defs>
    <radialGradient id="backGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00d2ff" stop-opacity="0.42"/>
      <stop offset="55%" stop-color="#005acc" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#0d1117" stop-opacity="0"/>
    </radialGradient>

    <linearGradient id="frameGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00d2ff"/>
      <stop offset="50%" stop-color="#005acc"/>
      <stop offset="100%" stop-color="#ff8b00"/>
    </linearGradient>

    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <clipPath id="photoClip">
      <rect x="45" y="42" width="320" height="445" rx="20"/>
    </clipPath>

    <linearGradient id="bottomFade" x1="0%" y1="70%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0d1117" stop-opacity="0"/>
      <stop offset="100%" stop-color="#0d1117" stop-opacity="0.82"/>
    </linearGradient>
  </defs>

  <style>
    .bg {{ fill: #0d1117; stroke: #21262d; stroke-width: 1.5px; }}
    text {{ font-family: "JetBrains Mono", Consolas, monospace; font-size: 13.5px; fill: #c9d1d9; white-space: pre; }}
    .hdr {{ fill: #58a6ff; font-weight: 600; }}
    .key {{ fill: #e38c2b; font-weight: 600; }}
    .val {{ fill: #c9d1d9; }}
    .num {{ fill: #58a6ff; font-weight: 600; }}
    .dot {{ fill: #484f58; }}
    .badge-txt {{ font-family: "JetBrains Mono", Consolas, monospace; font-size: 12px; fill: #00d2ff; font-weight: bold; letter-spacing: 1.5px; }}
  </style>

  <rect width="958" height="548" x="1" y="1" rx="10" class="bg"/>

  <!-- Left: Founder Portrait with Neon Glow -->
  <circle cx="205" cy="265" r="215" fill="url(#backGlow)"/>
  
  <g clip-path="url(#photoClip)">
    <rect x="45" y="42" width="320" height="445" fill="#161b22"/>
    <image href="{avatar_data_uri}" x="45" y="42" width="320" height="445" preserveAspectRatio="xMidYMid slice"/>
    <rect x="45" y="42" width="320" height="445" fill="url(#bottomFade)"/>
  </g>

  <rect x="45" y="42" width="320" height="445" rx="20" fill="none" stroke="url(#frameGrad)" stroke-width="2.5" filter="url(#neonGlow)"/>`    

  <!-- Right: Auto-Updated GitHub Metrics -->
  <text x="415" y="42"><tspan class="dot">— </tspan><tspan class="hdr">{USERNAME}@github</tspan><tspan class="dot"> ———————————————————————————————</tspan></text>
  <text x="415" y="65">{row_single("Uptime", uptime_str)}</text>
  <text x="415" y="87">{row_single("Role", "Full-Stack Developer &amp; AI Engineer")}</text>
  <text x="415" y="109">{row_single("Location", "Phnom Penh, Cambodia")}</text>
 <text x="415" y="131">{row_single("Focus", "Web &amp; Mobile Apps · AI &amp; Data · EdTech")}</text>
  <text x="415" y="153">{row_single("Stack", "JS · Laravel · Flutter · Java · Python · Cloudflare")}</text>
  <text x="415" y="175">{row_single("Languages", languages_str)}</text>

  <text x="415" y="212"><tspan class="dot">— </tspan><tspan class="hdr">Contact</tspan><tspan class="dot"> ————————————————————————————————————————————</tspan></text>
  <text x="415" y="235">{row_single("GitHub", f"github.com/{USERNAME}")}</text>
  <text x="415" y="257">{row_single("Website", "phirommanager.com")}</text>
  <text x="415" y="279">{row_single("Portfolio", "phirommanager.com/developer-portfolio")}</text>
  <text x="415" y="301">{row_single("Email", "reabphirom2@gmail.com")}</text>

  <text x="415" y="338"><tspan class="dot">— </tspan><tspan class="hdr">GitHub Stats</tspan><tspan class="dot"> ———————————————————————————————————————</tspan></text>
  <text x="415" y="361">{row_pair("Repos", repos_count, "Stars", stars_count)}</text>
  <text x="415" y="383">{row_pair("Forks", total_forks, "Followers", followers_count)}</text>
  <text x="415" y="405">{row_pair("Commits", commits_count, "Contributed", contributed_count)}</text>
  <text x="415" y="427">{row_pair("PRs", prs_count, "Issues", issues_count)}</text>
  <text x="415" y="449">{row_single("Top repo", top_repo_str)}</text>

  <text x="415" y="476"><tspan class="dot">— </tspan><tspan class="hdr">Last 12 Months</tspan><tspan class="dot"> —————————————————————————————————————</tspan></text>
  <text x="415" y="497">{row_pair("Contributions", contributions_12m, "Reviews", reviews_count)}</text>
  <text x="415" y="518">{row_num("Private", private_count)}</text>
  {bars_svg}
</svg>'''

# Save generated SVG
with open("profile.svg", "w", encoding="utf-8") as f:
    f.write(svg_output)
