#!/usr/bin/env node
/**
 * Offline npm installer for NIRIKSHAN AI.
 *
 * WHY THIS EXISTS
 * ---------------
 * This machine cannot reach registry.npmjs.org (blocked by a filtering proxy).
 * However, ~/.npm/_cacache already contains the tarballs for the whole
 * dependency closure we need. `npm install --offline` still fails, because the
 * cached *packument* (registry metadata) was stored with `accept: application/json`
 * while npm asks for `application/vnd.npm.install-v1+json` — the `vary: accept`
 * header makes those two entries different cache keys, so npm reports ENOTCACHED.
 *
 * The tarball cache entries have no such mismatch. So this script:
 *   1. indexes every *.tgz entry in the cacache,
 *   2. resolves the dependency graph itself with npm's own bundled `semver`,
 *   3. extracts the result into ./node_modules with npm's own bundled `tar`.
 *
 * It is a build aid, not part of the application. On a machine with normal
 * network access you can ignore it entirely and just run `npm install`.
 */

import { createRequire } from 'node:module'
import { execSync } from 'node:child_process'
import { Readable } from 'node:stream'
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const npmRoot = execSync('npm root -g').toString().trim()
const require = createRequire(path.join(npmRoot, 'npm', 'node_modules', 'index.js'))
const cacache = require('cacache')
const semver = require('semver')
const tar = require('tar')

const CACHE = path.join(process.env.HOME, '.npm', '_cacache')
const TARGET = process.argv[2] || process.cwd()
const NM = path.join(TARGET, 'node_modules')

const ROOT_DEPS = {
  react: '18.3.1',
  'react-dom': '18.3.1',
  'react-router-dom': '6.30.6',
  recharts: '2.15.4',
  vite: '6.4.3',
  '@vitejs/plugin-react': '4.7.0',
  tailwindcss: '3.4.19',
  postcss: '^8.5.0',
  autoprefixer: '10.5.2',
}

const log = (...a) => console.log('[offline-npm]', ...a)

/* ------------------------------------------------------------------ *
 * 1. Index every cached tarball: name -> { version -> integrity }
 * ------------------------------------------------------------------ */
const PREFIX = 'make-fetch-happen:request-cache:https://registry.npmjs.org/'
const registry = new Map()

const entries = await cacache.ls(CACHE)
for (const key of Object.keys(entries)) {
  if (!key.startsWith(PREFIX)) continue
  const urlPath = key.slice(PREFIX.length)
  // <name>/-/<basename>-<version>.tgz   (name may be @scope/pkg)
  const m = urlPath.match(/^(.+)\/-\/(.+)-(\d[^/]*)\.tgz$/)
  if (!m) continue
  const [, name, , version] = m
  if (!semver.valid(version)) continue
  if (!registry.has(name)) registry.set(name, new Map())
  registry.get(name).set(version, entries[key].integrity)
}
log(`indexed ${registry.size} packages from cacache`)

/* ------------------------------------------------------------------ *
 * 2. Read package.json straight out of a gzipped tarball buffer.
 *    Minimal tar reader: 512-byte headers, octal size at offset 124.
 * ------------------------------------------------------------------ */
