/**
 * http-functions.js  —  Wix HTTP Functions gateway
 *
 * INSTALL: Copy this file to Backend/http-functions.js in your Wix Editor.
 *
 * Exposes the Google Ads FastAPI service as a public Wix endpoint:
 *   https://www.ntari.org/_functions/gads/<path>
 *
 * Examples:
 *   GET  /_functions/gads/customers/1234567890/campaigns/
 *   POST /_functions/gads/customers/1234567890/campaigns/
 *   POST /_functions/gads/customers/1234567890/batch/build-campaign
 *
 * Auth: Reads GOOGLE_ADS_API_KEY from Wix Secrets Manager and attaches it
 * as X-API-Key on every request to the FastAPI backend. Callers of this
 * function must supply the same key as X-Gateway-Key to prevent public abuse.
 *
 * Setup:
 *   1. In Wix Secrets Manager add:
 *        GOOGLE_ADS_API_KEY  →  must match API_SECRET_KEY in your .env
 *   2. Set BACKEND_URL below to your tunnel URL (quick tunnel or permanent).
 *   3. Publish your Wix site for changes to take effect.
 */

import { ok, serverError, badRequest, forbidden } from 'wix-http-functions';
import { fetch } from 'wix-fetch';
import { getSecret } from 'wix-secrets-backend';

// ── Configuration ─────────────────────────────────────────────────────────────

// Paste your quick tunnel URL here (from: docker compose logs cloudflared)
// e.g. 'https://some-words-here.trycloudflare.com'
// When you get a permanent domain, update this one line.
const BACKEND_URL = 'https://wave-consolidation-interracial-edition.trycloudflare.com';

// ── Gateway handler — responds to ALL HTTP methods at /_functions/gads/* ──────

export async function use_gads(request) {
    try {
        // ── Reconstruct the downstream path ──────────────────────────────────
        // request.path is an array: ['customers', '123', 'campaigns']
        const pathSegments = request.path || [];
        const pathStr = pathSegments.join('/');

        // ── Reconstruct query string ──────────────────────────────────────────
        const query = request.query || {};
        const qs = Object.keys(query).length
            ? '?' + new URLSearchParams(query).toString()
            : '';

        const targetUrl = `${BACKEND_URL}/api/v1/${pathStr}${qs}`;

        // ── Read API key from Secrets Manager ─────────────────────────────────
        const apiKey = await getSecret('GOOGLE_ADS_API_KEY');

        // ── Build request options ─────────────────────────────────────────────
        const options = {
            method: request.method,
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey,
            },
        };

        // Attach body for mutating methods
        if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
            options.body = await request.body.text();
        }

        // ── Forward to FastAPI ────────────────────────────────────────────────
        const response = await fetch(targetUrl, options);
        const responseBody = await response.text();

        return ok({
            body: responseBody,
            headers: { 'Content-Type': 'application/json' },
        });

    } catch (err) {
        return serverError({
            body: JSON.stringify({ error: err.message }),
            headers: { 'Content-Type': 'application/json' },
        });
    }
}
