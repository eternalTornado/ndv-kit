export const meta = {
  name: 'ndv-gdd-to-spec',
  description: 'ndvkit GDD → modules.json + per-module requirement.md (EARS) + specify.md. One stage per run (args.stage: analyze | author | specify); the main session asks the user between stages.',
  phases: [
    { title: 'Analyze' },
    { title: 'Critic' },
    { title: 'Map' },
    { title: 'Write' },
    { title: 'Reconcile' },
    { title: 'Matrix' },
    { title: 'Ambiguity' },
    { title: 'Back-propagate' },
    { title: 'Compose' },
  ],
};

// Model per role — SoT: README §Model routing. Host override per role: args.models.
const MODEL = {
  analyst: 'opus', quoteVerifier: 'sonnet', critic: 'opus', mapper: 'opus',
  writer: 'opus', verifier: 'sonnet', fixer: 'opus', reconciler: 'opus',
  register: 'sonnet', ambiguity: 'opus', backprop: 'sonnet', composer: 'opus',
};
// Roles not listed run as the default workflow agent; their protocol is the prompt below.
const AGENT_TYPE = {
  writer: 'spec-writer', fixer: 'spec-writer', backprop: 'spec-writer', composer: 'spec-writer',
  mapper: 'module-architect', register: 'module-architect',
};
const MAX_FIX_ROUNDS = 2;
const BATCH_SIZE = 3;
const KINDS = ['data', 'formula', 'constant', 'state', 'flow', 'contract', 'edge', 'id-alloc', 'nfr'];
const STAGES = ['analyze', 'author', 'specify'];
const CHOICES = ['add', 'stopgap', 'withdraw'];
// Gate B answer kinds — action per kind: spec-writer §Mode compose-specify step 1.
const ANSWER_KINDS = ['clarify', 'out-of-scope', 'add', 'fix'];
const DEFAULT_KIT_RULES = '.claude/ndvkit/rules';

// ---------- args ----------

function fail(msg) { throw new Error('ndv-gdd-to-spec workflow: ' + msg); }
function isStr(x) { return typeof x === 'string' && x.trim().length > 0; }
function isObj(x) { return !!x && typeof x === 'object' && !Array.isArray(x); }
function list(x) { return Array.isArray(x) ? x : []; }
function needStr(v, name) { if (!isStr(v)) fail('args.' + name + ' is required (non-empty string)'); }
function needArr(v, name, nonEmpty) {
  if (!Array.isArray(v) || (nonEmpty && v.length === 0)) fail('args.' + name + ' must be a ' + (nonEmpty ? 'non-empty ' : '') + 'array');
}
function needUniqueIds(xs, name) {
  const seen = {};
  xs.forEach(x => { if (seen[x.id]) fail('args.' + name + ': duplicate id ' + x.id); seen[x.id] = true; });
}

const A = isObj(args) ? args : {};
if (STAGES.indexOf(A.stage) < 0) fail('args.stage must be one of ' + STAGES.join(' | ') + ' (got ' + JSON.stringify(A.stage) + ')');
needStr(A.feature, 'feature');
if (A.mode !== 'create' && A.mode !== 'update') fail("args.mode must be 'create' | 'update'");
if (!/^\d{4}-\d{2}-\d{2}$/.test(String(A.date || ''))) fail('args.date must be yyyy-mm-dd (scripts cannot read the clock — pass today)');
needArr(A.gddFiles, 'gddFiles', true);
A.gddFiles.forEach((f, i) => needStr(f, 'gddFiles[' + i + ']'));
if (!isObj(A.config)) fail('args.config is required (paths from .claude/ndvkit/ndvkit.config.json)');
['gddRoot', 'specsRoot', 'matrixRoot', 'templates'].forEach(k => needStr(A.config[k], 'config.' + k));
needArr(A.config.codeRoots, 'config.codeRoots', true);
if (A.moduleFilter != null) needArr(A.moduleFilter, 'moduleFilter', false);
// Snapshot of requirement.md / specify.md taken by the main session before this run (the kit never commits, so git is no baseline).
if (A.baselineDir != null) needStr(A.baselineDir, 'baselineDir');

if (A.stage === 'analyze') {
  needArr(A.chunks, 'chunks', true);
  A.chunks.forEach((c, i) => {
    if (!isObj(c) || !isStr(c.id) || !isStr(c.file)) fail('args.chunks[' + i + '] needs {id, file, headings[]}');
    needArr(c.headings, 'chunks[' + i + '].headings', true);
  });
  needUniqueIds(A.chunks, 'chunks');
  if (A.existingRequirements != null) needArr(A.existingRequirements, 'existingRequirements', false);
} else if (A.stage === 'author') {
  needArr(A.modules, 'modules', true);
  if (A.changed != null) needArr(A.changed, 'changed', false);
  A.modules.forEach((m, i) => {
    if (!isObj(m) || !isStr(m.id)) fail('args.modules[' + i + '].id is required');
    needArr(m.responsibilities, 'modules[' + i + '].responsibilities', A.mode !== 'update');
    m.responsibilities.forEach((r, j) => {
      if (!isObj(r) || !isStr(r.key) || !isStr(r.cite)) fail('args.modules[' + i + '].responsibilities[' + j + '] needs {key, kind, summary, cite}');
    });
    if (!m.responsibilities.length && !list(A.changed).some(x => isObj(x) && isStr(x.cite) && driftOwns(x, m))) {
      fail('args.modules[' + i + '] (' + m.id + '): empty responsibilities only allowed in update mode for a module with changed / removed FRs in args.changed');
    }
  });
  needUniqueIds(A.modules, 'modules');
  list(A.decisions).forEach((d, i) => {
    if (!isObj(d) || !isStr(d.cite) || !isStr(d.answer)) fail('args.decisions[' + i + '] needs {gapId, cite, question, answer, date}');
  });
  list(A.deferred).forEach((g, i) => {
    if (!isObj(g) || !isStr(g.cite) || !isStr(g.question)) fail('args.deferred[' + i + '] needs {gapId, question, cite}');
  });
} else {
  needArr(A.modules, 'modules', true);
  A.modules.forEach((m, i) => { if (!isObj(m) || !isStr(m.id)) fail('args.modules[' + i + '] needs {id, path}'); });
  needUniqueIds(A.modules, 'modules');
  list(A.answers).forEach((a, i) => {
    if (!isObj(a) || !isStr(a.module) || !isStr(a.answer)) fail('args.answers[' + i + '] needs {module, ref, question, answer, kind?}');
    if (a.kind != null && ANSWER_KINDS.indexOf(a.kind) < 0) fail('args.answers[' + i + '].kind must be ' + ANSWER_KINDS.join(' | '));
    if (a.kind != null && a.kind !== 'clarify' && !isStr(a.ref)) fail('args.answers[' + i + ']: kind ' + a.kind + ' needs ref (GDD cite / responsibility key / defect id)');
  });
  list(A.gapChoices).forEach((g, i) => {
    if (!isObj(g) || !isStr(g.consumer) || !isStr(g.owner) || !isStr(g.row)) fail('args.gapChoices[' + i + '] needs {consumer, row, owner, choice}');
    if (CHOICES.indexOf(g.choice) < 0) fail('args.gapChoices[' + i + '].choice must be ' + CHOICES.join(' | '));
    if (g.kind != null && g.kind !== 'surface' && g.kind !== 'obligation') fail('args.gapChoices[' + i + "].kind must be 'surface' | 'obligation'");
  });
}

const models = Object.assign({}, MODEL);
if (A.models != null) {
  if (!isObj(A.models)) fail('args.models must be an object {<role>: <model>}');
  Object.keys(A.models).forEach(role => {
    if (!Object.prototype.hasOwnProperty.call(MODEL, role)) fail('args.models.' + role + ': unknown role (roles: ' + Object.keys(MODEL).join(', ') + ')');
    needStr(A.models[role], 'models.' + role);
    models[role] = A.models[role];
  });
}

const C = {
  gddRoot: A.config.gddRoot,
  specsRoot: A.config.specsRoot,
  matrixRoot: A.config.matrixRoot,
  templates: A.config.templates,
  kitRulesRoot: isStr(A.config.kitRulesRoot) ? A.config.kitRulesRoot : DEFAULT_KIT_RULES,
  rulesRoot: isStr(A.config.rulesRoot) ? A.config.rulesRoot : '.claude/rules',
  codeRoots: A.config.codeRoots.filter(isStr),
  contractsDoc: isStr(A.config.contractsDoc) ? A.config.contractsDoc : '',
};
const FILTER = list(A.moduleFilter).filter(isStr);
const BASELINE = isStr(A.baselineDir) ? A.baselineDir.trim().replace(/[\\/]+$/, '') : '';

// ---------- runtime helpers ----------

const used = {};
const LOG = [];
function note(msg) { LOG.push(msg); log(msg); }

function call(role, prompt, opts) {
  used[role] = models[role];
  const o = { label: opts.label, phase: opts.phase, model: models[role] };
  if (opts.schema) o.schema = opts.schema;
  if (AGENT_TYPE[role]) o.agentType = AGENT_TYPE[role];
  return agent(prompt, o);
}

