# AI contribution: 50% or more AI-generated

# Private listing photos (FIX-02 / SEC-06)

`POST /api/store/listings/` accepts its existing optional multipart `photo` field.
Role, active store and ownership checks run before upload. The backend applies
the active RuleSet byte and dimension limits, then `BlobPhotoStore.put_image`
validates/processes the JPEG/PNG and uploads only the cleaned bytes. PostgreSQL
stores an opaque `listing-photos/<uuid>.jpg` or `.png` reference, never a signed
URL. A database failure triggers deletion; an uncertain upload triggers cleanup.
Cleanup failures are logged as safe events without provider text, keys or URLs.

`GET /api/listings/` adds nullable `photo_url` to each card. The signed-in user's
household must be approved; the normal visibility query runs before link
generation. Only the current page's cards receive links. Storage is loaded once
and container privacy is checked once per page containing photos; pages without
photos do not contact storage. Privacy checks are not cached across requests.
Internal references are not
serialized. Responses use `Cache-Control: private, no-store` and
`Referrer-Policy: no-referrer`. No new endpoint or frontend screen is introduced.
The posting response remains unchanged; the existing listing form can upload
photos, while rendering browse-card images is a separate frontend change.

## Storage behaviour

- The container is created privately if absent. Existing public containers are
  refused; the adapter does not change another owner's access policy silently.
- Uploads use random names, the actual processed content type, no public access,
  no overwrites and `private, no-store` cache control. Name collisions never
  cause deletion of an existing blob.
- Read links grant only read permission to one blob for at most 300 seconds.
  Expiry uses UTC seconds, matching the SAS format. Permissions, resource and
  expiry are signed by the Azure SDK; callers cannot extend a URL by editing it.
- Signing verifies the container remains private. Possessing a valid link grants
  access until expiry; logging out does not invalidate a previously issued link.
  Previously downloaded files cannot be recalled by expiry.
- HTTPS is required outside explicit local Azurite/loopback development. An
  HTTPS link remains HTTPS-only even when local HTTP support is enabled.
- Configuration/credential failures become generic translated errors. Invalid
  images return 400; unavailable storage or photo access returns 503.

The SDK uses Storage API `2023-11-03`, supported by Azure and the pinned Azurite
emulator, rather than relying on an SDK default newer than the emulator. Server
API-version validation remains enabled. Each operation closes its SDK client.

## Local configuration

Docker Compose supplies the public Azurite development connection string, private
`iris-dev` container, internal endpoint `http://azurite:10000/devstoreaccount1`,
and browser endpoint `http://localhost:<IRIS_AZURITE_PORT>/devstoreaccount1`.
Using different endpoints is necessary because browsers cannot resolve Docker's
internal `azurite` hostname. No real Azure account is required.

```powershell
docker compose up -d --build backend
```

The `.env.example` files document the settings. When running outside Compose,
set these environment variables using the appropriate local or Azure values:

| Setting | Purpose |
| --- | --- |
| `LISTING_PHOTO_STORE_BACKEND` | Default `modules.listings.photo_storage.configured_store` factory. |
| `AZURE_STORAGE_CONNECTION_STRING` | Account-key connection string; preferred over the individual account settings when present. Never commit real credentials. |
| `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY` | Alternative when no connection string is provided. |
| `AZURE_STORAGE_CONTAINER_NAME` | Private photo container. |
| `AZURE_STORAGE_BLOB_ENDPOINT` | Internal endpoint when individual account settings are used. A connection string's `BlobEndpoint` takes precedence. |
| `AZURE_STORAGE_PUBLIC_BLOB_ENDPOINT` | Optional browser-reachable endpoint; defaults to the internal account endpoint. |
| `AZURE_STORAGE_ALLOW_HTTP` | Default false. Only explicit local/loopback/Azurite HTTP endpoints are accepted when true. |
| `LISTING_PHOTO_MAX_PIXELS` | Default 20 million decoded pixels; review worker memory before increasing. |

For staging, obtain the private container/account configuration from SET-17 and
provide secrets through deployment configuration/Key Vault. The present adapter
uses account-key SAS; Microsoft recommends user delegation SAS when possible.
Managed-identity/user-delegation authentication is not implemented here and
requires coordinating that deployment choice with SET-17. The implementation
must be exercised against real Azure before claiming staging verification.

## Repeatable tests

Fast standalone tests, from `backend`, need neither PostgreSQL nor Azure:

```powershell
uv run --locked python -m pytest -c photos.ini -q
```

Real upload, permissions, cleanup and expiry tests use the local services:

```powershell
docker compose exec -T backend env DJANGO_SETTINGS_MODULE=iris.settings.test IRIS_TEST_AZURITE=1 python -m pytest tests/test_blob_photos_azurite.py modules/listings/tests/test_photo_storage_live.py modules/listings/tests/test_photo_upload.py modules/reservations/tests/test_api.py -q
```

The real expiry acceptance test intentionally takes five minutes: it reads a
link, waits for the actual provider deadline, then verifies the same URL is
refused. Advancing Python's clock cannot advance Azurite. The other tests check
unsigned access, write/delete attempts with a read link, altered expiry,
cross-blob reuse, public-container refusal, real metadata removal and rollback.
CI runs against Azurite as well as PostgreSQL.

Tests create uniquely named dedicated `iris-photo-tests-*` / `iris-post-tests-*`
containers and remove them in fixture teardown. They use synthetic images and
the disposable PostgreSQL test database, not application household records.
The visual image-processing demo is separate and creates files only when its
explicit developer command is run; storage tests keep image bytes in memory.

## Manual check through Iris

1. Sign in with a store account assigned to an active store. Post a listing with
   a JPEG/PNG. A successful request returns 201 with the normal listing fields.
2. Sign in as a beneficiary with an approved household. The frontend listings
   screen is currently a placeholder and does not fetch cards. In the same
   browser, open `http://localhost:8000/api/listings/` directly; the session cookie
   is shared on localhost across these ports. Find the card's `photo_url` in the
   JSON response. Without the approved beneficiary session, access is refused.
3. Open that URL: the processed image should load. Opening the URL without its
   query string must be refused. Do not publish the signed URL in screenshots.
4. After its five-minute deadline, make a fresh request to the same URL. It
   should be refused; an image already displayed or cached is not a new request.
5. Repeat these checks in staging after Azure resources/configuration exist.

Primary references: [upload with the Python SDK](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-upload-python),
[service SAS](https://learn.microsoft.com/en-us/azure/storage/blobs/sas-service-create-python),
[user delegation SAS](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-user-delegation-sas-create-python).