function readPackageJson(buf) {
  const t = zlib.gunzipSync(buf)
  let off = 0
  let longName = null
  while (off + 512 <= t.length) {
    const header = t.subarray(off, off + 512)
    if (header[0] === 0) break
    let name = header.subarray(0, 100).toString('utf8').replace(/\0.*$/, '')
    const sizeField = header.subarray(124, 136).toString('utf8').replace(/\0.*$/, '').trim()
    const size = parseInt(sizeField, 8) || 0
    const type = String.fromCharCode(header[156])
    const body = t.subarray(off + 512, off + 512 + size)
    off += 512 + Math.ceil(size / 512) * 512

    if (type === 'L') {               // GNU long name
      longName = body.toString('utf8').replace(/\0.*$/, '')
      continue
    }
    if (type === 'x' || type === 'g') { // pax header
      const px = body.toString('utf8').match(/\d+ path=([^\n]+)\n/)
      if (px) longName = px[1]
      continue
    }
    if (longName) { name = longName; longName = null }

    const rel = name.replace(/^[^/]+\//, '')
    if (rel === 'package.json') return JSON.parse(body.toString('utf8'))
  }
  return null
}

const tarballCache = new Map()
async function getTarball(name, version) {
  const k = `${name}@${version}`
  if (tarballCache.has(k)) return tarballCache.get(k)
  const integrity = registry.get(name)?.get(version)
  if (!integrity) return null
  const { data } = await cacache.get.byDigest(CACHE, integrity).then(
    (d) => ({ data: d }),
    () => ({ data: null })
  )
  tarballCache.set(k, data)
  return data
}

const manifestCache = new Map()
async function getManifest(name, version) {
  const k = `${name}@${version}`
  if (manifestCache.has(k)) return manifestCache.get(k)
  const buf = await getTarball(name, version)
  let mf = null
  if (buf) { try { mf = readPackageJson(buf) } catch { mf = null } }
  manifestCache.set(k, mf)
  return mf
}

/* ------------------------------------------------------------------ *
 * 3. Resolve the graph. One version per package (flat), highest that
 *    satisfies every requester; record conflicts for nesting.
 * ------------------------------------------------------------------ */
function pick(name, range) {
  const versions = registry.get(name)
  if (!versions) return null
  const list = [...versions.keys()]
  if (range === 'latest' || range === '*' || range === '') return semver.maxSatisfying(list, '*')
  return semver.maxSatisfying(list, range, { includePrerelease: false }) || null
}

const resolved = new Map()   // name -> Set(version)
const edges = []             // { from, fromVersion, name, version }
const missing = new Set()
const queue = []

for (const [name, range] of Object.entries(ROOT_DEPS)) {
  const v = pick(name, range)
  if (!v) { missing.add(`${name}@${range} (root)`); continue }
  queue.push({ name, version: v, from: '(root)' })
}

const seen = new Set()
while (queue.length) {
  const { name, version } = queue.shift()
  const key = `${name}@${version}`
  if (seen.has(key)) continue
  seen.add(key)

  if (!resolved.has(name)) resolved.set(name, new Set())
  resolved.get(name).add(version)

  const mf = await getManifest(name, version)
  if (!mf) { missing.add(`${key} (tarball unreadable)`); continue }

  const deps = { ...(mf.dependencies || {}) }
  const optional = mf.optionalDependencies || {}
  for (const [dn, dr] of Object.entries(optional)) deps[dn] = dr

  for (const [dn, dr] of Object.entries(deps)) {
    if (typeof dr !== 'string' || /^(npm:|file:|link:|git|http)/.test(dr)) continue
    const dv = pick(dn, dr)
    if (!dv) {
      if (!(dn in optional)) missing.add(`${dn}@${dr} (needed by ${key})`)
      continue
    }
    edges.push({ from: name, fromVersion: version, name: dn, version: dv })
    queue.push({ name: dn, version: dv, from: key })
  }
}

log(`resolved ${resolved.size} packages, ${seen.size} package-versions`)
if (missing.size) {
  log(`MISSING (${missing.size}):`)
  for (const m of [...missing].sort().slice(0, 40)) log('   -', m)
}

/* ------------------------------------------------------------------ *
 * 4. Extract. Hoist the highest version of each package to the root of
 *    node_modules; nest any other version under its dependents.
 * ------------------------------------------------------------------ */
const hoisted = new Map()
for (const [name, versions] of resolved) {
  hoisted.set(name, [...versions].sort(semver.rcompare)[0])
}

async function extract(name, version, dest) {
  const buf = await getTarball(name, version)
  if (!buf) throw new Error(`no tarball for ${name}@${version}`)
  fs.mkdirSync(dest, { recursive: true })
  await new Promise((res, rej) => {
    const rs = Readable.from(buf)
    const ex = tar.x({ cwd: dest, strip: 1 })
    rs.pipe(ex)
    ex.on('finish', res)
    ex.on('error', rej)
  })
}

fs.rmSync(NM, { recursive: true, force: true })
fs.mkdirSync(NM, { recursive: true })

let count = 0
for (const [name, version] of hoisted) {
  await extract(name, version, path.join(NM, name))
  count++
}

// Nested duplicates for version conflicts.
let nested = 0
for (const e of edges) {
  if (hoisted.get(e.name) === e.version) continue
  const parent = path.join(NM, e.from)
  if (hoisted.get(e.from) !== e.fromVersion) continue
  const dest = path.join(parent, 'node_modules', e.name)
  if (fs.existsSync(dest)) continue
  await extract(e.name, e.version, dest)
  nested++
}
log(`extracted ${count} hoisted + ${nested} nested packages`)

/* ------------------------------------------------------------------ *
 * 5. node_modules/.bin shims
 * ------------------------------------------------------------------ */
const BIN = path.join(NM, '.bin')
fs.mkdirSync(BIN, { recursive: true })
let bins = 0
for (const [name, version] of hoisted) {
  const mf = await getManifest(name, version)
  if (!mf?.bin) continue
  const map = typeof mf.bin === 'string' ? { [name.split('/').pop()]: mf.bin } : mf.bin
  for (const [binName, rel] of Object.entries(map)) {
    const target = path.join(NM, name, rel)
    if (!fs.existsSync(target)) continue
    try { fs.chmodSync(target, 0o755) } catch {}
    const link = path.join(BIN, binName)
    try { fs.rmSync(link, { force: true }) } catch {}
    fs.symlinkSync(path.relative(BIN, target), link)
    bins++
  }
}
log(`linked ${bins} bin shims`)
log('done ->', NM)
