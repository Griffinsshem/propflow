/*
 * PropFlow load test (spec section 55): the core user journeys against seeded data.
 *
 * Every rate limit stays on. Each virtual user gets its own client IP via X-Forwarded-For
 * (the server trusts one proxy hop for this run), as real users would have in production.
 *
 * Usage (from the repo root): k6 run -e PROFILE=smoke|baseline load-tests/journeys.js
 */
import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

const ROOT = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const API = `${ROOT}/api/v1`;
const PROFILE = __ENV.PROFILE || 'baseline';
const PASSWORD = JSON.parse(open('./accounts.json')).password;
// Seeder defaults (backend/scripts/seed_load_data.py), used to address every tenant for cold logins.
const PROPERTIES_PER_ORG = 8;
const UNITS_PER_PROPERTY = 40;
const DOMAIN = 'load.propflow.test';

function pool(role) {
  return new SharedArray(role, () => {
    const emails = [];
    for (const org of JSON.parse(open('./accounts.json')).organizations) {
      const value = org[role];
      if (Array.isArray(value)) emails.push(...value);
      else emails.push(value);
    }
    return emails;
  });
}

const OWNERS = pool('owner');
const MANAGERS = pool('managers');
const CONTRACTORS = pool('contractors');
const TENANTS = pool('tenants');
const ORG_COUNT = OWNERS.length;

const rateLimited = new Counter('rate_limited_responses');
const conflicts = new Counter('conflict_responses');

// Initial p95 budgets, revisited after the baseline. Not spec figures.
const BUDGETS_MS = {
  'POST /auth/login': 1000,
  'POST /auth/login (new browser)': 1000,
  'GET /dashboard/tenant': 300,
  'GET /dashboard/operations': 300,
  'GET /dashboard/organization': 300,
  'GET /dashboard/contractor': 300,
  'GET /maintenance': 300,
  'GET /maintenance/{id}': 300,
  'GET /work-orders': 300,
  'GET /notifications/unread-count': 200,
  'POST /maintenance': 500,
  'POST /maintenance/{id}/status': 500,
  'POST /work-orders/{id}/status': 500,
};

const PROFILES = {
  smoke: { ramp: '10s', hold: '30s', tenants: 2, managers: 1, contractors: 1, owners: 1, loginRate: 1 },
  // Same mix as baseline, shorter: enough samples to profile individual endpoints.
  profile: { ramp: '1m', hold: '3m', tenants: 40, managers: 15, contractors: 15, owners: 5, loginRate: 1 },
  baseline: { ramp: '2m', hold: '8m', tenants: 40, managers: 15, contractors: 15, owners: 5, loginRate: 1 },
};
const P = PROFILES[PROFILE];
if (!P) throw new Error(`Unknown PROFILE: ${PROFILE}`);

function users(fn, target) {
  return {
    executor: 'ramping-vus',
    exec: fn,
    startVUs: 0,
    gracefulRampDown: '30s',
    stages: [
      { duration: P.ramp, target },
      { duration: P.hold, target },
      { duration: '30s', target: 0 },
    ],
  };
}

const endpointThresholds = {};
for (const [name, ms] of Object.entries(BUDGETS_MS)) {
  endpointThresholds[`http_req_duration{name:${name}}`] = [`p(95)<${ms}`];
}

export const options = {
  scenarios: {
    tenants: users('tenantJourney', P.tenants),
    managers: users('managerJourney', P.managers),
    contractors: users('contractorJourney', P.contractors),
    owners: users('ownerJourney', P.owners),
    logins: {
      executor: 'constant-arrival-rate',
      exec: 'coldLogin',
      rate: P.loginRate,
      timeUnit: '1s',
      startTime: P.ramp,
      duration: P.hold,
      preAllocatedVUs: 5,
      maxVUs: 20,
    },
  },
  // k6 clears each VU's cookies between iterations by default; a real browser keeps its
  // session, so the session cookie must survive across iterations.
  noCookiesReset: true,
  summaryTrendStats: ['count', 'avg', 'med', 'p(95)', 'p(99)', 'max'],
  thresholds: Object.assign(
    {
      http_req_failed: ['rate<0.01'],
      checks: ['rate>0.99'],
      rate_limited_responses: ['count==0'],
    },
    endpointThresholds,
  ),
};

// --- per-VU helpers (each VU has its own JS runtime, cookie jar and session) ---------------

let csrf = null;
let warnings = 0;

function clientIp() {
  const id = exec.vu.idInTest;
  return `10.${Math.floor(id / 250) % 250}.${id % 250}.10`;
}

function headers(extra) {
  return Object.assign({ 'Content-Type': 'application/json', 'X-Forwarded-For': clientIp() }, extra);
}

function track(res, expected, label) {
  if (res.status !== expected && warnings < 3) {
    warnings += 1;  // a few per VU: enough to diagnose without flooding the output
    console.warn(`${label}: expected ${expected}, got ${res.status} ${res.body ? res.body.slice(0, 200) : ''}`);
  }
  if (res.status === 429) rateLimited.add(1);
  if (res.status === 409) conflicts.add(1);
  return check(res, { [`${label}: ${expected}`]: (r) => r.status === expected });
}

function get(path, name) {
  return http.get(`${API}${path}`, { headers: headers(), tags: { name } });
}

function post(path, body, name) {
  return http.post(`${API}${path}`, JSON.stringify(body), {
    headers: headers({ 'X-CSRF-Token': csrf }),
    tags: { name },
  });
}

