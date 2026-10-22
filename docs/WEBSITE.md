# Project website

The public showcase lives in `website/`. It is plain HTML, CSS, SVG, and JavaScript
with no build step or production dependencies. The interactive examples are
fictional, scripted demonstrations. They do not capture audio, call an AI service,
connect to AWS, or save visitor data.

The expanded showcase includes the full project title, a simulated pause flow,
an editable terminal lab, verified technical specifications, speech research,
setup commands, and an expandable roadmap. The lab displays a continuation
supplied by the visitor, enforcing the 12-word/160-character contract. It does
not generate, shorten, or ground a response with Nemotron. A live model demo
would require a separately hosted backend; never embed a Toolkit key in Pages.

The demo-video and Google Drive poster URLs have not been supplied. The resources
section labels these links as coming soon and provides working alternatives.
Replace those labels with real links when the project owner supplies the URLs.

The spotlight treatment adapts React Bits' SpotlightCard; scroll arrivals draw
inspiration from AnimatedContent. See `website/design-credits.txt` for the reviewed
source revision and full upstream license. Effects use native JavaScript/CSS with
reduced-motion support, so the existing Pages workflow needs no React build.

## Preview and edit

From the repository root:

```sh
python3 -m http.server 8765 --directory website
```

Open `http://localhost:8765` on that computer. Edit `website/index.html` for copy
and illustrations, `website/style.css` and `website/showcase.css` for layout, and
`website/site.js` for interactions. All assets use relative paths
so they work under the repository's GitHub Pages subdirectory.

```sh
node --check website/site.js
git diff --check
```

Check mobile and desktop layouts, keyboard navigation, all three example cues,
replay, switching examples during the animation, architecture tabs, and FAQs.
Test the lab's custom text, word/character bounds, reset while playing, and editing
while playing; neither may leave an old cue visible. Check all roadmap accordions.
The page supports reduced-motion preferences and provides a no-JavaScript note.
Its content security policy blocks outbound connections and external scripts.

Keep published content separate from `private/`, model files, timing reports,
credentials, portfolio snapshots, and saved conversation summaries. The reported
ASR metric is one small operator-reported baseline, not an end-to-end latency or
accuracy claim. Update that qualification if changing the metric.

## Publish with GitHub Pages

Expected project URL after a successful deployment:

<https://co-wingman-ai.github.io/Co-Wingman-Edge-AI/>

The `.github/workflows/pages.yml` workflow deploys **only `website/`**. It runs on
changes to the website or workflow on `main`, and can also be started manually.
It uses GitHub's scoped workflow token and OIDC; no personal token or AWS/API
secret belongs in the site or workflow.

Repository setup, if Pages is not already enabled:

1. Open [Settings → Pages](https://github.com/Co-Wingman-AI/Co-Wingman-Edge-AI/settings/pages).
2. Under **Build and deployment**, select **GitHub Actions** as the source.
3. Open [Deploy project website](https://github.com/Co-Wingman-AI/Co-Wingman-Edge-AI/actions/workflows/pages.yml)
   and choose **Run workflow** on `main` if the initial push did not deploy.
4. Wait for the deployment to succeed. Open the URL reported by the deployment
   and check the demo and mobile layout on the published site.

An administrator may need to enable Actions/Pages or approve the `github-pages`
environment under organization rules. A private repository needs a GitHub plan
that supports Pages for private repositories. Do not change repository visibility
as a deployment workaround without the owner's explicit approval. Publishing
this static directory does not require publishing private runtime data.

The presence of a workflow or this URL alone does not confirm a live deployment;
check the successful Pages job and the served website.
