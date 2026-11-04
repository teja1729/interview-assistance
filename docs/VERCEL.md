# Vercel deployment retired

This repository no longer includes Vercel deployment configuration or Vercel Queue integration.
For the supported deployment topology, follow [Railway deployment](RAILWAY.md).

GitHub's Vercel deployment status is managed by the Vercel GitHub App, not by files in this
repository. Disable the Vercel project's Git integration or remove the repository from the Vercel
GitHub App installation to stop Vercel deployment checks. Connect the same repository to Railway
and enable autodeploys for the `main` branch in each Railway service.
