-- Clear OAuth provider tokens stored before they were encrypted at rest.
-- Nothing reads these columns. Rows stay so account linking keeps working.
-- Encrypted values are Fernet tokens, which always start with gAAAAA.
UPDATE oauth_providers
SET access_token = NULL
WHERE access_token IS NOT NULL
  AND access_token NOT LIKE 'gAAAAA%';

UPDATE oauth_providers
SET refresh_token = NULL
WHERE refresh_token IS NOT NULL
  AND refresh_token NOT LIKE 'gAAAAA%';
