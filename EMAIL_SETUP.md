# Email Setup

The account approval flow emails the administrator-assigned username and initial password to the address on the registration request. The project reads SMTP configuration from a local `.env` file.

1. Install project dependencies with `pip install -r req.txt`.
2. Copy `.env.example` to `.env`.
3. Set `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` to the mail account details. For Gmail, enable 2-Step Verification and use a Google App Password, not the regular account password.
4. Keep `.env` private. It is excluded by `.gitignore`.
5. Run `python manage.py migrate` and restart Django.
6. Approve a test registration request and confirm its status on the home page. The admin request list records when credentials were emailed.

When SMTP is not configured in development, Django uses the console email backend and the app warns the admin that credentials were not delivered. In production (`DEBUG=false`), SMTP is selected by default; set the real mail values before starting the app.