function think(min, max) {
  sleep(min + Math.random() * (max - min));
}

function signIn(accounts) {
  if (csrf) return true;
  const email = accounts[(exec.vu.idInTest - 1) % accounts.length];
  const res = http.post(`${API}/auth/login`, JSON.stringify({ email, password: PASSWORD }), {
    headers: headers(),
    tags: { name: 'POST /auth/login' },
  });
  if (!track(res, 200, 'login')) {
    think(1, 3);
    return false;
  }
  const cookies = http.cookieJar().cookiesForURL(ROOT);
  csrf = cookies.propflow_csrf ? cookies.propflow_csrf[0] : null;
  return csrf !== null;
}

// --- journeys ------------------------------------------------------------------------------

const CATEGORIES = ['plumbing', 'electrical', 'water', 'appliance', 'security', 'other'];

export function tenantJourney() {
  if (!signIn(TENANTS)) return;
  track(get('/dashboard/tenant', 'GET /dashboard/tenant'), 200, 'tenant dashboard');
  think(2, 5);
  const mine = get('/maintenance?limit=10', 'GET /maintenance');
  if (track(mine, 200, 'own requests')) {
    const items = mine.json('items');
    if (items.length > 0) {
      track(get(`/maintenance/${items[0].id}`, 'GET /maintenance/{id}'), 200, 'request detail');
    }
  }
  track(get('/notifications/unread-count', 'GET /notifications/unread-count'), 200, 'unread count');
  if (Math.random() < 0.2) {
    think(5, 10); // writing the report
    const report = {
      category: CATEGORIES[Math.floor(Math.random() * CATEGORIES.length)],
      title: 'Load test issue',
      description: 'Created by the k6 load test.',
    };
    track(post('/maintenance', report, 'POST /maintenance'), 201, 'report issue');
  }
  think(5, 10);
}

export function managerJourney() {
  if (!signIn(MANAGERS)) return;
  track(get('/dashboard/operations', 'GET /dashboard/operations'), 200, 'operations dashboard');
  think(2, 5);
  const inbox = get('/maintenance?status=submitted&limit=25', 'GET /maintenance');
  if (track(inbox, 200, 'manager inbox')) {
    const items = inbox.json('items');
    if (items.length > 0) {
      const target = items[Math.floor(Math.random() * items.length)];
      const detail = get(`/maintenance/${target.id}`, 'GET /maintenance/{id}');
      if (track(detail, 200, 'request detail') && detail.json('allowed_transitions').includes('triaged')) {
        think(3, 8); // reading the report before triaging
        const body = { status: 'triaged', version: detail.json('version') };
        track(post(`/maintenance/${target.id}/status`, body, 'POST /maintenance/{id}/status'), 200, 'triage');
      }
    }
  }
  think(2, 5);
  track(get('/work-orders?overdue=true&limit=25', 'GET /work-orders'), 200, 'overdue work orders');
  track(get('/notifications/unread-count', 'GET /notifications/unread-count'), 200, 'unread count');
  think(5, 10);
}

const CONTRACTOR_STEPS = [
  ['assigned', 'accepted'],
  ['accepted', 'in_progress'],
  ['in_progress', 'completed'],
];

export function contractorJourney() {
  if (!signIn(CONTRACTORS)) return;
  track(get('/dashboard/contractor', 'GET /dashboard/contractor'), 200, 'contractor dashboard');
  think(2, 5);
  const [from, to] = CONTRACTOR_STEPS[Math.floor(Math.random() * CONTRACTOR_STEPS.length)];
  const jobs = get(`/work-orders?status=${from}&limit=10`, 'GET /work-orders');
  if (track(jobs, 200, 'contractor jobs')) {
    const items = jobs.json('items');
    if (items.length > 0) {
      think(3, 8);
      const job = items[0];
      const body = { status: to, version: job.version };
      track(post(`/work-orders/${job.id}/status`, body, 'POST /work-orders/{id}/status'), 200, `work order ${to}`);
    }
  }
  think(5, 10);
}

export function ownerJourney() {
  if (!signIn(OWNERS)) return;
  track(get('/dashboard/organization', 'GET /dashboard/organization'), 200, 'organization dashboard');
  think(3, 6);
  track(get('/dashboard/operations', 'GET /dashboard/operations'), 200, 'operations dashboard');
  think(3, 6);
  track(get('/maintenance?limit=25', 'GET /maintenance'), 200, 'request list');
  think(5, 10);
}

export function coldLogin() {
  // A new browser each time, cycling through all seeded tenants, each from its own IP.
  const i = exec.scenario.iterationInTest;
  const org = i % ORG_COUNT;
  const property = Math.floor(i / ORG_COUNT) % PROPERTIES_PER_ORG;
  const unit = Math.floor(i / (ORG_COUNT * PROPERTIES_PER_ORG)) % UNITS_PER_PROPERTY;
  const email = `tenant.${org}.${property}.${unit}@${DOMAIN}`;
  const res = http.post(`${API}/auth/login`, JSON.stringify({ email, password: PASSWORD }), {
    jar: new http.CookieJar(),
    headers: {
      'Content-Type': 'application/json',
      'X-Forwarded-For': `10.251.${Math.floor(i / 250) % 250}.${i % 250}`,
    },
    tags: { name: 'POST /auth/login (new browser)' },
  });
  track(res, 200, 'cold login');
}

export function handleSummary(data) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    [`load-tests/results/${PROFILE}-${stamp}.json`]: JSON.stringify(data, null, 2),
  };
}
