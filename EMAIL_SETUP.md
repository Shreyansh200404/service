# Email Setup

The account approval flow emails the administrator-assigned username and initial password to the address on the registration request. The project reads SMTP configuration from a local `.env` file.

1. Install project dependencies with `pip install -r req.txt`.
2. Copy `.env.example` to `.env`.
3. Set `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` to the mail account details. For Gmail, enable 2-Step Verification and create a Google App Password; do not use the normal account password.
4. Keep `.env` private. It is excluded by `.gitignore`. Restart Django after changing it.
5. Run `python manage.py migrate`.
6. Approve a test registration request and confirm its status on the home page. The admin request list records when credentials were emailed.

When SMTP is not configured in development, Django uses the console email backend. Password reset requests will show an error instead of suggesting an email was delivered. In production (`DEBUG=false`), SMTP is selected by default; configure valid mail values before starting the app.
