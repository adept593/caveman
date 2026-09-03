# Privacy Policy

**Last updated: 4 September 2026**

This policy covers the private OAuth application used by the operator of this
repository to manage their own YouTube channels. The application is not offered
to the public and has no users other than its owner.

## What the application does

It authenticates against the YouTube Data API v3 on behalf of the account that
owns the channels, in order to:

- read channel and video metadata (titles, descriptions, statistics);
- update titles, descriptions, tags and thumbnails on those channels;
- upload videos to those channels.

## What data it accesses

Only data belonging to the Google account that grants access, and only through
the scopes that account approves at the consent screen:

- `https://www.googleapis.com/auth/youtube`
- `https://www.googleapis.com/auth/youtube.upload`
- `https://www.googleapis.com/auth/youtube.force-ssl`

No data about any other person is requested, accessed, or processed.

## What is stored

An OAuth refresh token, held in a private configuration file on the operator's
own machines and readable only by the operator's account. Nothing else is
persisted: no video content, no analytics exports, no personal data.

## What is shared

Nothing. The application has no server, no analytics, no third-party
integrations, and no recipients. Data is never sold, transferred, or disclosed.

## Retention and deletion

The refresh token is kept until it is revoked or replaced. Access can be
withdrawn at any time from the Google account's "Third-party apps with account
access" page (https://myaccount.google.com/permissions); revoking it renders the
stored token unusable immediately.

## Limited Use

Use of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements.

## Contact

Questions about this policy go to the account that owns the application,
reachable at the support email listed on the application's OAuth consent screen.