function q(s) { return '`' + s + '`'; }
// Arrays: one compact JSON entry per line (readable, cheap); anything else compact.
function js(x) { return Array.isArray(x) ? '[\n' + x.map(e => ' ' + JSON.stringify(e)).join(',\n') + '\n]' : JSON.stringify(x); }
function bullets(xs) { return xs.length ? xs.map(x => '- ' + x).join('\n') : '- (none)'; }
function fileOf(cite) { const s = String(cite || ''); const i = s.indexOf('#'); return (i < 0 ? s : s.slice(0, i)).trim(); }
// Gap / drift cites route writer batches by file: always `<chunk file>#<heading>`, whatever the analyst emitted.
function citeIn(file, cite) {
  const s = String(cite || '').trim();
  return s.indexOf(file + '#') === 0 ? s : file + '#' + s.replace(/^[^#]*\.md#/i, '').replace(/^#+\s*/, '');
}
// A drift entry (analyze `changed` / Scout `removedAnchors`) belongs to the module it names, else to the module its FR / NFR id prefixes.
function driftOwns(x, m) {
  if (isStr(x.module)) return x.module.trim() === m.id;
  const fr = String(x.fr || '').trim().toUpperCase();
  const id = m.id.toUpperCase();
  return fr.indexOf(id + '-FR-') === 0 || fr.indexOf(id + '-NFR-') === 0;
}
function uniq(xs) {
  const seen = {};
  return xs.filter(x => { const k = String(x); if (seen[k]) return false; seen[k] = true; return true; });
}
function reqPath(id) { return C.specsRoot + '/' + id + '/requirement.md'; }
function specPath(id) { return C.specsRoot + '/' + id + '/specify.md'; }
function basePath(id, file) { return BASELINE + '/' + id + '/' + file; }
// Logged once per stage: without a baseline the verifiers cannot tell "before this run" (git is no baseline — the kit never commits).
function noteBaseline() {
  if (!BASELINE) note('Baseline: args.baselineDir not passed — verifiers skip ID-stability / byte-identical / specify.md-unchanged comparisons');
}
function strs(x) { return list(x).filter(isStr); }
// pipeline stages get (prevResult, originalItem, index); the first stage reads the original item.
function own(prev, item) { return isObj(item) ? item : prev; }

// ---------- schemas ----------

const S = { type: 'string' };
const SA = { type: 'array', items: S };
function obj(properties, required) { return { type: 'object', properties: properties, required: required || Object.keys(properties) }; }
function arr(items) { return { type: 'array', items: items }; }
const OPTION = obj({ label: S, description: S });
const QUESTION_OPTIONS = arr(OPTION);
const ROW_KIND = { type: 'string', enum: ['surface', 'obligation'] };

const ANALYST = obj({
  chunkId: S,
  items: arr(obj({ key: S, kind: { type: 'string', enum: KINDS }, summary: S, literal: S, cite: S })),
  gaps: arr(obj({ gapId: S, question: S, cite: S, options: QUESTION_OPTIONS })),
  noTech: arr(obj({ heading: S, reason: S })),
  changed: arr(obj({ fr: S, cite: S, change: S })),
}, ['chunkId', 'items', 'gaps', 'noTech']);
const QUOTE = obj({ rejected: arr(obj({ key: S, reason: S })) });
const CRITIC = obj({ misses: arr(obj({ chunkId: S, heading: S, why: S })) });
const MAPPER = obj({
  modules: arr(obj({
    id: S, name: S, isNew: { type: 'boolean' }, extends: S, rationale: S, responsibilities: SA, gddSections: SA,
  }, ['id', 'name', 'isNew', 'rationale', 'responsibilities', 'gddSections'])),
  alternatives: arr(obj({ question: S, options: QUESTION_OPTIONS })),
  unmapped: arr(obj({ key: S, reason: S })),
  outOfFilter: arr(obj({ key: S, owner: S })),
}, ['modules', 'alternatives', 'unmapped']);
const WRITER = obj({
  modules: arr(obj({
    id: S, path: S, frIds: SA, nfrIds: SA, open: arr(obj({ ref: S, question: S, cite: S })),
    contractRows: arr(obj({ need: S, owner: S, kind: ROW_KIND })),
    orphanContractFRs: SA, removed: SA, contractsDocProposals: SA,
  }, ['id', 'path', 'frIds', 'nfrIds', 'open', 'contractRows'])),
});
const VERIFY = obj({ defects: arr(obj({ module: S, id: S, problem: S, evidence: S })) });
const FIX = obj({
  fixed: arr(obj({ module: S, id: S, change: S })),
  disputed: arr(obj({ module: S, id: S, reason: S, evidence: S })),
  open: arr(obj({ module: S, id: S, question: S })),
}, ['fixed', 'disputed']);
const RECON = obj({
  linked: arr(obj({ consumer: S, row: S, owner: S, kind: ROW_KIND, id: S, cite: S })),
  gaps: arr(obj({ consumer: S, row: S, owner: S, kind: ROW_KIND })),
});
const REGISTER = obj({
  touched: SA,
  layers: arr(obj({ layer: { type: 'integer' }, modules: SA })),
  cycles: arr(obj({ modules: SA, evidence: S })),
  findings: arr(obj({ finding: S, evidence: S, impact: S })),
});
const AMBIG = obj({
  module: S,
  questions: arr(obj({ qId: S, fr: S, question: S, options: QUESTION_OPTIONS })),
});
const BACKPROP = obj({
  target: S,
  newIds: arr(obj({ row: S, module: S, id: S })),
  stopgaps: arr(obj({ row: S, module: S })),
  conflicts: arr(obj({ row: S, module: S, outOfScope: S })),
});
const COMPOSE = obj({
  id: S, specifyWritten: { type: 'boolean' }, open: arr(obj({ fr: S, question: S, options: QUESTION_OPTIONS })),
  acCount: { type: 'integer' }, changedIds: SA,
  conflicts: arr(obj({ ref: S, reason: S })),
  contractGaps: arr(obj({ row: S, kind: ROW_KIND, target: S })),
}, ['id', 'specifyWritten', 'open', 'acCount', 'changedIds']);

// ---------- prompt building blocks ----------

const HEAD = 'ndvkit /ndv-gdd-to-spec — stage ' + A.stage + ' · feature ' + A.feature + ' · mode ' + A.mode + ' · date ' + A.date + '.';
const NO_ASK = 'Never ask the user: gaps, questions and doubts go into the structured output — the main session asks the user between stages. Your output is parsed by a script.';
const READ_ONLY = 'READ-ONLY: never create, edit, move or delete any file. Read / Glob / Grep and read-only shell (cmp, diff, ls, wc, git show, git log) only.';
const KIND_DEFS = [
  'data = entity / field / data table / content list',
  'formula = calculation (full symbols, never paraphrased)',
  'constant = balance number, threshold, percentage, limit, timing',
  'state = state or mode and its transitions',
  'flow = trigger → response sequence',
  'contract = what this feature needs from / provides to another system',
  'edge = boundary, invalid input, failure case',
  'id-alloc = ID / key / enum value allocation',
  'nfr = performance, memory, determinism, platform, security constraint',
].join('; ');

function rulesLine() {
  return 'Rules: read ' + q(C.kitRulesRoot + '/Shared/ai-discipline.md') + ' first — R1–R5 and R7 bind you (tool-first, verify before claim; say "I don\'t know"; cite every claim; literal quotes for values; nothing invented; Finding/Evidence/Impact). Host rules ' +
    q(C.rulesRoot + '/**') + ' + CLAUDE.md override the kit defaults at ' + q(C.kitRulesRoot + '/**') +
    ' on conflict — read the ones your checks need (security / authority boundary, id plan, numeric conventions, glossary).';
}
function pathsBlock() {
  return [
    'Paths (repo-root-relative, from .claude/ndvkit/ndvkit.config.json):',
    '- gddRoot: ' + q(C.gddRoot),
    '- specsRoot: ' + q(C.specsRoot) + ' — per module ' + q('<specsRoot>/<MODULE>/requirement.md') + ', ' + q('specify.md'),
    '- module matrix: ' + q(C.matrixRoot + '/modules.json'),
    '- codeRoots: ' + C.codeRoots.map(x => q(x)).join(', '),
    '- contractsDoc: ' + (C.contractsDoc ? q(C.contractsDoc) : 'N/A — not configured'),
    '- templates: ' + q(C.templates),
  ].join('\n');
}
function roleHeader(role, readOnly) {
  return [HEAD, 'Role: ' + role + '.', readOnly ? READ_ONLY : '', rulesLine(), NO_ASK].filter(Boolean).join('\n');
}
function modeHeader(agentName, mode) {
  return [
    HEAD,
    'You are dispatched as ' + q(agentName) + ' in **Mode ' + mode + '** — follow §Mode ' + mode +
      ' of your agent instructions (the protocol lives there; if they lack that section, read ' +
      q('.claude/ndvkit/agents/' + agentName + '.md') + ' and follow it).',
    NO_ASK,
  ].join('\n');
}
function section(title, body) { return '## ' + title + '\n' + body; }
function prompt(parts) { return parts.filter(Boolean).join('\n\n'); }

// ---------- stage: analyze ----------

function analystPrompt(c, existing) {
  return prompt([
    roleHeader('GDD technical analyst for chunk ' + c.id, true),
    section('Scope', 'GDD file ' + q(c.file) + ' — ONLY these headings (with their sub-headings); locate each with Grep -n, then Read its line range in full:\n' + bullets(c.headings.map(h => q(h)))),
    c.parent ? section('Re-analysis round', [
      'The completeness critic found content under these headings that no verified item covers:',
      js(c.why),
      'Already extracted from chunk ' + c.parent + ' (verified items) and gaps already raised — do NOT repeat them, even reworded:',
      js({ items: c.prior, gaps: c.priorGaps }),
      'Extract ONLY content not covered above (start with what the critic quoted); raise a gap only when no gap above asks the same decision.',
    ].join('\n')) : '',
    section('Extract', [
      'Every TECHNICAL item a developer needs to build this; drop narrative, lore, art direction, marketing, UX copy that states no rule.',
      'Kinds: ' + KIND_DEFS + '.',
      'Per item: key ' + q(c.id + '-<n>') + ' (n = 1, 2, … in reading order), kind, summary (one sentence, your words), literal (verbatim GDD quote ≤2 sentences carrying the value / rule — copy exactly, keep symbols and units), cite ' + q(c.file + '#<exact heading text>') + ' (the heading the literal sits under).',
      'One behaviour or value per item — split "and/or" chains. Never round, convert or normalise a value.',
    ].join('\n')),
    section('Gaps', [
      'Where the GDD is silent, vague or self-contradictory on something a developer must know to implement an item in scope (missing value, undefined term, unspecified edge / failure case, conflicting statements) → gap: gapId ' + q(c.id + '-G<n>') + ', question (concrete, ONE decision), cite ' + q(c.file + '#<exact heading text>') + ' (the heading that raises it), options (2–3 concrete answers — the main session adds "Defer" as the 4th; each description quotes the GDD text that constrains it, or says "GDD im lặng").',
      'A gap is a question — never fill it with inference, "typical game" defaults or filename guesses.',
    ].join('\n')),
    section('Coverage', 'noTech = every in-scope heading with no technical content → {heading, reason}. Every in-scope heading ends with ≥1 item, ≥1 gap, or a noTech entry.'),
    A.mode === 'update' ? section('Update mode — drift', [
      'Existing requirement files citing these GDD files:',
      bullets(existing.map(x => q(x))),
      'For every FR/NFR whose Source cites ' + q(c.file + '#<heading in scope>') + ': compare its quoted literal with the GDD now. Changed text or behaviour no longer stated under the heading → changed {fr, cite ' + q(c.file + '#<heading>') + ', change (' + q('"<old literal>" → "<new literal>"') + ' | ' + q('removed') + ')}. Unchanged → omit. Headings that no longer exist are detected by the main session\'s Scout — not in your scope. Source into a legacy TDD → skip (the author stage re-cites it).',
      'A Source of the form ' + q('<file>#<heading> + decision: <date> — "<answer>"') + ' is a user decision, not a GDD quote: never compare its answer with the GDD. Report it as changed only when the GDD now states its own value for the question the decision settles (change: ' + q('decision "<answer>" vs GDD "<new literal>"') + '). A question such a decision already settles is NOT a gap — do not emit it.',
    ].join('\n')) : '',
    'Return chunkId "' + c.id + '".',
  ]);
}

function quotePrompt(c, items) {
  return prompt([
    roleHeader('adversarial quote verifier for chunk ' + c.id, true),
    'Re-open ' + q(c.file) + ' yourself. For EACH item below try to refute it:\n' + [
      '1. the cite heading does not exist in the file → reject;',
      '2. the literal is not verbatim under that heading (tolerate only whitespace, line wrap and markdown emphasis; any changed number, unit, symbol or word → reject);',
      '3. summary or kind claims something the literal does not state (invented, merged behaviours, wrong value) → reject.',
    ].join('\n') + '\nUnsure → reject: a rejected item costs one re-read, a false item poisons every spec downstream.',
    section('Items', js(items.map(it => ({ key: it.key, kind: it.kind, summary: it.summary, literal: it.literal, cite: it.cite })))),
    'Return rejected [{key, reason}] — reason quotes what the GDD actually says (≤2 sentences) or "heading not found". Empty array when every item holds.',
  ]);
}

function criticPrompt(scope, recheck) {
  return prompt([
    roleHeader('completeness critic' + (recheck ? ' (re-check after one re-analysis round)' : ''), true),
    'Below: GDD chunks with their in-scope headings, the verified items extracted from them (key · kind · summary · cite) and headings declared non-technical (noTech).',
    'Open each GDD file and go heading by heading. Report a miss for (a) technical content no item covers — kinds: ' + KIND_DEFS + ' — and (b) a noTech claim that is wrong. Miss = {chunkId, heading (exact text), why (quote ≤2 sentences of the uncovered content)}.',
    'Do NOT report: narrative / art / marketing; content an item already covers even if summarised differently; headings not listed.',
    section('Data', js(scope)),
    'Return misses [] (empty when coverage is complete).',
  ]);
}

function mapperPrompt(items, existing) {
  return prompt([
    modeHeader('module-architect', 'mapping'),
    'Read-only mode: write NOTHING.',
    pathsBlock(),
    section('Scope', [
      'Feature: ' + A.feature + ' · GDD files: ' + A.gddFiles.map(x => q(x)).join(', '),
      'Existing requirement files citing them: ' + (existing.length ? existing.map(x => q(x)).join(', ') : 'none'),
      FILTER.length
        ? 'Module filter: ' + FILTER.join(', ') + ' — modules[] holds ONLY these ids; every item another module owns → outOfFilter {key, owner}.'
        : 'Module filter: none.',
    ].join('\n')),
    section('Verified GDD items', js(items)),
    'Return modules[] (responsibilities = item keys; extends = ' + q('<path>::<Type>.<Member>') + ' opened this session, only when extending existing code), alternatives[] (real boundary choices, 2–4 options each), unmapped[] {key, reason}' + (FILTER.length ? ', outOfFilter[]' : '') + '. Every item key appears exactly once across responsibilities / unmapped' + (FILTER.length ? ' / outOfFilter' : '') + '.',
  ]);
}

async function analyzeChunks(chunks, phaseName, existing) {
  const results = await pipeline(chunks,
    (p, item) => { const c = own(p, item); return call('analyst', analystPrompt(c, existing), { label: 'analyst:' + c.id, phase: phaseName, schema: ANALYST }); },
    async (res, c) => {
      if (!res) return null;
      // Keys / gapIds re-stamped by the script: unique and stable regardless of what the analyst emitted.
      const items = list(res.items).filter(it => isObj(it) && isStr(it.literal) && isStr(it.cite))
        .map((it, n) => Object.assign({}, it, { key: c.id + '-' + (n + 1) }));
      const gaps = list(res.gaps).filter(g => isObj(g) && isStr(g.question)).map((g, n) => {
        const id = c.id + '-G' + (n + 1);
        const opts = list(g.options).filter(isObj);
        if (opts.length > 3) note(id + ': ' + (opts.length - 3) + ' option(s) beyond 3 dropped (Gate A adds Defer; AskUserQuestion max 4)');
        if (!opts.length) note(id + ': analyst gave no options — main session must write ≥1 cited option before Gate A');
        return Object.assign({}, g, { gapId: id, cite: citeIn(c.file, g.cite), options: opts.slice(0, 3) });
      });
      const malformed = list(res.items).length - items.length;
      if (malformed) note(c.id + ': ' + malformed + ' item(s) without literal / cite dropped');
      const badGaps = list(res.gaps).length - gaps.length;
      if (badGaps) note(c.id + ': ' + badGaps + ' gap(s) without question dropped');
      const changed = list(res.changed).filter(isObj).map(x => Object.assign({}, x, { cite: citeIn(c.file, x.cite) }));
      const base = { chunk: c, gaps: gaps, noTech: list(res.noTech).filter(isObj), changed: changed };
      if (!items.length) {
        note(c.id + ': 0 items, ' + gaps.length + ' gaps, ' + base.noTech.length + ' noTech');
        return Object.assign(base, { items: [] });
      }
      const qv = await call('quoteVerifier', quotePrompt(c, items), { label: 'quote:' + c.id, phase: phaseName, schema: QUOTE });
      if (!qv) {
        note(c.id + ': quote verifier failed — ' + items.length + ' unverified items dropped, headings re-queued');
        return null;
      }
      const rejected = {};
      list(qv.rejected).forEach(r => { if (isObj(r) && isStr(r.key)) rejected[r.key] = r.reason || ''; });
      const kept = items.filter(it => !Object.prototype.hasOwnProperty.call(rejected, it.key));
      const dropped = items.filter(it => Object.prototype.hasOwnProperty.call(rejected, it.key));
      note(c.id + ': ' + items.length + ' items, ' + dropped.length + ' rejected by quote check' +
        (dropped.length ? ' (' + dropped.map(it => it.key + ': ' + rejected[it.key]).join('; ') + ')' : '') +
        ', ' + gaps.length + ' gaps, ' + base.noTech.length + ' noTech');
      return Object.assign(base, { items: kept });
    });
  return chunks.map((c, i) => ({ chunk: c, result: results[i] || null }));
}

function criticScope(chunks, byChunk) {
  return chunks.map(c => {
    const done = byChunk[c.id] || [];
    return {
      chunkId: c.id, file: c.file, headings: c.headings,
      items: done.flatMap(r => r.items.map(it => ({ key: it.key, kind: it.kind, summary: it.summary, cite: it.cite }))),
      noTech: done.flatMap(r => r.noTech),
    };
  });
}

function validMisses(res, chunkById) {
  return list(res && res.misses).filter(m => isObj(m) && isStr(m.heading) && chunkById[m.chunkId]);
}

async function runAnalyze() {
  const existing = strs(A.existingRequirements);
  const chunkById = {};
  A.chunks.forEach(c => { chunkById[c.id] = c; });
  const byChunk = {};
  const uncovered = [];
  function collect(outcomes, parentOf) {
    const failed = [];
    outcomes.forEach(o => {
      const pid = parentOf(o.chunk);
      if (o.result) (byChunk[pid] = byChunk[pid] || []).push(o.result);
      else failed.push(o.chunk);
    });
    return failed;
  }

  phase('Analyze');
  const first = await analyzeChunks(A.chunks, 'Analyze', existing);
  const failedFirst = collect(first, c => c.id);

  phase('Critic');
  // Failed chunks are deterministic misses: no critic needed to know nothing was extracted.
  const forced = failedFirst.flatMap(c => c.headings.map(h => ({ chunkId: c.id, heading: h, why: 'analysis failed in first pass' })));
  if (failedFirst.length) note('Analyze: ' + failedFirst.length + ' chunk(s) failed (' + failedFirst.map(c => c.id).join(', ') + ') — headings re-queued for the re-analysis round');
  const okChunks = A.chunks.filter(c => failedFirst.indexOf(c) < 0);
  let misses = forced;
  let criticFailed = false;
  if (okChunks.length) {
    const cr = await call('critic', criticPrompt(criticScope(okChunks, byChunk), false), { label: 'critic', phase: 'Critic', schema: CRITIC });
    if (!cr) {
      criticFailed = true;
      note('Critic: critic failed — coverage of ' + okChunks.length + ' chunk(s) NOT checked (coverageChecked: false)');
    }
    const found = validMisses(cr, chunkById);
    const droppedMisses = list(cr && cr.misses).length - found.length;
    if (droppedMisses > 0) note('Critic: ' + droppedMisses + ' miss(es) ignored — unknown chunkId or empty heading');
    misses = misses.concat(found);
  }
  note(misses.length ? 'Critic: ' + misses.length + ' miss(es) → one re-analysis round' : (criticFailed ? 'Critic: no forced miss (critic did not run — see above)' : 'Critic: no miss'));

  if (misses.length) {
    const groups = {};
    misses.forEach(m => { (groups[m.chunkId] = groups[m.chunkId] || []).push(m); });
    const reChunks = Object.keys(groups).sort().map(id => {
      const done = byChunk[id] || [];
      return {
        id: id + 'r', parent: id, file: chunkById[id].file, headings: uniq(groups[id].map(m => m.heading)),
        why: groups[id].map(m => ({ heading: m.heading, why: m.why || '' })),
        prior: done.flatMap(r => r.items.map(it => ({ key: it.key, kind: it.kind, summary: it.summary, literal: it.literal, cite: it.cite }))),
        priorGaps: done.flatMap(r => r.gaps.map(g => ({ gapId: g.gapId, question: g.question, cite: g.cite }))),
      };
    });
    const second = await analyzeChunks(reChunks, 'Critic', existing);
    // Backstop: drop re-extracted duplicates of items / gaps the first pass already holds (same cite + same text).
    const normText = s => String(s || '').replace(/[*_`]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
    second.forEach(o => {
      if (!o.result) return;
      const c = o.chunk;
      const seenItem = {};
      const seenGap = {};
      c.prior.forEach(it => { seenItem[it.cite + '|' + normText(it.literal)] = true; });
      c.priorGaps.forEach(g => { seenGap[g.cite + '|' + normText(g.question)] = true; });
      const nItems = o.result.items.length;
      const nGaps = o.result.gaps.length;
      o.result.items = o.result.items.filter(it => !seenItem[it.cite + '|' + normText(it.literal)]);
      o.result.gaps = o.result.gaps.filter(g => !seenGap[g.cite + '|' + normText(g.question)]);
      const dupI = nItems - o.result.items.length;
      const dupG = nGaps - o.result.gaps.length;
      if (dupI || dupG) note(c.id + ': ' + dupI + ' duplicate item(s) + ' + dupG + ' duplicate gap(s) already held by ' + c.parent + ' dropped');
    });
    const failedRe = collect(second, c => c.parent);
    failedRe.forEach(c => c.headings.forEach(h => uncovered.push({ chunkId: c.parent, file: c.file, heading: h, why: 'analysis failed twice' })));
    const recheckChunks = reChunks.filter(c => failedRe.indexOf(c) < 0);
    if (recheckChunks.length) {
      // Re-check only the re-analysed headings; whatever is still missing is returned, not looped.
      const scope = criticScope(recheckChunks.map(c => ({ id: c.parent, file: c.file, headings: c.headings })), byChunk);
      const cr2 = await call('critic', criticPrompt(scope, true), { label: 'critic:recheck', phase: 'Critic', schema: CRITIC });
      if (!cr2) {
        note('Critic: re-check failed — ' + recheckChunks.reduce((n, c) => n + c.headings.length, 0) + ' re-analysed heading(s) returned as uncovered (unverified)');
        recheckChunks.forEach(c => c.headings.forEach(h => uncovered.push({ chunkId: c.parent, file: c.file, heading: h, why: 'critic re-check failed — coverage unverified' })));
      } else {
        const found2 = validMisses(cr2, chunkById);
        const dropped2 = list(cr2.misses).length - found2.length;
        if (dropped2 > 0) note('Critic: re-check — ' + dropped2 + ' miss(es) ignored — unknown chunkId or empty heading');
        found2.forEach(m => uncovered.push({ chunkId: m.chunkId, file: chunkById[m.chunkId].file, heading: m.heading, why: m.why || '' }));
      }
    }
  }
  if (uncovered.length) note('Critic: ' + uncovered.length + ' heading(s) returned as uncovered (see why)');

  const results = A.chunks.flatMap(c => byChunk[c.id] || []);
  const items = results.flatMap(r => r.items);
  const gaps = results.flatMap(r => r.gaps);
  // A re-analysis chunk re-reports drift its parent already reported: one entry per FR + cite.
  const seenDrift = {};
  const changed = results.flatMap(r => r.changed).filter(x => {
    const k = String(x.fr || '') + '|' + x.cite;
    if (seenDrift[k]) return false;
    seenDrift[k] = true;
    return true;
  });
  const compact = items.map(it => ({ key: it.key, kind: it.kind, summary: it.summary, cite: it.cite }));
  note('Analyze: ' + items.length + ' verified item(s), ' + gaps.length + ' gap(s)' + (A.mode === 'update' ? ', ' + changed.length + ' drifted FR Source(s)' : ''));

  phase('Map');
  let mapping = { modules: [], alternatives: [], unmapped: [] };
  let outOfFilter = [];
  if (!items.length) {
    note('Map: no verified item — mapping skipped');
  } else {
    const m = await call('mapper', mapperPrompt(compact, existing), { label: 'mapper', phase: 'Map', schema: MAPPER });
    if (!m) {
      note('Map: mapper failed — mapping is null; dispatch module-architect Mode mapping on `items` before Gate A');
      mapping = null;
    } else {
      const norm = normalizeMapping(m, compact);
      mapping = norm.mapping;
      outOfFilter = norm.outOfFilter;
    }
  }

  return {
    stage: 'analyze',
    items: compact,
    gaps: gaps,
    mapping: mapping,
    uncovered: uncovered,
    outOfFilter: outOfFilter,
    changed: changed,
    coverageChecked: !criticFailed,
    models: used,
    log: LOG,
  };
}

// Deterministic checks on the mapper output: every key placed exactly once, filter enforced.
function normalizeMapping(m, items) {
  const known = {};
  items.forEach(it => { known[it.key] = true; });
  const owner = {};
  const modules = [];
  const alternatives = list(m.alternatives).filter(a => isObj(a) && isStr(a.question));
  const badAlts = list(m.alternatives).length - alternatives.length;
  if (badAlts) note('Map: ' + badAlts + ' alternative(s) without question ignored');
  let unmapped = list(m.unmapped).filter(u => isObj(u) && known[u.key]);
  let outOfFilter = list(m.outOfFilter).filter(o => isObj(o) && known[o.key]);
  const strayLists = list(m.unmapped).length - unmapped.length + list(m.outOfFilter).length - outOfFilter.length;
  if (strayLists > 0) note('Map: ' + strayLists + ' unmapped / outOfFilter entr(ies) with unknown key ignored');
  list(m.modules).forEach(mod => {
    if (!isObj(mod) || !isStr(mod.id)) { note('Map: module entry without id ignored'); return; }
    const resp = uniq(strs(mod.responsibilities));
    const unknown = resp.filter(k => !known[k]);
    if (unknown.length) note('Map: ' + mod.id + ' listed unknown key(s) ' + unknown.join(', ') + ' — ignored');
    const keys = resp.filter(k => known[k]);
    if (FILTER.length && FILTER.indexOf(mod.id) < 0) {
      note('Map: ' + mod.id + ' is outside the module filter — its ' + keys.length + ' key(s) moved to outOfFilter');
      keys.forEach(k => outOfFilter.push({ key: k, owner: mod.id }));
      return;
    }
    keys.forEach(k => {
      if (owner[k]) {
        alternatives.push({
          question: 'Item ' + k + ' được map vào cả ' + owner[k] + ' và ' + mod.id + ' — module nào own?',
          options: [{ label: owner[k], description: 'giữ ở ' + owner[k] }, { label: mod.id, description: 'chuyển sang ' + mod.id }],
        });
        note('Map: key ' + k + ' assigned to both ' + owner[k] + ' and ' + mod.id + ' — kept on ' + owner[k] + ', question added');
      } else owner[k] = mod.id;
    });
    const mine = keys.filter(k => owner[k] === mod.id);
    if (!mine.length) { note('Map: ' + mod.id + ' owns no item key — not proposed'); return; }
    modules.push(Object.assign({}, mod, { responsibilities: mine }));
  });
  // A key owned by a module is not also unmapped / outOfFilter.
  unmapped = unmapped.filter(u => !owner[u.key]);
  outOfFilter = outOfFilter.filter(o => !owner[o.key]);
  const placed = Object.assign({}, owner);
  unmapped.forEach(u => { placed[u.key] = true; });
  outOfFilter.forEach(o => { placed[o.key] = true; });
  const missing = items.filter(it => !placed[it.key]).map(it => it.key);
  if (missing.length) {
    note('Map: ' + missing.length + ' key(s) not returned by the mapper → unmapped (' + missing.join(', ') + ')');
    missing.forEach(k => unmapped.push({ key: k, reason: 'not returned by the mapper' }));
  }
  return { mapping: { modules: modules, alternatives: alternatives, unmapped: unmapped }, outOfFilter: outOfFilter };
}

// ---------- shared verify → fix loop ----------

async function fixLoop(cfg) {
  // cfg: {key, phase, modules:[ids], verifyPrompt(round, prev), fixPrompt(defects, round)}
  let round = 0;
  let v = await call('verifier', cfg.verifyPrompt(0, null), { label: 'verify:' + cfg.key + '#0', phase: cfg.phase, schema: VERIFY });
  if (!v) {
    note(cfg.key + ': verifier failed — output UNVERIFIED');
    return cfg.modules.map(id => ({ module: id, id: '-', problem: 'verifier failed — output unverified', evidence: '' }));
  }
  let defects = list(v.defects).filter(isObj);
  while (defects.length && round < MAX_FIX_ROUNDS) {
    round++;
    const fx = await call('fixer', cfg.fixPrompt(defects, round), { label: 'fix:' + cfg.key + '#' + round, phase: cfg.phase, schema: FIX });
    if (!fx) { note(cfg.key + ': fixer round ' + round + ' failed — ' + defects.length + ' defect(s) left'); break; }
    const prev = { defects: defects, fixed: list(fx.fixed), disputed: list(fx.disputed), open: list(fx.open) };
    v = await call('verifier', cfg.verifyPrompt(round, prev), { label: 'verify:' + cfg.key + '#' + round, phase: cfg.phase, schema: VERIFY });
    if (!v) {
      note(cfg.key + ': re-verify round ' + round + ' failed — previous defects kept as unresolved');
      defects = defects.map(d => Object.assign({}, d, { problem: d.problem + ' (re-verify failed — status unknown)' }));
      break;
    }
    defects = list(v.defects).filter(isObj);
  }
  note(cfg.key + ': ' + (defects.length ? defects.length + ' unresolved defect(s)' : 'verified clean') + ' after ' + round + ' fix round(s)' + (defects.length && round === MAX_FIX_ROUNDS ? ' (limit ' + MAX_FIX_ROUNDS + ')' : ''));
  return defects;
}

function deltaBlock(round, prev, checksName) {
  if (!round) return '';
  return section('Round ' + round + ' — delta re-check only', [
    'For each previously reported defect decide whether it is resolved — re-open the file, do not trust the fixer report. Then check the FRs / sections the fixer changed for NEW defects of the kinds in ' + checksName + '. Do not re-audit untouched content.',
    'Previous defects: ' + js(prev.defects),
    'Fixer report: ' + js({ fixed: prev.fixed, disputed: prev.disputed, open: prev.open }),
    'A disputed defect stays a defect only if the evidence still shows it; an open one stays (it needs a user answer).',
  ].join('\n'));
}

function fixPrompt(files, defects, round) {
  return prompt([
    modeHeader('spec-writer', 'fix'),
    'Fix round ' + round + '/' + MAX_FIX_ROUNDS + '. Files: ' + files.map(x => q(x)).join(', '),
    section('Defects from the independent verifier — apply ONLY these, touch nothing else, IDs stay stable', js(defects)),
    'Return fixed [{module, id, change}], disputed [{module, id, reason, evidence}] (defect not supported by its evidence — not changed), open [{module, id, question}] (fix needs information no source gives).',
  ]);
}

// ---------- stage: author ----------

// Drift entries of a module (update mode): a module with responsibilities [] is in the run only for these.
function driftOf(m, changed) { return changed.filter(x => driftOwns(x, m)); }
// GDD cites that decide a module's batch / GDD files: its responsibilities + its drift entries.
function citesOf(m, changed) { return m.responsibilities.map(r => r.cite).concat(driftOf(m, changed).map(x => x.cite)); }
function primaryFile(m, changed) {
  const counts = {};
  citesOf(m, changed).forEach(c => { const f = fileOf(c); counts[f] = (counts[f] || 0) + 1; });
  return Object.keys(counts).sort((a, b) => (counts[b] - counts[a]) || (a < b ? -1 : a > b ? 1 : 0))[0];
}

// Owner modules of a decision / deferred gap: modules with a responsibility citing the exact anchor;
// none → every module citing the same GDD file (fallback, logged by the caller).
function exactOwners(x, mods) { return mods.filter(m => m.responsibilities.some(r => r.cite.trim() === x.cite.trim())).map(m => m.id); }
function ownersOf(x, mods) {
  const exact = exactOwners(x, mods);
  return exact.length ? exact : mods.filter(m => m.responsibilities.some(r => fileOf(r.cite) === fileOf(x.cite))).map(m => m.id);
}

function makeBatches(mods, decisions, deferred, changed) {
  const byFile = {};
  mods.forEach(m => { const f = primaryFile(m, changed); (byFile[f] = byFile[f] || []).push(m); });
  const groups = [];
  Object.keys(byFile).sort().forEach(f => {
    for (let i = 0; i < byFile[f].length; i += BATCH_SIZE) groups.push(byFile[f].slice(i, i + BATCH_SIZE));
  });
  return groups.map((ms, i) => {
    const files = uniq(ms.flatMap(m => citesOf(m, changed).map(fileOf)));
    const inFiles = x => files.indexOf(fileOf(x.cite)) >= 0;
    const owned = x => x.modules.some(id => ms.some(m => m.id === id));
    // Drift goes to the batch of its module; no module of the run owns it → by GDD file (logged by the caller).
    const driftHere = x => { const o = mods.filter(m => driftOwns(x, m)); return o.length ? o.some(m => ms.indexOf(m) >= 0) : inFiles(x); };
    return {
      id: 'b' + (i + 1), modules: ms, files: files,
      decisions: decisions.filter(owned), deferred: deferred.filter(owned), changed: changed.filter(driftHere),
    };
  });
}

function writerPrompt(b) {
  return prompt([
    modeHeader('spec-writer', 'forward'),
    pathsBlock(),
    section('Batch ' + b.id, [
      'Mode ' + A.mode + ' (a target requirement.md that already exists follows the Update rules, whatever the mode) · template ' + q(C.templates + '/requirement-template.md') + ' · date ' + A.date,
      'GDD files (read each ONCE for the whole batch): ' + b.files.map(x => q(x)).join(', '),
      'Target per module: ' + q('<specsRoot>/<id>/requirement.md') + '.',
    ].join('\n')),
    section('Modules — confirmed mapping (responsibility keys with GDD cites)', js(b.modules.map(m => ({
      id: m.id, name: m.name, isNew: m.isNew, extends: m.extends, gddSections: m.gddSections, responsibilities: m.responsibilities,
    })))),
    section('Decisions (user answers to GDD gaps — literal; apply only in the module(s) of the entry\'s ' + q('modules') + ')', b.decisions.length ? js(b.decisions) : 'none'),
    section('Deferred gaps (stay NEEDS CLARIFICATION — only in the module(s) of the entry\'s ' + q('modules') + ')', b.deferred.length ? js(b.deferred) : 'none'),
    A.mode === 'update' ? section('Drift (FR Source literal ≠ GDD now, or cited heading removed)', b.changed.length ? [
      js(b.changed),
      '- change ' + q('"<old literal>" → "<new literal>"') + ' → rewrite the FR per the new literal, same ID.',
      '- change ' + q('removed') + ' → content moved under another heading of these GDD files → re-cite (same ID, literal from that heading); else entry with ' + q('decision') + ' → keep the FR, Source ' + q('decision: ' + A.date + ' — "<decision>"') + '; else delete the FR and return it in removed.',
      '- A module with responsibilities [] is in this batch only for its drift entries: touch nothing else in its file.',
    ].join('\n') : 'none') : '',
    'Return per module: id, path, frIds, nfrIds, open [{ref, question, cite}] (every NEEDS CLARIFICATION left), contractRows (Contract surface row → kind surface, owner = owning module; Consumer obligations row → kind obligation, owner = consumer module), orphanContractFRs + removed (existing file), contractsDocProposals (additions you propose for contractsDoc — only when configured; never put them in open).',
  ]);
}

function authorVerifyPrompt(b, written, round, prev) {
  const runFiles = A.gddFiles.map(x => q(x)).join(', ');
  const base = BASELINE
    ? 'Baseline (state before this run): ' + q(basePath('<MODULE>', 'requirement.md')) + ' — compare with ' + q('cmp') + ' / ' + q('diff') + ', never git (the kit never commits, so git is not "before this run"). Baseline file absent = new file.'
    : 'No baseline passed — skip every before/after comparison (ID stability, byte-identical rows); do not use git for it (the kit never commits, so git is not "before this run").';
  const scope = BASELINE
    ? 'In scope = every FR/NFR/Data row that is new (absent from the baseline), named by a drift entry, or whose Source — now or in the baseline — cites one of ' + runFiles + ' or cites a TDD whose ' + q('gdd-sources') + ' lists one of them (legacy migration). Run checks 1 and 3–8 on in-scope rows only. Every other FR/NFR/Data row: check only that it is byte-identical to the baseline — a changed out-of-scope row = defect; do not audit it further. Checks 2 and 9 apply to the whole file.'
    : 'In scope = every FR/NFR/Data row named by a drift entry, or whose Source cites one of ' + runFiles + ' (incl. ' + q('+ decision:') + '), is ' + q('decision:') + ' alone or a ' + q('NEEDS CLARIFICATION') + ' marker, or cites a TDD whose ' + q('gdd-sources') + ' lists one of them. Run checks 1 and 3–8 on in-scope rows only; leave every other row unaudited. Checks 2 and 9 apply to the whole file.';
  const checks = [
    '1. EARS shape: exactly one pattern of the template\'s EARS table (Ubiquitous / WHEN / WHILE / IF-THEN / WHERE / Complex with one chain); exactly one testable behaviour — hidden "and/or" behaviours = defect.',
    '2. IDs ' + q('<MODULE>-FR-NNN') + ' / ' + q('<MODULE>-NFR-NNN') + ', unique.' + (BASELINE ? ' Existing file (baseline present): an existing ID renumbered, reused for another behaviour, or deleted while its Source still resolves = defect; a FR whose Source starts with ' + q('contract:') + ' must be unchanged.' : ''),
    '3. Every Source resolves: GDD file + heading exist and the quoted literal is verbatim under it; ' + q('decision:') + ' text equals the decision answer verbatim (or, for a row re-cited from a legacy TDD, the ' + q('decision:') + ' text of that TDD sentence verbatim, same date; or the ' + q('decision') + ' of a drift entry) and is paired with its GDD anchor when one exists; a legacy-migration Source ' + q('NEEDS CLARIFICATION: <question>') + ' with a matching ' + q('## Open clarifications') + ' entry is valid; ' + q('contract:') + ' cites an existing row; code cites ' + q('<path>::<Type>.<Member>') + ' grep-match.',
    '4. Every decision is applied verbatim to the FR(s) it settles in the requirement.md of a module listed in its ' + q('modules') + ' field (other modules are not checked for it); no FR contradicts a decision.',
    '5. Every deferred gap is present as inline ' + q('NEEDS CLARIFICATION') + ' + an entry under ' + q('## Open clarifications') + ' in the requirement.md of a module listed in its ' + q('modules') + ' field — and in no module outside that list.',
    '6. Nothing invented (R5): every value / rule traces to a cited literal, decision or contract row; no estimate, no banned ambiguous quantifier without number + cite.',
    '7. Host trust boundary: if the host rules declare an authority / trust boundary (e.g. server-authoritative outcomes), a requirement that violates it = defect.',
    '8. Coverage: every responsibility key → ≥1 FR/NFR or ' + q('## Data & constants') + ' row whose Source cites the key\'s GDD heading, or an ' + q('## Out of scope') + ' line naming it and the receiving module, or (file with ' + q('origin: reverse-engineered') + ' only) a ' + q('## Drift vs GDD') + ' entry citing that heading — a code-cited FR duplicated by a new GDD-cited FR for the same behaviour = defect.',
    '9. Frontmatter ' + q('gdd-sources') + ' lists every GDD file the FRs cite; ' + q('tdd-source') + ' absent unless a row still cites a TDD whose ' + q('gdd-sources') + ' lists no file of this run (legacy, out of scope); ' + q('## Data & constants') + ' rows are literal + cited (or ' + q('N/A — <reason>') + ').',
  ];
  if (b.changed.length) {
    checks.push('10. Drift: every drift entry applied — literal change → FR rewritten to the new literal, same ID; ' + q('removed') + ' → FR re-cited to the heading the content moved to, or kept with ' + q('decision: ' + A.date + ' — "<decision>"') + ' when the entry carries ' + q('decision') + ', or deleted (and listed in the writer\'s removed).');
  }
  return prompt([
    roleHeader('adversarial requirement verifier for batch ' + b.id + ' — default to "defect" when unsure', true),
    section('Files', written.map(w => '- ' + w.id + ': ' + q(w.path)).join('\n') + '\nTemplate: ' + q(C.templates + '/requirement-template.md') + ' · GDD files: ' + b.files.map(x => q(x)).join(', ')),
    section('Inputs', [
      'Responsibilities: ' + js(b.modules.map(m => ({ module: m.id, keys: m.responsibilities.map(r => ({ key: r.key, cite: r.cite })) }))),
      'Decisions: ' + (b.decisions.length ? js(b.decisions) : 'none'),
      'Deferred gaps: ' + (b.deferred.length ? js(b.deferred) : 'none'),
      'Drift entries: ' + (b.changed.length ? js(b.changed) : 'none'),
      'Writer report: ' + js(written.map(w => ({ module: w.id, removed: w.removed, open: w.open }))),
    ].join('\n')),
    deltaBlock(round, prev, 'Checks'),
    section('Baseline', base),
    section('Scope', scope),
    section('Checks', checks.join('\n')),
    'Return defects [{module, id (FR/NFR id, section name or responsibility key), problem, evidence (cite + literal ≤2 sentences)}]; [] when clean.',
  ]);
}

function ambiguityPrompt(w, files) {
  return prompt([
    roleHeader('EARS ambiguity reviewer for module ' + w.id, true),
    'File: ' + q(w.path) + ' · GDD context: ' + files.map(x => q(x)).join(', '),
    'For every FR/NFR flag only ambiguity a developer could not resolve from the file + its cited GDD literal:\n' + [
      '- missing trigger (event behaviour without WHEN, unclear start condition);',
      '- unmeasurable response (no observable value; "fast", "smooth"; banned ambiguous quantifier);',
      '- hidden multi-behaviour (two testable outcomes in one requirement);',
      '- undefined term (not defined in the file, its GDD cite or the host glossary).',
    ].join('\n'),
    'Skip anything already marked NEEDS CLARIFICATION (already asked).',
    'Per question: qId ' + q(w.id + '-Q<n>') + ', fr, question (ONE decision), options (2–4; each description quotes the GDD / requirement text that constrains it, or says "GDD im lặng").',
    'Return {module: "' + w.id + '", questions: []} — empty when nothing is ambiguous.',
  ]);
}

function reconcilePrompt(written, runIds) {
  return prompt([
    roleHeader('contract reconciler', false),
    'Edit permission: ONLY the ' + q('Owner FR') + ' cells of ' + q('## Contract surface') + ' tables and the ' + q('Consumer FR') + ' cells of ' + q('## Consumer obligations') + ' tables, in the files listed below. Change nothing else — no other cell, no prose, no other file.',
    pathsBlock(),
    section('Files in scope', written.map(w => '- ' + w.id + ': ' + q(w.path)).join('\n') + '\nModules of this run (count as registered even if ' + q('modules.json') + ' does not list them yet): ' + runIds.join(', ')),
    section('Rule per row', [
      '- Contract surface row (file module = consumer, Owning module = owner): find in ' + q('<specsRoot>/<owner>/requirement.md') + ' a FR/NFR that provides EXACTLY that need. Link only when (a) the ID Grep-matches as a heading ' + q('### <ID>') + ' in that file AND (b) its Requirement text provides the need — same topic is not enough. Write the ID into Owner FR.',
      '- Consumer obligations row (file module = owner, Consumer module = consumer): same check against ' + q('<specsRoot>/<consumer>/requirement.md') + ', written into Consumer FR.',
      '- Cell already holding an ID: re-check (a) + (b); failing → ' + q('contract-gap') + '. Cell ' + q('stopgap — …') + ': leave untouched, report nothing.',
      '- Target has no requirement.md, is neither in modules.json nor in this run, or no exact FR → ' + q('contract-gap') + '.',
    ].join('\n')),
    'Return linked [{consumer, row, owner, kind, id, cite (' + q('<path>#<ID>') + ' + literal ≤2 sentences)}] and gaps [{consumer, row, owner, kind}] — row = the row\'s first cell verbatim, kind surface | obligation, consumer / owner always the consumer side / provider side of the need.',
  ]);
}

function registerPrompt(written, mapping) {
  return prompt([
    modeHeader('module-architect', 'register'),
    pathsBlock(),
    'Today: ' + A.date + '.',
    section('Confirmed mapping', js(mapping.map(m => ({ id: m.id, name: m.name, isNew: m.isNew, extends: m.extends, gddSections: m.gddSections })))),
    section('requirement.md files', written.map(w => '- ' + w.id + ': ' + q(w.path)).join('\n')),
    'Return touched (module ids written), layers [{layer, modules}], cycles [{modules, evidence}], findings [{finding, evidence, impact}].',
  ]);
}

function normalizeWritten(res, b) {
  const byId = {};
  list(res.modules).filter(w => isObj(w) && isStr(w.id)).forEach(w => { byId[w.id] = w; });
  const extra = Object.keys(byId).filter(id => !b.modules.some(m => m.id === id));
  if (extra.length) note(b.id + ': writer returned module(s) outside the batch ignored: ' + extra.join(', '));
  const out = [];
  b.modules.forEach(m => {
    const w = byId[m.id];
    if (!w) { note(b.id + ': writer returned nothing for ' + m.id + ' — treated as not written'); return; }
    out.push({
      id: m.id, path: isStr(w.path) ? w.path : reqPath(m.id),
      frIds: strs(w.frIds), nfrIds: strs(w.nfrIds), open: list(w.open).filter(isObj),
      contractRows: list(w.contractRows).filter(isObj), orphanContractFRs: strs(w.orphanContractFRs), removed: strs(w.removed),
      contractsDocProposals: strs(w.contractsDocProposals),
    });
  });
  return out;
}

async function runAuthor() {
  const mods = A.modules;
  noteBaseline();
  // Each decision / deferred gap carries its owner modules; writer + verifier apply it only there.
  const tag = x => {
    const owners = ownersOf(x, mods);
    if (owners.length && !exactOwners(x, mods).length) {
      note('Write: ' + (x.gapId || x.cite) + ' — no responsibility cites its exact anchor; routed to every module citing ' + fileOf(x.cite) + ': ' + owners.join(', '));
    }
    return Object.assign({}, x, { modules: owners });
  };
  const decisions = list(A.decisions).map(tag);
  const deferred = list(A.deferred).map(tag);
  const changed = list(A.changed).filter(x => isObj(x) && isStr(x.cite));
  const badChanged = list(A.changed).length - changed.length;
  if (badChanged) note('Write: ' + badChanged + ' changed entr(ies) without cite ignored');
  const batches = makeBatches(mods, decisions, deferred, changed);
  note('Write: ' + mods.length + ' module(s) in ' + batches.length + ' batch(es) of ≤' + BATCH_SIZE + ': ' + batches.map(b => b.id + '[' + b.modules.map(m => m.id).join(',') + ']').join(' '));
  const routed = x => batches.some(b => b.decisions.indexOf(x) >= 0 || b.deferred.indexOf(x) >= 0);
  decisions.concat(deferred).filter(x => !routed(x)).forEach(x => {
    note('Write: ' + (x.gapId || x.cite) + ' cites a GDD file no module of this run cites — not routed to any writer');
  });
  changed.forEach(x => {
    const n = batches.filter(b => b.changed.indexOf(x) >= 0).length;
    if (!n) note('Write: drift ' + (x.fr || x.cite) + ' — no module of this run owns it or cites ' + fileOf(x.cite) + ' — not routed to any writer');
    else if (!mods.some(m => driftOwns(x, m))) note('Write: drift ' + (x.fr || x.cite) + ' — no module of this run owns it; routed by GDD file to ' + n + ' batch(es)');
  });

  phase('Write');
  const ambPending = [];
  const out = await pipeline(batches,
    (p, item) => { const b = own(p, item); return call('writer', writerPrompt(b), { label: 'writer:' + b.id, phase: 'Write', schema: WRITER }); },
    async (res, b) => {
      if (!res) { note(b.id + ': writer failed — ' + b.modules.map(m => m.id).join(', ') + ' not written'); return null; }
      const written = normalizeWritten(res, b);
      if (!written.length) return null;
      const defects = await fixLoop({
        key: b.id, phase: 'Write', modules: written.map(w => w.id),
        verifyPrompt: (round, prev) => authorVerifyPrompt(b, written, round, prev),
        fixPrompt: (ds, round) => fixPrompt(written.map(w => w.path), ds, round),
      });
      return { batch: b, written: written, defects: defects };
    },
    r => {
      if (!r) return null;
      // Ambiguity starts per module as soon as its batch leaves the fix loop; collected after Matrix.
      r.written.forEach(w => {
        ambPending.push(Promise.resolve()
          .then(() => call('ambiguity', ambiguityPrompt(w, r.batch.files), { label: 'ambiguity:' + w.id, phase: 'Ambiguity', schema: AMBIG }))
          .then(a => {
            if (!a) { note(w.id + ': ambiguity review failed — no EARS question collected'); return null; }
            const qs = list(a.questions).filter(x => isObj(x) && isStr(x.question));
            const badQs = list(a.questions).length - qs.length;
            if (badQs) note(w.id + ': ' + badQs + ' ambiguity question(s) without text dropped');
            return { module: w.id, questions: qs };
          })
          .catch(e => { note(w.id + ': ambiguity review error — ' + (e && e.message ? e.message : String(e))); return null; }));
      });
      return r;
    });

  const done = out.filter(Boolean);
  const written = done.flatMap(r => r.written);
  const writtenById = {};
  written.forEach(w => { writtenById[w.id] = w; });
  const defectsOf = {};
  done.forEach(r => r.defects.forEach(d => {
    const ids = r.written.some(w => w.id === d.module) ? [d.module] : r.written.map(w => w.id);
    ids.forEach(id => { (defectsOf[id] = defectsOf[id] || []).push(d); });
  }));

  phase('Reconcile');
  let recon = null;
  let reg = null;
  if (written.length) {
    const runIds = written.map(w => w.id);
    const pair = await parallel([
      () => call('reconciler', reconcilePrompt(written, runIds), { label: 'reconcile', phase: 'Reconcile', schema: RECON }),
      () => call('register', registerPrompt(written, mods.filter(m => writtenById[m.id])), { label: 'register', phase: 'Matrix', schema: REGISTER }),
    ]);
    recon = pair[0];
    reg = pair[1];
    if (!recon) note('Reconcile: reconciler failed — Owner FR / Consumer FR cells left as the writers wrote them; contract gaps UNKNOWN');
    else note('Reconcile: ' + list(recon.linked).length + ' row(s) linked, ' + list(recon.gaps).length + ' contract-gap(s)');
    if (!reg) note('Matrix: register failed — modules.json NOT updated');
    else note('Matrix: ' + strs(reg.touched).length + ' module(s) touched, ' + list(reg.cycles).length + ' cycle(s)');
  } else {
    // Nothing to reconcile / register: empty results, so null keeps meaning "agent failed".
    recon = { linked: [], gaps: [] };
    reg = { touched: [], layers: [], cycles: [], findings: [] };
    note('Reconcile/Matrix skipped — no module written');
  }

  const order = mods.map(m => m.id);
  const ambiguities = (await Promise.all(ambPending)).filter(Boolean).sort((x, y) => order.indexOf(x.module) - order.indexOf(y.module));
  note('Ambiguity: ' + ambiguities.reduce((n, a) => n + a.questions.length, 0) + ' question(s) over ' + ambiguities.length + ' module(s)');

  return {
    stage: 'author',
    modules: mods.map(m => {
      const w = writtenById[m.id];
      if (!w) {
        return {
          id: m.id, path: reqPath(m.id), frCount: 0, nfrCount: 0, open: [], failed: true,
          unresolvedDefects: [{ module: m.id, id: '-', problem: 'writer failed — requirement.md not written / not verified', evidence: '' }],
        };
      }
      const r = { id: w.id, path: w.path, frCount: w.frIds.length, nfrCount: w.nfrIds.length, open: w.open, unresolvedDefects: defectsOf[w.id] || [] };
      if (w.orphanContractFRs.length) r.orphanContractFRs = w.orphanContractFRs;
      if (w.removed.length) r.removed = w.removed;
      if (w.contractsDocProposals.length) r.contractsDocProposals = w.contractsDocProposals;
      return r;
    }),
    ambiguities: ambiguities,
    contractGaps: recon ? list(recon.gaps).filter(isObj) : null,
    matrix: reg,
    models: used,
    log: LOG,
  };
}

// ---------- stage: specify ----------

function backpropPrompt(target, rows) {
  return prompt([
    modeHeader('spec-writer', 'back-propagation'),
    pathsBlock(),
    'Target module: ' + target + ' — ' + q(reqPath(target)) + ' · template ' + q(C.templates + '/requirement-template.md') + ' · date ' + A.date,
    section('Rows the target must own (user choice per row)', js(rows.map(r => ({
      choice: r.choice, kind: r.kind, row: r.row, rowModule: r.rowModule,
      rowFile: reqPath(r.rowModule), rowSection: r.kind === 'obligation' ? 'Consumer obligations' : 'Contract surface',
    })))),
    'The row modules\' specify.md are composed AFTER you in this run (stage specify, phase Compose).',
    'Return target "' + target + '", newIds [{row, module, id}] for choice add, stopgaps [{row, module}] for choice stopgap, conflicts [{row, module, outOfScope}] for needs that contradict the target\'s Out of scope (quote that line; nothing written). Exactly one entry per input row; row = the row text exactly as given, module = its rowModule exactly as given (rows from different modules with the same text get separate entries, and may share an id when one FR covers both).',
  ]);
}

function composePrompt(m, ctx) {
  return prompt([
    modeHeader('spec-writer', 'compose-specify'),
    pathsBlock(),
    section('Module ' + m.id, [
      'requirement.md: ' + q(m.path) + ' · specify.md target: ' + q(specPath(m.id)) + ' · template ' + q(C.templates + '/specify-template.md') + ' · date ' + A.date,
    ].join('\n')),
    section('User answers (literal — write back verbatim; action per kind — spec-writer §Mode compose-specify step 1)', ctx.answers.length ? js(ctx.answers.map(a => ({ kind: a.kind, ref: a.ref, question: a.question, answer: a.answer, date: A.date }))) : 'none'),
    section('Contract cells to fill (ids from back-propagation)', ctx.fills.length ? js(ctx.fills) : 'none'),
    section('Stopgap marks', ctx.stopgaps.length ? js(ctx.stopgaps) : 'none'),
    section('Withdrawn needs (remove the row, rework the FR text that depended on it)', ctx.withdrawals.length ? js(ctx.withdrawals) : 'none'),
    section('Rows left as contract-gap (back-propagation conflict or failure)', ctx.conflicts.length ? js(ctx.conflicts) : 'none'),
    section('FRs back-propagated INTO this module this run (compose them too)', ctx.incoming.length ? js(ctx.incoming) : 'none'),
    'Return id "' + m.id + '", specifyWritten, open [{fr, question, options}] (markers / unsettled ambiguities left — specify.md NOT written when non-empty), acCount, changedIds (FR/NFR whose requirement text changed), conflicts [{ref, reason}] (answers contradicting a GDD literal, not applied), contractGaps [{row, kind, target}] (rows still contract-gap).',
  ]);
}

function composeVerifyPrompt(m, ctx, res, round, prev) {
  const written = !!res.specifyWritten;
  const checks = [
    'A. Write-back (requirement.md), per answer kind: ' + [
      'clarify → marker replaced / ambiguous FR rewritten under the same ID, entry removed from ' + q('## Open clarifications') + ', Source carries ' + q('decision: ' + A.date + ' — "<answer>"') + ' paired with its GDD anchor when one exists',
      'add (ref = uncovered GDD heading cite or responsibility key) → a new FR/NFR/Data row at the next free ID whose Source quotes the GDD literal under that heading — no ' + q('decision:') + ' (the GDD is not silent)',
      'out-of-scope (ref = heading cite / key / defect id) → one ' + q('## Out of scope') + ' line citing the heading / key and naming the receiving module from the answer, with a ' + q('decision:') + ' cite for the choice',
      'fix (ref = defect id) → the user ruling applied to that FR/row only, nothing else changed (ruling "accept as-is" → no edit)',
    ].join('; ') + '. Answers listed as conflicts are NOT applied; contract fills / stopgap marks / withdrawals land in the right rows.',
  ];
  if (written) {
    checks.push(
      'B0. Gate: requirement.md (after write-back) contains zero ' + q('NEEDS CLARIFICATION') + ', its ' + q('## Open clarifications') + ' section is empty, and the composer report ' + q('open') + ' is empty — otherwise specify.md must not have been written this run = defect (id "specify.md").',
      'B1. Zero ' + q('NEEDS CLARIFICATION') + ' in specify.md.',
      'B2. Every FR/NFR has ≥1 Given/When/Then acceptance criterion with an observable, measurable result; numeric convention per host rules; no banned ambiguous quantifier (vài, nhiều, khoảng, chừng, hơi, khá, tương đối, một số) without number + cite.',
      'B3. FR/NFR ID set identical to requirement.md; requirement text identical to requirement.md (clarified).',
      'B4. Every Trace cite resolves (GDD file + heading exist; decision text matches requirement.md; contract row exists; code symbol grep-matches).',
      'B5. Every Owner FR / Consumer FR cell: the ID Grep-matches ' + q('### <ID>') + ' in the target\'s requirement.md, or is ' + q('contract-gap') + ', or ' + q('stopgap — <Target> Out of scope') + ' (Target = owning module for a Contract surface row, consumer module for a Consumer obligations row).'
    );
  } else {
    checks.push('specify.md was NOT written (open: ' + js(list(res.open)) + ') — check A only' + (BASELINE
      ? ', and that ' + q(specPath(m.id)) + ' is unchanged by this run: baseline ' + q(basePath(m.id, 'specify.md')) + ' absent → the file must not exist; present → ' + q('cmp') + ' both files, they must be identical. Never use git for this (the kit never commits, so earlier runs leave specify.md modified / untracked).'
      : '. No baseline passed — do not check specify.md state (git cannot tell this run from earlier uncommitted runs).'));
  }
  return prompt([
    roleHeader('adversarial specify verifier for module ' + m.id + ' — default to "defect" when unsure', true),
    'Files: ' + q(m.path) + (written ? ', ' + q(specPath(m.id)) : '') + ' · template ' + q(C.templates + '/specify-template.md'),
    section('Inputs', [
      'Answers: ' + (ctx.answers.length ? js(ctx.answers) : 'none'),
      'Contract fills: ' + js({ fills: ctx.fills, stopgaps: ctx.stopgaps, withdrawals: ctx.withdrawals }),
      'Composer report: ' + js(res),
    ].join('\n')),
    deltaBlock(round, prev, 'Checks'),
    section('Checks', checks.join('\n')),
    'Return defects [{module, id, problem, evidence (cite + literal ≤2 sentences)}]; [] when clean.',
  ]);
}

async function runSpecify() {
  const mods = A.modules.map(m => ({ id: m.id, path: isStr(m.path) ? m.path : reqPath(m.id) }));
  const inRun = {};
  mods.forEach(m => { inRun[m.id] = m; });
  const followUps = [];
  noteBaseline();
  const answers = list(A.answers).map(a => ({ module: a.module, kind: a.kind || 'clarify', ref: a.ref || '', question: a.question || '', answer: a.answer }));
  answers.filter(a => !inRun[a.module]).forEach(a => {
    note('Compose: answer ' + (a.ref || a.question) + ' targets ' + a.module + ', not in this run — not applied');
    followUps.push({ target: a.module, reason: 'answer "' + (a.ref || a.question) + '" not applied — module outside this specify run; /ndv-specify ' + a.module });
  });
  const choices = list(A.gapChoices).map(g => {
    const kind = g.kind === 'obligation' ? 'obligation' : 'surface';
    return {
      consumer: g.consumer, owner: g.owner, row: g.row, choice: g.choice, kind: kind,
      target: kind === 'obligation' ? g.consumer : g.owner, // module that must own the need
      rowModule: kind === 'obligation' ? g.owner : g.consumer, // module whose table holds the row
    };
  });
  choices.filter(c => !inRun[c.rowModule]).forEach(c => {
    note('Back-propagate: row "' + c.row + '" lives in ' + c.rowModule + ', not in this run — skipped');
    followUps.push({ target: c.rowModule, reason: 'contract-gap "' + c.row + '" not handled — module outside this specify run; /ndv-specify ' + c.rowModule + ' Phase 4' });
  });
  const active = choices.filter(c => inRun[c.rowModule]);
  const ctxOf = {};
  mods.forEach(m => {
    ctxOf[m.id] = {
      answers: answers.filter(a => a.module === m.id),
      fills: [], stopgaps: [], conflicts: [], incoming: [],
      withdrawals: active.filter(c => c.choice === 'withdraw' && c.rowModule === m.id).map(c => ({ row: c.row, kind: c.kind, target: c.target })),
    };
  });

  phase('Back-propagate');
  const toProp = active.filter(c => c.choice !== 'withdraw');
  const targets = uniq(toProp.map(c => c.target)).sort();
  if (!targets.length) note('Back-propagate: no add / stopgap choice — skipped');
  const bp = await parallel(targets.map(t => () =>
    call('backprop', backpropPrompt(t, toProp.filter(c => c.target === t)), { label: 'backprop:' + t, phase: 'Back-propagate', schema: BACKPROP })));
  targets.forEach((t, i) => {
    const rows = toProp.filter(c => c.target === t);
    const r = bp[i];
    if (!r) {
      note('Back-propagate: ' + t + ' failed — ' + rows.length + ' row(s) stay contract-gap');
      rows.forEach(c => ctxOf[c.rowModule].conflicts.push({ row: c.row, kind: c.kind, target: t, reason: 'back-propagation failed' }));
      followUps.push({ target: t, reason: 'back-propagation failed for ' + rows.length + ' row(s) — /ndv-specify ' + uniq(rows.map(c => c.rowModule)).join(', ') + ' Phase 4' });
      return;
    }
    // Match by row text AND row module: two consumers may send the same text to one target.
    const handled = [];
    const find = (text, mod) => rows.filter(c => c.rowModule === String(mod || '').trim() && c.row.trim() === String(text || '').trim() && handled.indexOf(c) < 0)[0];
    const take = (entries, apply) => list(entries).filter(isObj).forEach(e => {
      const c = find(e.row, e.module);
      if (!c) { note('Back-propagate: ' + t + ' returned unknown row "' + e.row + '" (' + e.module + ') — ignored'); return; }
      handled.push(c);
      apply(c, e);
    });
    take(r.newIds, (c, e) => {
      ctxOf[c.rowModule].fills.push({ row: c.row, kind: c.kind, target: t, id: e.id });
      if (inRun[t]) ctxOf[t].incoming.push({ id: e.id, row: c.row, from: c.rowModule });
    });
    take(r.stopgaps, c => { ctxOf[c.rowModule].stopgaps.push({ row: c.row, kind: c.kind, target: t, mark: 'stopgap — ' + t + ' Out of scope' }); });
    take(r.conflicts, (c, e) => {
      ctxOf[c.rowModule].conflicts.push({ row: c.row, kind: c.kind, target: t, reason: 'conflicts with Out of scope: ' + (e.outOfScope || '') });
      followUps.push({ target: t, reason: 'conflict with ' + t + ' Out of scope — "' + c.row + '": ' + (e.outOfScope || '') });
    });
    rows.filter(c => handled.indexOf(c) < 0).forEach(c => {
      note('Back-propagate: ' + t + ' returned no result for row "' + c.row + '" — stays contract-gap');
      ctxOf[c.rowModule].conflicts.push({ row: c.row, kind: c.kind, target: t, reason: 'no back-propagation result' });
    });
    const changedTarget = list(r.newIds).length + list(r.stopgaps).length;
    if (changedTarget && !inRun[t]) {
      followUps.push({ target: t, reason: 'requirement.md changed by back-propagation (' + uniq(list(r.newIds).map(e => e.id)).concat(list(r.stopgaps).length ? ['stopgap'] : []).join(', ') + ') — /ndv-specify ' + t });
    }
    note('Back-propagate: ' + t + ' — ' + list(r.newIds).length + ' new id(s), ' + list(r.stopgaps).length + ' stopgap(s), ' + list(r.conflicts).length + ' conflict(s)');
  });

  phase('Compose');
  const composed = await pipeline(mods,
    (p, item) => { const m = own(p, item); return call('composer', composePrompt(m, ctxOf[m.id]), { label: 'compose:' + m.id, phase: 'Compose', schema: COMPOSE }); },
    async (res, m) => {
      if (!res) { note(m.id + ': composer failed — specify.md not written'); return null; }
      const defects = await fixLoop({
        key: m.id, phase: 'Compose', modules: [m.id],
        verifyPrompt: (round, prev) => composeVerifyPrompt(m, ctxOf[m.id], res, round, prev),
        fixPrompt: (ds, round) => fixPrompt(res.specifyWritten ? [m.path, specPath(m.id)] : [m.path], ds, round),
      });
      return { res: res, defects: defects };
    });

  return {
    stage: 'specify',
    modules: mods.map((m, i) => {
      const c = composed[i];
      if (!c) {
        return { id: m.id, path: m.path, specifyWritten: false, open: [], acCount: 0, changedIds: [], failed: true,
          unresolvedDefects: [{ module: m.id, id: '-', problem: 'composer failed — nothing composed', evidence: '' }] };
      }
      const open = list(c.res.open).filter(isObj);
      const defects = list(c.defects).slice();
      // Gate (zero markers / settled ambiguities) checked here too, not only by the verifier.
      if (c.res.specifyWritten && open.length) {
        note(m.id + ': composer reports specify.md written with ' + open.length + ' open item(s) — gate violated');
        defects.push({ module: m.id, id: 'specify.md', problem: 'specify.md written while ' + open.length + ' open item(s) remain — gate (zero markers / settled ambiguities) violated', evidence: js(open) });
      }
      return {
        id: m.id, path: m.path, specifyWritten: !!c.res.specifyWritten, open: open,
        acCount: typeof c.res.acCount === 'number' ? c.res.acCount : 0, changedIds: strs(c.res.changedIds),
        conflicts: list(c.res.conflicts).filter(isObj), contractGaps: list(c.res.contractGaps).filter(isObj),
        unresolvedDefects: defects,
      };
    }),
    followUps: followUps,
    models: used,
    log: LOG,
  };
}

// ---------- dispatch ----------

if (A.stage === 'analyze') return await runAnalyze();
if (A.stage === 'author') return await runAuthor();
return await runSpecify();
