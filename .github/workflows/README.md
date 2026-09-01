This folder contains GitHub Actions workflows for maintenance tasks.

The `run-migrations.yml` workflow runs Django migrations against the
production DATABASE_URL. It's intended to be triggered manually from the
Actions tab by a repository maintainer after confirming the deployment
and secrets are configured.

Important:
- Add the repository secret `DATABASE_URL` (postgres://...) before running.
- Optionally set `DJANGO_SETTINGS_MODULE` if your production settings module is different.
