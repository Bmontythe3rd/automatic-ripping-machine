# Users and 2FA

## Roles

| Role | Access |
|------|--------|
| **Admin** | Settings, Database, Users, API keys, plus everything Operators can do |
| **Operator** | Home / active rips, history, logs, title search, job actions |

Default user `admin` is an Admin.

## Manage users

**Users** in the nav (Admin only): create users, set role, disable, reset password to `password`, clear 2FA.

## Two-factor authentication (TOTP)

1. Log in → **Account**  
2. **Set up 2FA** — scan QR (or enter the secret) in an authenticator app  
3. Confirm with a code — **save the backup codes** shown once  

Login then asks for a TOTP or backup code after the password.

## Disable 2FA

- On **Account**, confirm with a live authenticator code, or  
- Admin **Users → Clear 2FA**, or  
- SQLite recovery in [Waves-and-Rollback](Waves-and-Rollback)

## Dependencies

Docker image installs `pyotp`, `qrcode`, and `Pillow`. Rebuild the image after upgrading through Wave 7.
