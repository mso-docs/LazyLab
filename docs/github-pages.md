# GitHub Pages demo and help

The `site/` folder is a buildless static website. It includes an evidence explorer, a downloadable research-design worksheet, appearance controls, and a video help guide. Its five measurements are taken from the committed completed-investigation example; no inference or scientific execution happens in the browser. The help page embeds `https://youtu.be/UV3h4IRk3go` only after a visitor chooses playback or a chapter.

## Publish

This repository is already configured to use the Actions publishing source. New files still need to be committed and pushed before they can deploy.

1. Commit and push `site/` and `.github/workflows/pages.yml` to `main`.
2. In the repository's **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
3. Open **Actions → GitHub Pages demo → Run workflow** if enabling Pages after the initial push. Otherwise, pushes changing the website deploy automatically.

The expected URLs are:

- Demo: https://mso-docs.github.io/LazyLab/
- Help: https://mso-docs.github.io/LazyLab/help.html

The workflow uploads only `site/`, excluding the application database, runtime artifacts, local secrets, and editorial drafts. It does not deploy the Python application. GitHub Pages must be enabled for the workflow to succeed; an unpushed working tree is not a deployed website.

This follows [GitHub's custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). The Actions deployment's returned URL is authoritative if the repository is renamed or moved.

## Preview locally

```bash
python3 -m http.server 8080 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8080. Serving over HTTP is required for loading the evidence JSON; opening `index.html` directly as a file can prevent that fetch. All page links and assets use relative paths so the project subdirectory on Pages works.

## Privacy and scope

Only appearance is persisted in local browser storage. Planning text remains in page memory unless downloaded. There are no analytics, model calls, profile credentials, or real application sessions in this site. YouTube receives requests after an explicit playback action; a text transcript link is also provided. The local Streamlit application retains its separate single-user deployment boundary.

## Verification

The static evidence JSON was checked against the original published metrics. Playwright verifies desktop and mobile layouts, phase filtering, experiment-table rendering, keyboard tab navigation, theme persistence, plan validation and JSON download, and explicit video loading with chapter offsets. The YouTube iframe request is mocked in browser checks; actual YouTube playback and the remote Pages deployment are separate checks. Run `NODE_PATH=/path/to/node_modules node scripts/check_static_demo.cjs` with the local preview server on port 8080 and Playwright installed.
